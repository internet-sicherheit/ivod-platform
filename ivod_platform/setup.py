from setuptools import setup
from pathlib import Path

HARDCODED_PIVE_VERSION = '0.3.202111251215'

setup(
    name='ivod-platform',
    packages=['ivod_platform', 'platformAPI'],
    install_requires=['Django==3.2.5',
                      'djangorestframework==3.12.4',
                      'django-cors-headers==3.7.0',
                      'django-filter==2.4.0',
                      'django-ratelimit==3.0.1',
                      'drf-jwt==1.19.1',
                      f'pive=={HARDCODED_PIVE_VERSION}',
                      ],
    dependency_links = [
        f'git+ssh://git@github.com/internet-sicherheit/pive@develop#egg=pive-{HARDCODED_PIVE_VERSION}',
        ''.join(['file://', str(Path(__file__).resolve().parent.joinpath(f'pive#egg=pive-{HARDCODED_PIVE_VERSION}'))])
    ]
)