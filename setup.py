# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.
import os
from setuptools import setup, find_packages


def get_long_description():
    long_description = open('README.md').read()
    try:
        import subprocess
        import pandoc

        process = subprocess.Popen(
            ['which pandoc'],
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)

        pandoc_path = process.communicate()[0]
        pandoc_path = pandoc_path.strip('\n')

        pandoc.core.PANDOC_PATH = pandoc_path

        doc = pandoc.Document()
        doc.markdown = long_description
        long_description = doc.rst
        open("README.rst", "w").write(doc.rst)
    except:
        if os.path.exists("README.rst"):
            long_description = open("README.rst").read()
        else:
            print("Could not find pandoc or convert properly")
            print("  make sure you have pandoc (system) and pyandoc (python module) installed")

    return long_description


setup(
    name='suitcase',
    version='0.8',
    url="https://github.com/digidotcom/python-suitcase",
    description='A library for specifying/parsing/packing binary protocols',
    long_description=get_long_description(),
    author="Paul Osborne",
    author_email="paul.osborne@digi.com",
    packages=find_packages(),
    keywords = ("suitcase, construct, declarative, dsl, protocol,"
                "binary, parser, builder, pack, unpack"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Software Development :: Libraries",
    ],
    install_requires=[
        "six",
    ],
)
