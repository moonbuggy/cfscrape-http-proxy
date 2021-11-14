#! /usr/bin/env python

"""Cloudflare Anti-Bot HTTP Proxy.

A basic HTTP proxy in Python, implementing VeNoMouS' cloudflare scraping module.

https://github.com/moonbuggy/cfscrape-http-proxy
https://github.com/Anorov/cloudflare-scrape
https://github.com/VeNoMouS/cloudscraper
"""

import sys
from os import curdir, path
import signal

from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import configparser

from urllib.parse import urlparse
from urllib.parse import parse_qsl

import socket
import fcntl  # pylint: disable=E0401
import struct

import json
import daemon  # type: ignore
import daemon.pidfile  # type: ignore

import netifaces  # type: ignore

import validators  # type: ignore

import cloudscraper  # type: ignore
from requests_toolbelt.adapters.source import SourceAddressAdapter  # type: ignore

# prctl needs certain packages to be installed in the operating system
# and is therefore an optional module as a result we should expect an
# error in cases where it's not installed, which we need to catch
try:
    import prctl  # type: ignore
except ImportError:
    pass
else:
    prctl.set_proctitle('cfscrape-http-proxy ' + ' '.join(sys.argv[1:]))

# pylint: disable=C0103

# list possible configuration file locations in the order they should
# be tried, use first match
CONFIG_FILE = 'cfscrape-http-proxy.conf'
CONFIG_PATHS = [
                '/opt/etc/',
                '/etc/',
                '/usr/local/etc/',
                curdir
        ]


def signal_handler(_sig, _frame):
    """Handle SIGINT cleanly."""
    print('\nSignal interrupt. Exiting.')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def get_interface_ip(interfaces):
    """Get the first matching IP address for a list of interfaces."""
    for interface in interfaces:
        if interface in ['any', '0']:
            return '0'

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        iface_string = bytes(interface[:15], 'utf-8')

        try:
            ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,
                                  struct.pack('256s', iface_string))[20:24])
        except IOError:
            pass
        else:
            return ip

        print('Error: cannot find any network interfaces. %s' % interfaces)
        sys.exit(2)


