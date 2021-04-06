# -*- encoding: utf-8 -*-

r'''
-----------------------------------------------------------------------------------------
    setup | git-cat setuptools configuration

      - python3 setup.py build    :  build everything needed to install
      - python3 setup.py develop  :  install package in develop mode
      - python3 setup.py doc      :  build the README and manual files
      - python3 setup.py upload   :  upload to PyPi

    Copyright (C) Andrew Mathas

    Distributed under the terms of the GNU General Public License (GPL)
                  http://www.gnu.org/licenses/

    <Andrew.Mathas@gmail.com>
-----------------------------------------------------------------------------------------

Developer install:
    - python3 setup.py develop

Install:
    - python3 setup.py install

Build documention:
    - python3 setup.py doc

Upload to PyPI:
    - python3 setup.py sdist upload

'''

import os
import gitcat
import subprocess

from setuptools import setup, find_packages, Command

class Settings(dict):
    r"""
    A dummy class for reading and storing key-value pairs that are read from a file
    """
    def __init__(self, filename):
        super().__init__()
        with open(filename, 'r') as meta:
            for line in meta:
                key, val = line.split('=')
                if key.strip() != '':
                    setattr(self, key.strip().lower(), val.strip())

settings = Settings('gitcat.ini')

LICENSE='''
Author
......

{author} Mathas

`git cat`_ version {version}

Copyright (C) {copyright}

------------

GNU General Public License, Version 3, 29 June 2007

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License (GPL_) as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

.. _bitbucket: https://bitbucket.org/
.. _`git cat`: {repository}
.. _github: https://github.com
.. _GPL: http://www.gnu.org/licenses/gpl.html
.. _Python: https://www.python.org/
.. |version| image:: https://img.shields.io/github/v/tag/AndrewAtLarge/gitcat?color=success&label=version
.. |pyversion| image:: https://img.shields.io/badge/requires-python{python}%2B-important
.. |GPL3| image:: https://img.shields.io/badge/license-GPLv3-blueviolet.svg
   :target: https://www.gnu.org/licenses/gpl-3.0.en.html

'''

from gitcat import setup_command_line_parser, __doc__, settings as gitcat_settings

class GitCatDoc:
    r'''
    A helper class for generating the GitCat documentation. There are two
    main methods:

        - readme      -- generates the README.rst file
        - description -- generates the long description for uploading to PyPI

    with the only difference being that the README file also contains a
    description of each git cat commands. In turn, these methods call on a
    numbewr of helper commands that generate different parts of the
    documentation.
    '''
    def __init__(self):
        self.gitcat_doc = __doc__.split('******')
        self.parser, self.git_commands = setup_command_line_parser(gitcat_settings)

    def description(self):
        r'''
        Return an rst string for the long description when uploading to PyPI
        '''
        newline = '\n'
        return f'{self.rst_top()}{newline}{self.rst_bottom()}'

    def readme(self):
        r'''
        Return an rst string for the README file
        '''
        newline = '\n'
        return f'{self.rst_top()}{newline}{self.rst_commands()}{newline}{self.rst_bottom()}'

    def print_command_help(self, command):
        '''
        Print the help for this command with some formatting changes.
        Very hacky but it works...
        '''
        replacements = ['Example:', '*Example*:\n\n.. code-block:: bash\n',
                        'Examples:', '*Examples*:\n\n.. code-block:: bash\n',
                        '[STRATEGY]', '<STRATEGY>'
        ]
        help = self.git_commands.choices[command].format_help()
        rep = 0
        while rep < len(replacements):
            help = help.replace(replacements[rep], replacements[rep+1])
            rep += 2
        return help

    def rst_top(self):
        r'''
        Return a string for the top the rst file, which includes the heading
        '''
        newline = '\n'
        return f'{self.gitcat_doc[0]}{newline}{self.parser.format_help().replace("Commands:", f"Commands::{newline}")}{newline}{self.gitcat_doc[1]}'

    def rst_commands(self):
        r'''
        Return a string conrtaining a description of all of the gitcat commands.
        '''
        return '\n------------\n\n'.join(f'**git cat {cmd}**\n\n{self.print_command_help(cmd)}'
                 for cmd in self.git_commands.choices if cmd not in gitcat_settings.command_alias
        )

    def rst_bottom(self):
        r'''
        Return a string for the bottom the rst file, which includes the licence
        '''
        return LICENSE.format(
                author     = settings.author,
                copyright  = settings.copyright.split(' ')[0],
                python     = settings.python,
                repository = settings.repository,
                version    = settings.version
        )



class BuildDoc(Command):
    r'''
    Build the README and documentation for git-cat:

    > python3 setup doc
    '''
    description = 'Build the README and manual files'
    user_options = []

    def initialize_options(self):
        '''init options'''
        if not os.path.exists('man/man1'):
            os.makedirs('man/man1')

    def finalize_options(self):
        '''finalize options'''
        pass

    def run(self):
        '''
        This is where all of the work is done
        '''
        self.clean_doc_files()
        self.build_readme()
        self.build_manual()

    @staticmethod
    def clean_doc_files():
        '''
        remove all generated doc files
        '''
        for doc in ['README.rst', 'README.html', 'man/man1/git-cat.1']:
            try:
                os.remove(doc)
            except FileNotFoundError:
                pass

    def build_readme(self):
        '''
        Construct the README.rst file from the files in the doc directory and
        using gitcat.py --generate_help.
        '''
        doc = __doc__.split('******')
        with open('README.rst', 'w', newline='\n') as readme:
            readme.write(GitCatDoc().readme())

    @staticmethod
    def build_manual():
        '''
        Build the git-cat manual from the README file
        '''
        subprocess.run('rst2html5.py README.rst README.html', shell=True)
        subprocess.run('rst2man.py README.rst man/man1/git-cat.1', shell=True)

setup(name             = settings.program,
      version          = settings.version,
      description      = settings.description,
      long_description = GitCatDoc().description(),
      long_description_content_type='text/x-rst',
      url              = settings.url,
      author           = settings.author,
      author_email     = settings.author_email,

      keywords         = 'git, catalogue, repositories',

      cmdclass         = {'doc'   : BuildDoc},
      data_files       = [('man/man1', ['man/man1/git-cat.1'])],

      packages=find_packages(),
      python_requires=f'>={settings.python}',

      entry_points     = {'console_scripts': ['git-cat = gitcat:main', ],},

      license          = settings.licence,
      classifiers      = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        f'Programming Language :: Python :: {settings.python}',
        'Topic :: Software Development :: Version Control :: Git'
      ]
)
