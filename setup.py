# -*- encoding: utf-8 -*-

r'''
-----------------------------------------------------------------------------------------
    setup | git-cat setuptools configuration
-----------------------------------------------------------------------------------------
    Copyright (C) Andrew Mathas

    Distributed under the terms of the GNU General Public License (GPL)
                  http://www.gnu.org/licenses/

    <Andrew.Mathas@gmail.com>
-----------------------------------------------------------------------------------------
'''

from setuptools import setup, find_packages
import gitcat

class Settings(dict):
    r"""
    A dummy class for reading and storing key-value pairs that are read from a file
    """
    def __init__(self, filename):
        with open(filename,'r') as meta:
            for line in meta:
                key, val = line.split('=')
                if len(key.strip())>0:
                    setattr(self, key.strip().lower(), val.strip())

settings = Settings('gitcat.ini')

setup(name             = settings.program,
      version          = settings.version,
      desription       = settings.description,
      long_description = gitcat.__doc__,
      url              = settings.url,
      author           = settings.author,
      author_email     = settings.author_email,

      keywords         = 'git, catalogue, repositories',

      packages=find_packages(),
      include_package_data=True,
      python_requires='>=3',

      entry_points     = {'console_scripts': ['git-cat = gitcat:main', ],},

      license          = settings.licence,
      classifiers      = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.7+',
        'Topic :: Software Development :: Version Control :: Git'
      ]
)
