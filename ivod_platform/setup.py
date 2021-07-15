from setuptools import setup, find_packages
import os
from pathlib import Path

HARDCODED_PIVE_VERSION = '0.3.202106161145'

setup(
    name='ivod-platform',
    packages=['ivod_platform', 'platformAPI', 'platformFrontend'],
    install_requires=['Django',
                      'djangorestframework',
                      'django-cors-headers',
                      'django-filter',
                      'aiosmtpd',
                      #'djangorestframework-simplejwt',
                      'django-ratelimit',
                      'drf-jwt',
                      f'pive=={HARDCODED_PIVE_VERSION}',
                      ],
    dependency_links = [
        f'git+ssh://git@github.com/internet-sicherheit/pive@develop#egg=pive-{HARDCODED_PIVE_VERSION}',
        ''.join(['file://', str(Path(__file__).resolve().parent.joinpath(f'pive#egg=pive-{HARDCODED_PIVE_VERSION}'))])
    ]
)