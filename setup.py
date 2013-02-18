#!/usr/bin/env python3
# coding: UTF-8
#
# Copyright © 2012, Elizabeth J. Myers, et al. All rights reserved.
# License terms can be found in the LICENSE file at the top level of the source
# tree.

from setuptools import setup, find_packages
from os import listdir
from os.path import isdir, join

PKGNAME='irclib'

setup(name=PKGNAME,
      description='an IRC lib for Python',
      author='Elizabeth Myers',
      author_email='elizabeth@sporksmoo.net',
      url='http://github.com/Elizacat/irclib',
      license='BSD',
      version='0.01-alpha',
      keywords=['irc', 'protocol'],
      packages=find_packages(),
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'License :: WTFPL',
          'Natural Language :: English',
          'Operating System :: Microsoft',
          'Operating System :: Unix',
          'Operating System :: POSIX',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Topic :: Internet',
          'Topic :: Communications :: Chat :: Internet Relay Chat',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ]
)
