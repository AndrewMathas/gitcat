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

import git-cat

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
      long_description = git-cat.__doc__,
      url              = settings.url,
      author           = settings.author,
      author_email     = settings.author_email,

      keywords         = 'git, catalogue, repositories',

      packages=find_packages(),
      include_package_data=True,

      entry_points     = {'console_scripts': ['git-cat = git-cat:main', ],},

      license          = settings.licence,
      classifiers      = [
        'Development Status :: 5 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.7+',
      ]
)
