from setuptools import setup, find_packages
import os
from pathlib import Path


setup(
    name='ivod-platform',
    packages=['ivod_platform', 'platformAPI', 'platformFrontend'],
    install_requires=['Django',
                      'djangorestframework',
                      'django-cors-headers',
                      'pive==0.3.202012171300'
                      ],
    dependency_links = [
        'git+ssh://git@github.com/internet-sicherheit/pive@static-js#egg=pive-0.3.202012171300',
        ''.join(['file://', str(Path(__file__).resolve().parent.joinpath('pive#egg=pive-0.3.202012171300'))])
    ]
)