class ProxyRequestHandler(BaseHTTPRequestHandler):
    """Parse incomming requests and fetch the data they want."""

    global args
    sessionBaseURL = None

    @staticmethod
    def get_url(url):
        """Fetch data from from a URL."""
        s = cloudscraper.create_scraper()
        if args.exit_ip:
            s.mount('http://', SourceAddressAdapter(args.exit_ip))
            s.mount('https://', SourceAddressAdapter(args.exit_ip))

        try:
            gotten = s.get(url)
            if 'text' in gotten.headers['Content-Type']:
                output = gotten.text.encode('utf-8')
            else:
                output = gotten.content
        # except cfscrape.CloudflareCaptchaError:
        except cloudscraper.exceptions.CloudflareCaptchaProvider:
            output = 'Cloudflare reCaptcha detected, but no reCaptcha provider is configured.'
            return output.encode('utf-8')

        return gotten.headers, output

    def validate_request_path(self, path_string):
        """Check the request path string.

        If it contains valid information return a URL to fetch.
        """
        parsed_path = dict(parse_qsl((urlparse(path_string)).query))

        if 'url' in parsed_path:
            url = parsed_path['url'].replace("%3A//", "://")

            if 'http' not in url:
                url = 'http://' + url

            if validators.url(url):
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.strip()
                try:
                    socket.gethostbyname(domain)
                except socket.gaierror:
                    return ('Non-existant domain: %s' % domain, None)
                else:
                    ProxyRequestHandler.sessionBaseURL = parsed_url.scheme \
                                            + '://' + parsed_url.netloc
                    if args.debug:
                        print('Setting base URL: %s' % self.sessionBaseURL)
            else:
                return ('Invalid URL: %s' % url, None)

        elif self.sessionBaseURL is not None:
            url = self.sessionBaseURL + self.path
            if args.debug:
                print('No domain in request, using session base URL: %s'
                      % ProxyRequestHandler.sessionBaseURL)
            if args.no_redirect is not True:
                return (301, url)
        else:
            return ('Invalid request: %s' % path_string, None)

        return (None, url)

    def do_GET(self):
        """Parse incomming requests, respond with data from do_fetch()."""
        status, url = self.validate_request_path(self.path)

        if status is None:
            if args.debug:
                print('Fetching: %s' % url)
            self.send_response(200)
            headers, body = self.get_url(url)
            self.send_header('Content-Type', headers['Content-Type'])
        elif status == 301:
            if args.debug:
                print('Redirecting to: %s' % url)
            self.send_response(301)
            self.send_header('Location', '/?url=' + url)
            body = None
        else:
            if args.debug:
                print(status)
                print('Aborting fetch.')
            self.send_response(400)
            body = status.encode('utf-8')

        self.end_headers()
        if body is not None:
            self.wfile.write(body)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Allow the proxy to use multiple threads."""


def start_daemon(args):
    """Start the proxy daemonized."""
    with daemon.DaemonContext(pidfile=daemon.pidfile.TimeoutPIDLockFile(args.pidfile)):
        worker(args)


def worker(args):
    """Start the proxy."""
    handler = ProxyRequestHandler

    try:
        server = ThreadedHTTPServer((args.listen_ip, args.listen_port), handler)
    except OSError:
        print('Error: could not open socket. (%s, %s)' % (args.listen_ip, args.listen_port))
        sys.exit(1)
    server.serve_forever()


if __name__ == '__main__':
    # get the default interface from the 'route' command
    default_interface = netifaces.gateways()['default'][netifaces.AF_INET][1]

    # setup default configuration
    defaults = {
        'listen_if': 'any',
        'listen_port': 8080,
        'exit_if': default_interface,
        'pidfile': '/tmp/cfscrape-http-proxy.pid',
        'config_file': 'cfscrape-proxy.conf',
        'no_redirect': False
        }

    config_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__, add_help=False)
    config_parser.add_argument(
        '-c', '--config_file', action='store', metavar='FILE',
        help='external configuration file')
    config_parser.add_argument(
        '--debug', action='store_true',
        help='turn on debug messaging')

    args = config_parser.parse_known_args()[0]

    # find external configuration
    if args.config_file is None:
        for config_file in (path.join(config_path, CONFIG_FILE) for config_path in CONFIG_PATHS):
            if path.isfile(config_file):
                if args.debug:
                    print('Found config file: %s' % config_file)
                args.config_file = config_file
                break

    # read external configuration if we've found it
    if args.config_file is not None and path.isfile(args.config_file):
        config = configparser.ConfigParser()
        config.read(args.config_file)
        defaults.update(dict(config.items("Defaults")))

        # config.read() makes everything a string but we need to set
        # some variables as integers or booleans. there's probably a
        # cleaner way to do this, but this works for now
        if config.has_option('Defaults', 'debug'):
            defaults['debug'] = config.getboolean('Defaults', 'debug')
        if config.has_option('Defaults', 'daemonize'):
            defaults['daemonize'] = config.getboolean('Defaults', 'daemonize')
        if config.has_option('Defaults', 'listen_port'):
            defaults['listen_port'] = config.getint('Defaults', 'listen_port')
        if config.has_option('Defaults', 'no_redirect'):
            defaults['no_redirect'] = config.getboolean('Defaults', 'no_redirect')
        if args.debug:
            print('read config file:\n%s' % json.dumps(defaults, indent=4))
    else:
        print('Error: config file (%s) does not exist, using defaults'
              % args.config_file)

    # parse command line arguments, overwriting both default config
    # and anything found in a config file
    parser = argparse.ArgumentParser(
        description='CloudFlare Anti-Bot HTTP Proxy', parents=[config_parser])
    parser.set_defaults(**defaults)
    parser.add_argument(
        '-l', '--listen_if', action='store', metavar='INTERFACE',
        help='interface to listen on (use \'any\' or \'0\' for all interfaces) '
              + '(default \'%(default)s\')')
    parser.add_argument(
        '-p', '--listen_port', action='store', type=int, metavar='PORT',
        help='port to listen on (default %(default)s)')
    parser.add_argument(
        '-e', '--exit_if', action='store', metavar='INTERFACE',
        help='interface for outgoing connections (default \'%(default)s\')')
    parser.add_argument(
        '-D', '--daemonize', action='store_true',
        help='run the proxy as a daemon')
    parser.add_argument(
        '-P', '--pidfile', action='store', metavar='FILE',
        help='PID file for daemon (default \'%(default)s\')')
    parser.add_argument(
        '-R', '--no_redirect', action='store_true',
        help='turn off redirects, prevent adding missing elements to URLs '
              + 'in the browser')
    args = parser.parse_args()

    if args.debug:
        print('parsed command line:\n%s' % json.dumps(vars(args), indent=4))

    args.listen_ip = get_interface_ip([args.listen_if, defaults['listen_if']])
    args.exit_ip = get_interface_ip([args.exit_if, defaults['exit_if']])

    if args.debug:
        print('startup configuration:\n%s' % json.dumps(vars(args), indent=4))

    # start the proxy
    if args.daemonize:
        print('Starting Cloudflare scrape proxy as daemon..')
        start_daemon(args)

    else:
        print('Starting Cloudflare scrape proxy..')
        worker(args)
