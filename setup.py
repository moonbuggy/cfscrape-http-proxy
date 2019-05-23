#!/usr/bin/env python

from setuptools import setup
from os import path
import subprocess

## determine appropriate location for configuration file
CONFIG_PATHS = ['/opt/etc/',
                '/etc/',
                '/usr/local/etc/',
                ]

data_files = None

for config_path in CONFIG_PATHS:
    if path.isdir(config_path):
        data_files = [(config_path, ['cfscrape-http-proxy.conf'])]
        break;

print('config_path: %s' % config_path)
#print('data_files: %s' % dict(data_files))

## determine service manager in use
if path.isfile('/opt/etc/entware_release'):
    data_files.append(('/opt/etc/init.d/', ['init/S90cfscrape-http-proxy']))
else:
    service_manager = subprocess.Popen("ls -l /proc/1/exe | awk '{print $NF}' | tr -d '\n'", shell=True, universal_newlines=True, stdout=subprocess.PIPE).stdout.read()
    print('service_manager: %s' % service_manager)
    if service_manager == '/lib/systemd/systemd':
        # systemd
        print('Detected systemd.')
        data_files.append(('/lib/systemd/system/', ['init/cfscrape-http-proxy.service']))
    elif service_manager is '/sbin/init':
        # sysV
        print('Detected SysV.')
        data_files.append(('/etc/init.d/', ['init/cfscrape-http-proxy']))
    elif service_manager is 'upstart':
        # upstart (we don't have a tested init script for upstart)
        print('Detected upstart, no init script available.')
    else:
        # unknown
        print('No service manager detected, no init script installed.')

print('data_files: %s' % dict(data_files))

setup(name='cfscrape_http_proxy',
      version='0.1',
      description='An HTTP proxy that bypasses basic Cloudflare anti-bot pages',
      url='http://github.com/moonbuggy/cfsrape-http-proxy',
      author='moonbuggy',
      author_email='3319867+moonbuggy@users.noreply.github.com',
      install_requires=[
        'cfscrape',
        'daemons',
        'nodejs',
        'requests',
        'requests-toolbelt',
        'setuptools',
        'validators',
      ],
      extras_require={
        'prctl': ["python-prctl"],
      },
      scripts=['cfscrape-http-proxy'],
      data_files=data_files,
      zip_safe=False)
