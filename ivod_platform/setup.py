from setuptools import setup, find_packages


setup(
    name='ivod-platform',
    install_requires=['Django',
                      'djangorestframework',
                      'pive==0.3.202012161415'
                      ],
    dependency_links = ['git+ssh://git@github.com/internet-sicherheit/pive@static-js#egg=pive-0.3.202012161415']
)