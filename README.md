# Cloudflare Anti-Bot HTTP Proxy
A basic HTTP proxy in Python, implementing [VeNoMouS' cloudscraper][cloudscraper] module.

## Installation
Clone this repo, cd into the repo folder and then use `setup.py` to install:

```
sudo python setup.py install
```

Optionally, install [python-prctl][python-prctl]. This will alow the proxy to change its process name as displayed in ps, netstat and other such software to make it easier to see what the proxy is doing:

```
sudo pip install python-prctl
```

**Note:** python-prctl requires gcc, libc development headers and libcap development headers to be installed in the operating system. See the [python-prctl docs][python-prctl-docs] for details.

If you're installing this on a router and are using Entware you may need to install some Python modules with `opkg`, for example:
```
opkg install python-requests
opkg install node_legacy
```

### Compatibility
The proxy should run on most linux distros and has been tested on:

-   Ubuntu Bionic
-   Armbian (Debian) Stretch
-   ASUSWRT-Merlin / Entware

The proxy won't run on Windows due to differences in handling network interfaces and sockets.

## Usage
```
usage: cfscrape-http-proxy [-h] [-c FILE] [--debug] [-l INTERFACE] [-p PORT]
                           [-e INTERFACE] [-D] [-P FILE]

CloudFlare Anti-Bot HTTP Proxy

optional arguments:
  -h, --help            show this help message and exit
  -c FILE, --config_file FILE
                        external configuration file
  --debug               turn on debug messaging
  -l INTERFACE, --listen_if INTERFACE
                        interface to listen to (use 'any' or '0' to listen to all interfaces) (default 'any')
  -p PORT, --listen_port PORT
                        port to listen on (default 8080)
  -e INTERFACE, --exit_if INTERFACE
                        interface for outgoing connections (default <default>)
  -D, --daemonize       run the proxy as a daemon
  -P FILE, --pidfile FILE
                        PID file for daemon (default '/tmp/cfscrape-http-proxy.pid')
  -R, --no_redirect     turn off redirects, prevent adding missing elements to URLs in the browser

```
Command line parameters override default settings and any settings from a configuration file. An external configuration file specified on the command line will override a configuration file installed in the system config path (typically `/etc/`, or possibly `/opt/etc/` by default).

Once the proxy is running it can be used by accessing it via HTTP with the page you wish to proxy included as the `url` GET variable:
```
http://<proxy_server_IP>:<proxy_port>/?url=<target_page>
```

Example: `http://192.168.0.10:8080/?url=www.news.com.au/content-feeds/latest-news-world/`

## Configuration
The config file (called `cfscrape-http-proxy.conf` by default, but can be changed via the command line) uses the same names for paramaters as the command line. As an example, a configuration file for use on a router with distinct LAN (br0) and WAN (eth0) interfaces:

```
[Defaults]
listen_if=br0
port=8080
exit_if=eth0
daemoinze=True
pidfile=/tmp/cfscrape-http-proxy.pid
no_redirect=False
```

The proxy will search several paths for a configuration file if none is specified on the command line. If you're running Entware it should be at `/opt/etc/cfscrape-http-proxy.conf`, otherwise it should probably be at `/etc/cfscrape-http-proxy.conf`.

The default exit interface (shown as `<default>` in the usage above), used if nothing is specified in the config file or on the command line, will vary from one system to another. The proxy determines the default by looking at the routing table.

The `no_redirect` flag will make the proxy faster by not sending HTTP 301 responses to add `?url=http://<domain>/` to the beginning of requests that don't include it (i.e. relative URLs in links on a web page), but it may make browsing web pages through the proxy buggier. It's a trade between speed and robustness, you can experiment to see which you prefer.

## Notes
Installing with pip (`sudo pip install .`) ends up putting the config and init files inside Python's `site-packages` path rather than the root path. This is apparently because it's installing from a bdist, but also because I don't really know how to work setuptools properly. :)

[cloudscraper]: https://github.com/VeNoMouS/cloudscraper
[python-prctl]: https://github.com/seveas/python-prctl
[python-prctl-docs]: https://pythonhosted.org/python-prctl/
