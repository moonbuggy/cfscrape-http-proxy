#!/usr/bin/env python

"""
setup.py for cfscrape-http-proxy.

Determine the init system in use, copy files as required.
"""

import subprocess
import shutil
from os import path
from setuptools import setup

# determine appropriate location for configuration file
CONFIG_PATHS = [
        '/opt/etc/',
        '/etc/',
        '/usr/local/etc/'
    ]

data_files = []

for config_path in CONFIG_PATHS:
    if path.isdir(config_path):
        data_files = [(config_path, ['cfscrape-http-proxy.conf'])]
        break

print(f'config_path: {config_path}')

# determine service manager in use
if path.isfile('/opt/etc/entware_release'):
    data_files.append(('/opt/etc/init.d/', ['init/S90cfscrape-http-proxy']))
else:
    # service_manager = subprocess.Popen("ls -l /proc/1/exe | awk '{print $NF}' | tr -d '\n'",
    #                                    shell=True,
    #                                    universal_newlines=True,
    #                                    stdout=subprocess.PIPE).stdout.read()
    with subprocess.Popen("ls -l /proc/1/exe | awk '{print $NF}' | tr -d '\n'",
                          shell=True,
                          universal_newlines=True,
                          stdout=subprocess.PIPE) as service_manager_object:
        assert service_manager_object.stdout is not None
        service_manager = service_manager_object.stdout.read()

    print(f'service_manager: {service_manager}')
    if service_manager == '/lib/systemd/systemd':
        # systemd
        print('Detected systemd.')
        data_files.append(('/lib/systemd/system/', ['init/cfscrape-http-proxy.service']))
    elif service_manager == '/sbin/init':
        # sysV
        print('Detected SysV.')
        data_files.append(('/etc/init.d/', ['init/cfscrape-http-proxy']))
    elif service_manager == 'upstart':
        # upstart (we don't have a tested init script for upstart)
        print('Detected upstart, no init script available.')
    else:
        # unknown
        print('No service manager detected, no init script installed.')

print(f'data_files: {dict(data_files)}')

shutil.copyfile('cfscrape-http-proxy.py', 'cfscrape-http-proxy')

setup(name='cfscrape_http_proxy',
      version='0.5',
      description='An HTTP proxy that bypasses basic Cloudflare anti-bot pages',
      url='http://github.com/moonbuggy/cfsrape-http-proxy',
      author='moonbuggy',
      author_email='3319867+moonbuggy@users.noreply.github.com',
      install_requires=[
        'cloudscraper',
        'netifaces',
        'nodejs',
        'python-daemon',
        'requests',
        'requests-toolbelt',
        'setuptools',
        'validators',
        'future',
      ],
      extras_require={
        'prctl': ["python-prctl"],
      },
      scripts=['cfscrape-http-proxy'],
      data_files=data_files,
      zip_safe=False)
