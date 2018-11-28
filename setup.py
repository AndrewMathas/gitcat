# -*- encoding: utf-8 -*-

r'''
-----------------------------------------------------------------------------------------
    setup | git-cat setuptools configuration

    Copyright (C) Andrew Mathas

    Distributed under the terms of the GNU General Public License (GPL)
                  http://www.gnu.org/licenses/

    <Andrew.Mathas@gmail.com>
-----------------------------------------------------------------------------------------
'''

from setuptools import setup, find_packages, Command
import gitcat
import os
import subprocess

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

class BuildDoc(Command):
    r'''
    Build the README and documentation for git-cat
    '''
    description = 'Build the README and manual files'
    user_options = []

    def initialize_options(self):
         """init options"""
         pass

    def finalize_options(self):
         """finalize options"""
         pass

    def run(self):
        '''
        This is where all of the work is done
        '''
        self.clean_doc_files()
        self.build_readme()
        self.build_manual()

    def clean_doc_files(self):
        '''
        remove all generated doc files
        '''
        for doc in ['README.rst', 'README.html', 'git-cat.1']:
            try:
                os.remove(doc)
            except FileNotFoundError:
                pass

    @staticmethod
    def print_help(help):
        '''
        Print the help for this command with some formatting changes.
        Very hacky but it works...
        '''
        replacements = ['Example:', '*Example*:\n\n.. code-block:: bash\n',
                        'Examples:', '*Examples*:\n\n.. code-block:: bash\n',
                        '[STRATEGY]', '<STRATEGY>'
        ]
        rep=0
        while rep < len(replacements):
            help = help.replace(replacements[rep], replacements[rep+1])
            rep += 2
        return help

    def build_readme(self):
        '''
        Construct the README.rst file from the files in the doc directory and
        using gitcat.py --generate_help.
        '''
        from gitcat import setup_command_line_parser, __doc__
        doc = __doc__.split('----')
        parser, commands = setup_command_line_parser()
        with open('README.rst','w', newline='\n') as readme:
            readme.write(doc[0]) # README header
            readme.write(parser.format_help().replace('Commands:','Commands::\n')+'\n')
            readme.write(self.print_help(doc[1])) # README blurb
            for cmd in commands.choices:
                readme.write('\n------------\n\n**{}**\n\n'.format(cmd))
                readme.write(self.print_help(commands.choices[cmd].format_help()))
            readme.write(doc[2]) # README end
            readme.write('.. _gitcat: {}'.format(settings.repository))

    def build_manual(self):
        '''
        Build the git-cat manual from the README file
        '''
        subprocess.run('rst2html5.py README.rst README.html', shell=True)
        subprocess.run('rst2man.py README.rst git-cat.1', shell=True)

setup(name             = settings.program,
      version          = settings.version,
      description      = settings.description,
      long_description = gitcat.__doc__,
      url              = settings.url,
      author           = settings.author,
      author_email     = settings.author_email,

      keywords         = 'git, catalogue, repositories',

      cmdclass         = {'doc'   : BuildDoc},
      data_files       = [('man/man1', ['git-cat.1'])],

      packages=find_packages(),
      python_requires='>=3.7',

      entry_points     = {'console_scripts': ['git-cat = gitcat:main', ],},

      license          = settings.licence,
      classifiers      = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7+',
        'Topic :: Software Development :: Version Control :: Git'
      ]
)
