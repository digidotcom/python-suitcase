from distutils.core import setup
from setuptools import find_packages

setup(
  name='pacman',
  version='0.4',
  description='A library for specifying/parsing binary protocols',
  long_description=open('README.txt').read(),
  author="Paul Osborne",
  author_email="paul.osborne@spectrumdsi.com",
  packages=find_packages(),
)
