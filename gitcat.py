#!/usr/bin/env python3
r'''|version|
|pyversion|
|GPL3|

==========
`git cat`_
==========

*Herding a catalogue of git repositories*

******

`git cat`_ is a command line tool for synchronising multiple git repositories
with remote servers from the command line. This tool is not intended to be used
on large projects with multiple developers but, instead, it is aimed at the
lone developer who has wants to synchronise multiple git repositories that live
on several computers. In particular, with one `git cat`_ command you can run git
commands on multiple git repositories, such as pushing or pulling from remote
servers, such as bitbucket_ and github_. When pushing, any local changes to the
repositories will be automatically commited.

`git cat`_ provides only a thin veneer over git. It does not support all git
commands and nor does it support the full functionality of those git commands
that it does support. The `git cat`_ philosophy is to "do no harm" so, when
possible, it uses dry-runs before changing any repository and it will only
change a repository if the dry-run succeeds. Any problems encountered by `git
cat` are printed to the terminal (stdout). The aim of `git cat`_ is to
streamline the management of multiple git repositories so, by default, it
prints a summary of what it does to each repository to the terminal.

By default, the `git cat`_ commands are applied to all of the repositories that
are managed by `git cat`, however, repositories that the command is applied to
by supplying a regular expression.

Examples:
    > git cat pull       # pull from all repositories
    > git cat pull Code  # pull from all "Code" repositories

This makes it possible, for example, to push or pull from related git
repositories that are in different directories.

The remote repositories are accessed in the normal way using git. Ideally, they
will be set up with ssh access so that passwords are not required. If git
requires a password for a repository then you will be prompted to supply it in
the usual way.

.. warning::
   `git cat`_ is designed to automatically push and pull git repositories. It will
   commit any uncomitted changes to your repositories and so should be used
   with care. Any unintended changes to your repositories should be recoverable
   using standard git commands. I have used `git cat`_ without problem since
   2018 but there is always a chance that something may go wrong, so use at
   your won risk.

The gitcatrc file
.................

The gitcatrc file contains the catalogue of repositories maintained by `git
cat`. This file will be stored in the directory ~/.dotfiles/config, if it
exists, and otherwise it defaults to `~/.gitcatrc`. This location of this file
can be changed from the command line using the `-c` command line option.

The `git cat`_ commands are only applied to those repositories that have been
"installed" using `git cat install`. Consequently, if the gitcatrc file is
itself in a git repository then different computers that use this file can
synchronise different repositories using `git cat`.

'''

r'''
Author
......

Andrew Mathas

`git cat`_ Version 1.0

Copyright (C) 2018-2020

------------

GNU General Public License, Version 3, 29 June 2007

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License (GPL_) as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.
'''

# flag to enable argparse autocompletion if argcomplete is installed
# PYTHON_ARGCOMPLETE_OK

# ---------------------------------------------------------------------------
# TODO:
#  - debugging and testing...
#  - add a "git cat --set-as-defaults cmd [options]" option to set defaults
#     for a given command and then store the information into the gitcatrc
#     file. Will need to be clever to avoid code duplication...possibly add all
#     of the command-line options to the settings class and then use it to
#     automatically generate the command line options
#  - add options for sorting catalogue
#  - make status check that changes have been pushed
#  - add a fast option
#  - add exclude option
#  - use parallel processing
#  - ? add a "git cat git" command
#  - ? make "git cat pull" first update the repository containing the gitcatrc file and
#     then reread it

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import textwrap

from difflib import get_close_matches

try:
    import argcomplete
except ImportError:
    argcomplete = False

# ---------------------------------------------------------------------------
import socket
REMOTE_SERVER = "www.google.com"
def connected_to_internet(hostname=REMOTE_SERVER):
  try:
    # see if we can resolve the host name -- tells us if there is
    # a DNS listening
    host = socket.gethostbyname(hostname)
    # connect to the host -- tells us if the host is actually
    # reachable
    s = socket.create_connection((host, 80), 2)
    s.close()
    return True
  except:
     pass
  return False

# compiled regular expressions

# [ahead 1], or [behind 1] or [ahead # 2, behind 1] in status
ahead_behind = re.compile(r'\[((ahead|behind) [0-9]+(, )?)+\]')

# list of files that have changed
files_changed = re.compile(r'([0-9]+ file(?:s|))(?: changed)')

# section in an ini file
ini_section = re.compile(r'^\[([-a-zA-Z]*)\]$')


# ---------------------------------------------------------------------------
class Settings(dict):
    r"""
    A class for reading and saving the gitcat settings and supported git
    command line options.
    """
    DEBUGGING = False

    def __init__(self, ini_file, git_options_file):
        super().__init__()

        self.prefix = os.environ['HOME']
        self.quiet = False      # defaults
        self.dry_run = False

        # store a dictionary of aliases for the git cat command
        self.command_alias = {}

        # location of the gitcatrc file defaults to ~/.dotfiles/config/gitcatrc
        # and then to ~/.gitcatrc
        if os.path.isdir(os.path.expanduser('~/.dotfiles/config')):
            self.rc_file = os.path.expanduser('~/.dotfiles/config/gitcatrc')
        if not (os.path.isfile(self.rc_file) or hasattr(self, 'rc_file')):
            self.rc_file = os.path.expanduser('~/.gitcatrc')

        # read gitcat ini file, which gives data about gitcat
        self.read_ini_file(ini_file)

        self.commands = {}
        self.read_git_options(git_options_file)

        # save the default options
        self.default_options = {}  # will hold non-standard git defaults
        for cmd in self.commands:
            self.default_options[cmd] = {}
            for option in self.commands[cmd]:
                if 'default' in self.commands[cmd][option]:
                    self.default_options[cmd][option] = self.commands[cmd][option]['default']

    @staticmethod
    def doc_string(cmd):
        '''
        Return a sanitised version of the doc-string for the method `cmd` of
        `GitCat`. In particuar, all code-blocks are removed.
        '''
        return textwrap.dedent(getattr(GitCat, cmd.replace('-','_')).__doc__)

    def add_git_options(self, commands):
        '''
        Generate all of the `git cat` command options as parsers of `commands`
        '''
        for cmd in self.commands:
            aliases = [ self.commands[cmd]['alias'] ] if 'alias' in self.commands[cmd] else []
            for c in range(3, len(cmd)):
                self.command_alias[cmd[:c]] = cmd
                aliases.append(cmd[:c])

            command = commands.add_parser(
                cmd,
                aliases=aliases,
                help=self.commands[cmd]['description'],
                description=self.commands[cmd]['description'],
                formatter_class=argparse.RawTextHelpFormatter,
                epilog=self.doc_string(cmd)
            )
            for option in self.commands[cmd]:
                if option not in self.special_options:
                    if 'short-option' in self.commands[cmd][option]:
                        options = self.commands[cmd][option].copy()
                        short_option = options['short-option']
                        del options['short-option']
                        debugging('short option = {short_option}.')
                        if short_option is None:
                            command.add_argument('--' + option, **options)
                        else:
                            command.add_argument('-' + short_option,
                                                 '--' + option, **options)
                    else:
                        command.add_argument('-' + option[:1], '--' + option,
                                             **self.commands[cmd][option])

            # finally, add the optional repository filter option
            if 'directory' not in self.commands[cmd]:
                command.add_argument(
                    dest='repositories',
                    type=str,
                    default='',
                    nargs='?',
                    help='optionally filter repositories for status')

            # add a quiet option
            command.add_argument(
                '-q', '--quiet',
                default=False,
                action='store_true',
                help='only print "important" messages')

    def read_ini_file(self, ini_file):
        '''
        Read and store the information in the ini file
        '''
        with open(ini_file, 'r') as ini:
            for line in ini:
                key, val = [w.strip() for w in line.split('=')]
                if key != '':
                    if '.' in key:
                        command, option = key.split('.')
                        if command not in self.git_defaults:
                            self.git_defaults[command] = {}
                        self.git_defaults[command][option] = val
                    else:
                        setattr(self, '_' + key.lower(), val)

    # list options that are not passed to git
    special_options = ['alias', 'description']

    def read_git_options(self, options_file):
        '''
        Read and store the information in the command-line options file
        '''
        with open(options_file, 'r') as options:
            for line in options:
                match = ini_section.search(line.strip())
                if match:
                    # line is an ini section of the form: [command]
                    # set command and initialise to an empty dictionary
                    command = match.groups()[0]
                    self.commands[command] = {}

                elif not line.startswith('#') and '=' in line:

                    choices = [c.strip() for c in line.split('=')]
                    if len(choices) == 3:
                        # initial option line for current command which is
                        # of the form: opt = <help message> = <default value>
                        opt = choices[0]
                        default = choices[2]
                        option = dict(help=choices[1])
                        if opt.startswith('*'):
                            opt = opt[1:]
                            option['short-option'] = None

                        try:
                            option['default'] = eval(default)
                        except (NameError, SyntaxError, TypeError):
                            option['default'] = default.strip()
                        if isinstance(option['default'], bool):
                            option['action'] = 'store_{}'.format(str(not option['default']).lower())
                        if isinstance(option['default'], str):
                            option['type'] = str

                        # dest could be overwritten later in the ini file
                        option['dest'] = 'git_' + opt.replace('-', '_')
                        self.commands[command][opt] = option
                    elif len(choices) == 2:
                        # description of command or extra specifications for the current option
                        if choices[0] in self.special_options:
                            self.commands[command][choices[0]] = choices[1]
                        else:
                            try:
                                self.commands[command][opt][choices[0]] = eval(choices[1])
                            except (NameError, SyntaxError, TypeError, KeyError):
                                self.commands[command][opt][choices[0]] = choices[1]
                    else:
                        error_message(f'syntax error in {options_file} on the line\n {line}')

    def save_settings(self):
        r'''
        Return a string for setting the non-standard settings in the gitcatrc file
        '''
        save_settings = ''
        if self.prefix != os.environ['HOME']:
            save_settings += f'prefix = {self.prefix}\n'

        if save_settings !='':
            return '\n'+save_settings+'\n'
        return ''

    def version(self):
        """ return gitcat version """
        return f'git cat version {self._version}'


file = lambda f: os.path.join(os.path.dirname(__file__), f)
settings = Settings(file('gitcat.ini'), file('git-options.ini'))


# ---------------------------------------------------------------------------
# error messages and debugging
def error_message(err):
    r'''
    Print error message and exit.
    '''
    print(f'git cat error: {err}')
    sys.exit(1)


def debugging(message):
    """ print a debugging message if `debugging` is true"""
    if settings.DEBUGGING:
        print(message)


# ---------------------------------------------------------------------------
def graceful_exit(sig, frame):
    ''' exit gracefully on SIGINT and SIGTERM '''
    print(f'program terminated (signal {sig})')
    debugging(f'{frame}')
    sys.exit()


signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

# ---------------------------------------------------------------------------
# running git commands using subprocess
class Git:
    """
    Container class for running a git command and printing an
    error message if necessary.

    Usage: Git(rep, command, options)

    where
     - rep     is the key for the repository being processed
     - command is the main git command being run
     - options are the options to the git commend

    The class that is return has attributes:
     - rep        the catalogue key for the respeoctory
     - returncode the return code from the subprocess command
     - output     the stdout and stderr output from the subprocess command
    """

    def __init__(self, rep, command, options=''):
        """ run a git command and wrap the return values for later use """
        git = subprocess.run(f'git {command} {options}'.strip(), shell=True, capture_output=True)

        # store the output
        self.rep = rep
        self.returncode = git.returncode
        self.command = command + ' ' + options

        if self.returncode != 0:
            self.error_message = '{}: there was an error using git {} {}\n  {}\n'.format(
                rep,
                command,
                options,
                git.stderr.decode().strip().replace('\n', '\n  ').replace(
                    '\r', '\n  '),
            )
            print(self.error_message)
            debugging('{line}{err}{line}'.format(line='-' * 40, err=self.error_message))
            self.git_command_ok = False
        else:
            self.git_command_ok = True

        # output is indented two spaces and has no blank lines
        self.output = '\n'.join('  ' + lin.strip() for lin in (
            git.stdout.decode().replace('\r', '\n').strip().split('\n') +
            git.stderr.decode().replace('\r', '\n').strip().split('\n'))
                                if lin != '')
        debugging(f'{self}\nstdout={git.stdout}\nstderr={git.stderr}')

    def __bool__(self):
        ''' return 'self.is_ok` '''
        return self.git_command_ok

    def __repr__(self):
        """ define a __repr__ method for debugging """
        return 'Git({})\n  rep={}, OK={}, returncode={}\n  output={}.'.format(
            self.command,
            self.rep,
            self.git_command_ok,
            self.returncode,
            self.output.replace('\n', '\n  '),
        )


# ---------------------------------------------------------------------------
class GitCat:
    r"""
    Usage: GitCat(options, settings)

    A class for reading, accessing and storing details of the different git
    repositories. These are stored in `filename` in the form:

       directory1 = repository1
       directory2 = repository2
       ...

    Any lines without a key-value pair are ignored.
    """

    def __init__(self, options, settings):
        self.gitcatrc = options.catalogue
        self.options = options
        self.prefix = options.prefix

        for opt in ['dry_run', 'quiet']:
            setattr(self, opt, getattr(settings, opt))
            if hasattr(options, opt):
                setattr(self, opt, getattr(options, opt))
            if hasattr(options, 'git_'+opt):
                setattr(self, opt, getattr(self, opt) or getattr(options, 'git_'+opt))

        # read the catalogue from the rc file
        self.read_catalogue()

        # run corresponding command - but allow short hands
        command = options.command.replace('-','_')
        bad_command = True
        try:
            getattr(self, command)()
            bad_command = False

        except AttributeError:
            try:
                getattr(self, settings.command_alias[command])()
            except KeyError:
                # should not ever reach this branch as argparse should give
                # a usage error first
                pass

        except Exception as err:
            error_message(f'unknown error: {err}')

        if bad_command:
            error_message(f'unrecognised command: {command}')


    @staticmethod
    def changed_files(rep):
        r'''
        Return list of files repository in the current directory that have
        changed.  We assume that we are in a git repository.
        '''
        return Git(rep, 'diff-index', '--name-only HEAD')

    def commit_repository(self, rep):
        r'''
        Commit the files in the repository in current working directory.
        The commit message is a list of the files being changed. Return
        the Git() record of the commit.
        '''
        debugging('\nCOMMIT rep=' + rep)
        changed_files = self.changed_files(rep)
        if changed_files and changed_files.output != '':
            commit_message = 'git cat: updating ' + changed_files.output
            options = f'--all --message="{commit_message}"'
            if self.dry_run:
                options += ' --porcelain' # implies --dry-run
            return Git(rep, 'commit', options)

        return changed_files

    def connected_to_internet(self, operation):
        r'''
        If we are connected to the internet then return `True`. Otherwise print
        and error message and exit.
        '''
        if connected_to_internet():
            return True

        print(f'Unable to {operation}. Please check your internet connection')
        return False

    def expand_path(self, dire):
        r'''
        Return the path to the directory `dire`, adding `self.prefix` if
        necessary.
        '''
        return dire if dire.startswith('/') else os.path.join(self.prefix, dire)

    def get_current_git_root(self):
        r'''
        Return the root directory of the git repository that contains the
        current working directory.
        '''
        if hasattr(self.options, 'repositry') and self.options.repository is not None:
            dire = self.short_path(os.path.expanduser(self.options.repository))
        else:
            dire = self.short_path(os.getcwd())
        dire = self.expand_path(dire)

        if not (os.path.isdir(dire) and self.is_git_repository(dire)):
            error_message(f'{dire} not a git repository')

        # find the root directory for the repository and the remote URL`
        os.chdir(dire)
        root = Git(dire, 'root')
        if not root:
            error_message(f'{dire} is not a git repository:\n  {root.output}')
        return root

    def is_git_repository(self, dire):
        r'''
        Return `True` if `dire` is a git repository and `False` otherwise. As
        part of testing for a repository the current working directory is also
        changed to `dire`.
        '''
        debugging(f'\nCHECKING for git dire={dire}')
        if os.path.isdir(dire):
            os.chdir(dire)
            rep = dire.replace(self.prefix + '/', '')
            is_git = Git(rep, 'rev-parse', '--is-inside-work-tree')
            return is_git.returncode == 0 and 'true' in is_git.output

        return False

    def list_catalogue(self, listing):
        r'''
        Return a string that lists the repositories in the catalogue. If
        `listing` is `False` and the repository does not exist then the
        separator is an exclamation mark, otherwise it is an equals sign.
        '''
        return '\n'.join('{dire:<{max}} {sep} {rep}'.format(
            dire=dire,
            rep=self.catalogue[dire],
            sep='=' if listing or self.
            is_git_repository(self.expand_path(dire)) else '!',
            max=self.max) for dire in self.repositories())

    def move(self, position):
        r'''
        Move current repository to position `position` in the catalogue.
        If `position` is negative then we count from the end of the repository.
        Therefore,

            git cat move -1

        moves the current repository to the end of the catalogue.
        '''
        dire = self.get_current_git_root()
        rep = Git(dire, 'remote', 'get-url --push origin')
        if not rep:
            error_message(f'Unable to find remote repository for {dire}')
        dire = self.short_path(dire.output.strip())
        if dire in self.catalogue:
            # as is usual in python, negatives count backwards
            if position<0:
                position += len(self.catalogue.keys())
            reps = list(self.catalogue.keys())
            dire_pos = reps.index(dire)
            if dire_pos != position:
                # make a copy of the catalogue and then recreate it
                cat = self.catalogue.copy()
                self.catalogue = {}
                pos = 0
                delta = 0
                for pos in range(len(cat.keys())):
                    if pos == position:
                        self.catalogue[dire] = cat[dire]
                        delta = -1 if position<dire_pos else 0
                    else:
                        self.catalogue[reps[pos+delta]] = cat[reps[pos+delta]]
                    if pos == dire_pos:
                        delta = 1 if position>dire_pos else 0
                self.save_catalogue()
        else:
            error_message(f'The git repository {dire} is not in the catalogue')

    def process_options(self, default_options=''):
        r'''
           Set the command line options starting with `default_options` and
           then checking the command list options against the list of options
           in `options_list`
        '''
        options = default_options
        for option in vars(self.options):
            if option.startswith('git_'):
                opt = option[4:].replace('_', '-')
                val = getattr(self.options, option)
                if val is True:
                    options += ' --' + opt
                elif isinstance(val, list):
                    options += ' --{}={}'.format(opt, ','.join(val))
                elif isinstance(val, str):
                    options += ' --{}={}'.format(opt, val)
                else:
                    debugging(f'option {option}={val} ignored')
        return options

    def read_catalogue(self):
        r'''
        Read the catalogue of git repositories to sync. These are stored in the
        form:

           directory1 = repository1
           directory2 = repository2
           ...

        and then put into the dictionary self.catalogue with the directory as
        the key. Any lines that do not contain an equal sign are ignored.
        '''
        self.catalogue = {}
        try:
            reading_settings = True
            with open(self.gitcatrc, 'r') as catalogue:
                for line in catalogue:
                    if line.strip() == 'Catalogue:':
                        reading_settings = False

                    if ' = ' in line:
                        dire, rep = line.split(' = ')
                        dire = dire.strip()
                        rep = rep.strip()
                        if reading_settings:
                            if hasattr(self, dire):
                                setattr(self, dire, rep)
                            elif hasattr(self.options, dire):
                                setattr(self.options, dire, rep)
                            else:
                                self.message(f'bad setting "{dire}" in gitcatrc file')

                        else:
                            if dire in self.catalogue:
                                error_message(f'{dire} appears in the catalogue more than once!')
                            else:
                                self.catalogue[dire] = rep.strip()

        except (FileNotFoundError, OSError):
            error_message(f'there was a problem reading the catalogue file {self.gitcatrc}')

        # set the maximum length of a catalogue key
        try:
            self.max = max(len(dire) for dire in self.repositories()) + 1
        except ValueError:
            self.max = 0

    def save_catalogue(self):
        r'''
        Save the catalogue of git repositories to sync
        '''
        with open(self.gitcatrc, 'w') as catalogue:
            catalogue.write('# List of git repositories to sync using gitcat\n')
            catalogue.write('# Do not remove the "Catalogue:" line below!\n')
            catalogue.write(settings.save_settings())
            catalogue.write('Catalogue:\n'+self.list_catalogue(listing=True) + '\n')

    def short_path(self, dire):
        r'''
        Return the shortened path to the directory `dire` obtained by removing `self.prefix`
        if necessary.
        '''
        debugging(f'prefix = {self.prefix}.'.format(self.prefix))
        debugging(f'dire = {dire}, prefixed={dire.startswith(self.prefix)}')

        return dire[len(self.prefix) + 1:] if dire.startswith(
            self.prefix) else dire

    def repositories(self):
        ''' return the list of repositories to iterate over by
            filtering by options.repositories
        '''
        # if there is no filter then return the catalogue keys
        if not hasattr(self.options, 'repositories'):
            return self.catalogue.keys()

        repositories = re.compile(self.options.repositories)
        return filter(repositories.search, self.catalogue.keys())

    # ---------------------------------------------------------------------------
    # messages
    # ---------------------------------------------------------------------------

    def message(self, message, ending=None):
        r'''
        If `self.quiet` is `True` then print `message` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `False` then do nothing.
        '''
        if not self.quiet:
            debugging('-' * 40)
            print(message, end=ending)
            debugging('-' * 40)

    def quiet_message(self, message, ending=None):
        r'''
        If `self.quiet` is `False` then print `message` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `True` then do nothing.
        '''
        if self.quiet:
            debugging('-' * 40)
            print(message, end=ending)
            debugging('-' * 40)

    def rep_message(self, rep, message='', quiet=True, ending=None):
        r'''
        If `self.quiet` is `True` then print `message` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `False` then do nothing.
        '''
        debugging(
            'rep message: quiet={}, self.quiet={} and quietness={}\n{}'.format(
                quiet, self.quiet, not (quiet and self.quiet), '-' * 40))
        if not (quiet and self.quiet):
            print('{:<{max}} {}'.format(rep, message, max=self.max),
                  end=ending)
            debugging('-' * 40)

    # ---------------------------------------------------------------------------
    # Now implement the git cat commands that are available from the command line
    # The doc-strings for this methods become part of help text in the manual.
    # In particular, any Example blocks become code blocks.
    # ---------------------------------------------------------------------------

    def add(self):
        r'''
        Add the current repository to the catalogue stored in the gitcatrc
        file. An error is returned if any of the following hold:
        - the current directory is already in the git cat catalogue
        - the current directory is not contained in a git repository
        - the current directory does not have a remote a git repository

        Example:
            > git cat add  # add the current directory to the catalogue
        '''
        dire = self.get_current_git_root()

        rep = Git(dire, 'remote', 'get-url --push origin')
        if not rep:
            error_message(f'Unable to find remote repository for {dire}')

        dire = self.short_path(dire.output.strip())
        rep = rep.output.strip()
        if dire in self.catalogue:
            # give an error if repository is already in the catalogue
            error_message(f'the git repository in {dire} is already in the catalogue')
        else:
            # add current directory to the repository and save
            self.catalogue[dire] = rep
            self.save_catalogue()
            self.message(f'Adding {dire} to the catalogue')

            # check to see if the gitcatrc is in a git repository and, if so,
            # add a commit message
            catdir = os.path.dirname(self.gitcatrc)
            if self.is_git_repository(catdir):
                Git(dire, 'commit', '--all --message="{}"'.format(f'Adding {dire} to gitcatrc'))

    def branch(self):
        r'''
        Run `git branch --verbose` in selected repositories in the
        catalogue. This gives a summary of the status of the branches in the
        repositories managed by git cat.

        Example:
            > git cat branch Code
            Code/Project1
              python3 6c2fcd5 Putting out the washing
            Code/Project2
              master  2d2614e [ahead 1] Making some important changes
            Code/Project3        already up to date
            Code/Project4        already up to date
            Code/Project5
              branch1 14fc541 Adding braid method to tableau
              * branch2       68480a4 git cat: updating   doc/README.rst
              master             862e2f4 Adding good stuff
            Code/Project6            already up to date

        '''
        if self.connected_to_internet('check status of branches'):

            # need to use -q to stop output being printed to stderr, but then we
            # have to work harder to extract information about the pull
            options = self.process_options('--verbose')
            for rep in self.repositories():
                debugging('\nBRANCH ' + rep)
                dire = self.expand_path(rep)
                if self.is_git_repository(dire):
                    pull = Git(rep, 'branch', options)
                    if pull:
                        if '\n' not in pull.output:
                            self.rep_message(rep, 'already up to date')
                        else:
                            self.rep_message(rep,
                                             pull.output[pull.output.index('\n'):])
                else:
                    self.rep_message(rep, 'not on system')

    def list(self):
        r'''
        List the repositories managed by git cat, together with the location of
        their remote repository.

        Example:
            > git cat ls
            Code/Project1  = git@bitbucket.org:AndrewsBucket/prog1.git
            Code/Project2  = git@bitbucket.org:AndrewsBucket/prog2.git
            Code/Project3  = git@bitbucket.org:AndrewsBucket/prog3.git
            Code/Project4  = git@bitbucket.org:AndrewsBucket/prog4.git
            Code/GitCat    = git@gitgithub.com:AndrewMathas/gitcat.git
            Notes/Life     = git@gitgithub.com:AndrewMathas/life.git
            Stuff          = git@some.random.rep.com:Me/stuffing.git

        '''
        print(self.list_catalogue(listing=False))

    def commit(self):
        r'''
        Commit all changes in the selected repositories in the catalogue. The
        commit message will list the files that were changed. This command is
        provided mainly for completeness and, instead, `git cat push` would
        probably be used.

        Example:
            > git cat commit
        '''
        if self.connected_to_internet('commit repositories'):

            for rep in self.repositories():
                debugging('\nCOMMITTING ' + rep)
                dire = self.expand_path(rep)
                if self.is_git_repository(dire):
                    self.commit_repository(rep)

    def diff(self):
        r'''
        Run git diff with various options on the repositories in the
        catalogue.

        Example:

            > git cat diff Code
            Code/Project1  up to date
            Code/Project2  up to date
            Code/GitCat    diff --git c/gitcat.py w/gitcat.py
            index b32a07f..c32a435 100644
            --- c/gitcat.py
            +++ w/gitcat.py
            @@ -29,16 +29,25 @@ Examples:
            -gitcatrc:
            +The gitcatrc file:
        '''
        if self.connected_to_internet('diff repositories'):

            options = self.process_options()
            options += ' HEAD'
            for rep in self.repositories():
                debugging('\nDIFFING ' + rep)
                dire = self.expand_path(rep)
                if self.is_git_repository(dire):
                    diff = Git(rep, 'diff', options)
                    if diff:
                        if diff.output != '':
                            self.rep_message(rep, diff.output.lstrip(), quiet=False)
                        else:
                            self.rep_message(rep, 'up to date')

    def fetch(self):
        r'''
        Run `git fetch -q --progress` on the installed git cat repositories.

        Example:
            > git cat fetch
            Rep1  already up to date
            Rep2  already up to date
            Rep3  remote: Counting objects: 3, done.
              remote: Compressing objects:  33% (1/3)
              remote: Compressing objects:  66% (2/3)
              remote: Compressing objects: 100% (3/3)
              remote: Compressing objects: 100% (3/3), done.
              remote: Total 3 (delta 2), reused 0 (delta 0)

        '''
        if self.connected_to_internet('fetch repositories'):
            # need to use -q to stop output being printed to stderr, but then we
            # have to work harder to extract information about the pull
            options = self.process_options('-q --progress')
            for rep in self.repositories():
                debugging('\nFETCHING ' + rep)
                dire = self.expand_path(rep)
                if self.is_git_repository(dire):
                    pull = Git(rep, 'fetch', options)
                    if pull:
                        if pull.output == '':
                            self.rep_message(rep, 'already up to date')
                        else:
                            self.rep_message(rep, pull.output.lstrip())
                else:
                    self.rep_message(rep, 'not on system')

    def install(self):
        r'''
        Install listed repositories from the catalogue.

        If a directory exists but is not a git repository then initialise the
        repository and fetch from the remote.

        By default all repositories are installed, however, by specifying a
        regular expression for the repositories you can install a subset of the
        repositories managed by git cat.abs

        Examples:

            > git cat install       # install all repositories managed by git cat
            > git cat install Code  # install all "Code" repositories managed by git cat
        '''
        if self.connected_to_internet('install new repositories'):

            installed_something = False
            for rep in self.repositories():
                debugging('\nINSTALLING ' + rep)
                dire = self.expand_path(rep)
                if os.path.exists(dire):
                    if os.path.exists(os.path.join(dire, '.git')):
                        self.rep_message(f'git repository {dire} already exists')
                    else:
                        # initialise current repository and fetch from remote
                        Git(rep, 'init')
                        Git(rep, f'remote add origin {self.catalogue[rep]}')
                        Git(rep, 'fetch origin')
                        Git(rep, 'checkout -b master --track origin/master')
                        installed_something = True

                else:
                    self.rep_message(rep, 'installing')
                    parent = os.path.dirname(dire)
                    os.makedirs(parent, exist_ok=True)
                    os.chdir(parent)
                    if not self.dry_run:
                        install = Git(rep, 'clone', f'--quiet {self.catalogue[rep]} {os.path.basename(dire)}')
                        if install:
                            installed_something = True
                            self.message(' - done!')
                if not (self.dry_run or self.is_git_repository(dire)):
                    self.rep_message(rep, f'{rep} is not a git repository!?', quiet=False)

            if not installed_something:
                error_message('No matching repositories found to install')

    def pull(self):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer. Unless the  `--quiet` option is used,
        a message is printed to give the summarise the status of the
        repository.

        Example:
            > git cat pull
            Code/Project1  already up to date
            Code/Project2  already up to date
            Code/GitCat    already up to date
              remote: Counting objects: 8, done.
              remote: Total 8 (delta 6), reused 0 (delta 0)
            Notes/Life     already up to date

        '''
        if self.connected_to_internet('pull repositories'):

            # need to use -q to stop output being printed to stderr, but then we
            # have to work harder to extract information about the pull
            options = self.process_options('-q --progress')
            for rep in self.repositories():
                debugging('\nPULLING ' + rep)
                dire = self.expand_path(rep)
                if self.is_git_repository(dire):
                    pull = Git(rep, 'pull', options)
                    if pull:
                        if pull.output == '':
                            self.rep_message(rep, 'already up to date')
                        else:
                            self.rep_message(
                                rep,
                                'pulling\n' + '\n'.join(
                                    lin for lin in pull.output.split('\n')
                                    if 'Compressing' not in lin),
                                quiet=False)
                else:
                    self.rep_message(rep, 'repository not installed')

    def push(self):
        r'''
        Run through all installed repositories and push them to their remote
        repositories. Any uncommitted repository with local changes will be
        committed and the commit message listing the files that have changed.
        Unless the `-quiet` option is used, a summary of the status of
        each repository is printed with each push.

        Example:
            > git cat push
            Code/Project1  pushed
              To bitbucket.org:AndrewsBucket/dotfiles.git
              refs/heads/master:refs/heads/master	e128dd9..904f96a
              Done
            Code/Project2  up to date
            Code/Project3  up to date
            Code/Project4  up to date
            Code/GitCat    commit
              [master 442822d] git cat: updating   gitcat.py
              1 file changed, 44 insertions(+), 5 deletions(-)
              To bitbucket.org:AndrewsBucket/gitcat.git
              refs/heads/master:refs/heads/master	6ffeb9d..442822d
              Done
            Notes/Life     up to date

        '''
        if self.connected_to_internet('push repositories'):
            debugging('\nPUSHING ')
            options = self.process_options('--porcelain --follow-tags')
            for rep in self.repositories():
                debugging('\nPUSHING ' + rep)
                dire = self.expand_path(rep)
                if self.is_git_repository(dire):
                    debugging('Continuing with push')
                    commit = self.commit_repository(rep)
                    if commit:
                        if commit.output != '':
                            self.rep_message(rep, 'commit\n' + commit.output)
                        ahead = Git(rep, 'for-each-ref', r'--format="%(refname:short) %(upstream:track)" refs/heads')
                        if ahead:
                            if 'ahead' not in ahead.output:
                                self.rep_message(rep, 'up to date')
                            elif not self.dry_run:
                                push = Git(rep, 'push', options)

                                if push:
                                    if push.output.startswith('  To ') and push.output.endswith('Done'):
                                        if commit.output == '' and 'up to date' not in commit.output:
                                            self.rep_message(rep, 'pushed\n' + push.output)
                                        else:
                                            self.message(
                                                push.output.split('\n')[0])
                                    else:
                                        if commit.output == '' and 'up to date' not in commit.output:
                                            self.rep_message(rep, 'pushed\n' + push.output)
                                        else:
                                            self.message(push.output)

                else:
                    self.rep_message(rep, 'not on system')

    def remote_set_ssh(self):
        r'''
        Make the URLs of all repositories use SSH access (rather than HHTPS).
        This is useful because it allows password-less once the user's public
        key has been uploaded to the remote repository.

        This involves changing the remote URL from something like:

            https://AndrewsBucket@bitbucket.org/AndrewsBucket/webquiz.git

        to:

            git@bitbucket.org:AndrewsBucket/webquiz.git

        Example:
            > git cat remote-set-ssh
            Code/Project1  unchanged
            Code/Project2  changed to ssh access
            Code/Project3  unchanged
        '''
        if self.connected_to_internet('change ssh settings'):

            for rep in self.repositories():
                debugging('\nCONVERT-TO-SSH ' + rep)
                dire = self.expand_path(rep)
                if self.is_git_repository(dire):
                    remote = Git(rep, 'remote', '-v')
                    changed = [] # avoid duplicates by keeping a list of remotes that have already been changed
                    if remote:
                        if 'https://' in remote.output:
                            # remotes will be repeating triples that look something like:
                            # 'origin', 'https://AndrewsBucket@bitbucket.org/AndrewsBucket/webquiz.git', '(fetch)'
                            remotes = remote.output.split()
                            r=0
                            while r+1<len(remotes):
                                https = remotes[r+1] # a https string as above
                                if remotes[r] not in changed and '@' in https:
                                    ssh = 'git'+https[https.index('@'):].replace('/',':',1)
                                    changing = Git(rep, 'remote', f'set-url {remotes[r]} {ssh}')
                                    if changing:
                                        self.rep_message(rep, 'changed to ssh access')
                                        changed.append(remotes[r])
                                r += 3
                        else:
                            self.rep_message(rep, 'unchanged')
                else:
                    self.rep_message(rep, 'not on system')

    def remove(self):
        r'''
        Remove the current repository to the catalogue stored in the gitcatrc
        file. An error is returned if any of the following hold:
        - the current directory is not in the git cat catalogue
        - the current directory is not contained in a git repository

        Example:
            git cat remove  # remove the current directory to the catalogue

        '''
        dire = self.get_current_git_root()
        rep = Git(dire, 'remote', 'get-url --push origin')

        if not rep:
            error_message(f'Unable to find remote repository for {dire}')

        dire = self.short_path(dire.output.strip())
        if dire not in self.catalogue:
            error_message(f'unknown repository {dire}')

        del self.catalogue[dire]
        self.message(f'Removing {dire} from the catalogue')
        self.save_catalogue()

        if self.options.git_everything:
            # remove directory
            self.message(f'Removing directory {dire}')
            shutil.rmtree(dire)

            # check to see if the gitcatrc is in a git repository and, if so,
            # add a commit message
            catdir = os.path.dirname(self.gitcatrc)
            if self.is_git_repository(catdir):
                Git(dire, 'commit', '--all --message "{}"'.format(f'Removing {dire} from gitcatrc'))

    def status(self):
        r'''
        Print a summary of the status of all of the repositories in the
        catalogue. The name is slightly misleading as this command does not
        just run `git status` on each repository and, instead, it queries the
        remote repositories to determine whether each repository is ahead or
        behind the remote repository.

        Example:
            > git cat status Code
            Code/Project1  up to date
            Code/Project2  ahead 1
            Code/Project3  up to date
            Code/Project4  behind 1
            Code/GitCat    uncommitted changes in 3 files
              M README.rst
              M git-options.ini
              M gitcat.py
        '''
        if self.connected_to_internet('check status'):

            status_options = self.process_options('--porcelain --short --branch')
            diff_options = '--shortstat --no-color'

            for rep in self.repositories():
                debugging(f'\nSTATUS for {rep}')
                dire = self.expand_path(rep)
                if self.is_git_repository(dire):

                    # update with remote, unless local is true
                    remote = self.options.git_local or Git(rep, 'remote', 'update')

                    if remote:
                        # use status to work out relative changes
                        status = Git(rep, 'status', status_options)
                        if status:
                            changes = ahead_behind.search(status.output)
                            changes = '' if changes is None else changes.group()[1:-1]

                            if '\n' in status.output:
                                status.output = status.output[status.output.
                                                              index('\n') + 1:]
                            elif status.output.startswith('  ##'):
                                status.output = ''

                            # use diff to work out which files have changed
                            diff = Git(rep, 'diff', diff_options)
                            changed = ''
                            if diff:
                                changed = files_changed.search(diff.output)
                                changed = '' if changed is None else 'uncommitted changes in ' + changed.groups()[0]

                            debugging(f'changes = {changes}\nchanged={changed}\nstatus={status.output}')

                            if changes != '':
                                changed += changes if changed == '' else ', ' + changes

                            if status.output != '':
                                self.rep_message(
                                    rep,
                                    changed + '\n' + status.output,
                                    quiet=False)
                            elif changed != '':
                                self.rep_message(rep, changed, quiet=False)
                            else:
                                self.rep_message(rep, 'up to date')

                else:
                    self.rep_message(rep, 'not on system')


# ---------------------------------------------------------------------------
class GitCatHelpFormatter(argparse.HelpFormatter):
    '''
    Override help formatter so that we can print a list of the possible
    commands together with a quick summary of them
    '''
    def _check_value(self, action, value):
        """
        It's probably not a great idea to override a "hidden" method
        but the default behavior is pretty ugly and there doesn't
        seem to be any other way to change it.
        """
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            msg = ['Invalid choice, valid choices are:\n']
            for i in range(len(action.choices))[::self.ChoicesPerLine]:
                current = []
                for choice in action.choices[i:i+self.ChoicesPerLine]:
                    current.append('%-40s' % choice)
                msg.append(' | '.join(current))
            possible = get_close_matches(value, action.choices, cutoff=0.8)
            if possible:
                extra = ['\n\nInvalid choice: %r, maybe you meant:\n' % value]
                for word in possible:
                    extra.append('  * %s' % word)
                msg.extend(extra)
            raise argparse.ArgumentError(action, '\n'.join(msg))

    def _format_action_invocation(self, act):
        """
        Initial substrings of the subparser commands are accepted as aliases
        for the command.  By default, in the help, the list of aliases are shown
        with each subparser command, leading to help output like:

            Commands:
              add               Add current repository to the catalogue
              branch (bra, bran, branc)  Print status of all branches in each repository
              commit (com, comm, commi)  Commit changes in all repositories
              diff (dif)        Print a diff of the changes in each repository
              fetch (fet, fetc)  Fetch all repositories from remote repositories
              install (ins, inst, insta, instal)  Install repository from the catalogue
              ls                List all repositories in the catalogue

        Override `self._format_action_invocation` in order to remove the list
        of aliases from each subparser command.
        """
        inv = super()._format_action_invocation(act)
        if ' (' in inv:
            return inv[:inv.index(' (')]
        return inv

    def _format_action(self, action):
        if isinstance(action, argparse._SubParsersAction):
            # inject new class variable for subcommand formatting
            subactions = action._get_subactions()
            invocations = [
                self._format_action_invocation(a) for a in subactions
            ]
            self._subcommand_max_length = max(len(i) for i in invocations)

        if isinstance(action, argparse._SubParsersAction._ChoicesPseudoAction):
            # format subcommand help line
            subcommand = self._format_action_invocation(action)  # type: str
            width = self._subcommand_max_length+2
            help_text = ""
            if action.help:
                help_text = self._expand_help(action)
            return f'  {subcommand:{width}}  {help_text}\n'

        elif isinstance(action, argparse._SubParsersAction):
            # process subcommand help section
            message = ''
            for subaction in action._get_subactions():
                message += self._format_action(subaction)
            return message

        return super()._format_action(action)

    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        elif action.choices is not None:
            result = '<command> [options]'
        else:
            result = default_metavar

        def new_format(tuple_size):
            if isinstance(result, tuple):
                return result

            return (result, ) * tuple_size

        return new_format


# ---------------------------------------------------------------------------
def setup_command_line_parser(settings):
    '''
    Return parsers for the command line options and the commands.
    The function is used to parse the command-line options and to
    automatically generate the documentation from setup.py
    '''
    # set parse the command line options using argparse
    parser = argparse.ArgumentParser(
        add_help=False,
        description='Simultaneously synchronise multiple local and remote git repositories',
        formatter_class=GitCatHelpFormatter,
        prog='git cat',
    )

    # ---------------------------------------------------------------------------
    # catalogue options
    # ---------------------------------------------------------------------------
    parser.add_argument(
        '-c',
        '--catalogue',
        type=str,
        default=settings.rc_file,
        help=f'specify the catalogue of git repositories (default: {settings.rc_file})')
    parser.add_argument(
        '-p',
        '--prefix',
        type=str,
        default=settings.prefix,
        help='Prefix directory name containing all repositories')
    parser.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        default=settings.quiet,
        help='Print messages only if repository changes')
    # parser.add_argument(
    #     '-s',
    #     '--set-as-default',
    #     action='store_true',
    #     default=False,
    #     help='use the current options for <command> as the default')

    # override default help mechanism
    parser.add_argument('-h', '--help',
        action='count',
        help='help: for extended help use -hh and -hhh',
        default=0)

    # options suppressed from help
    parser.add_argument(
        '--debugging',
        action='store_true',
        default=False,
        help=argparse.SUPPRESS)

    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=settings.version(),
        help=argparse.SUPPRESS
    )

    # ---------------------------------------------------------------------------
    # add catalogue commands using settings and the git-options.ini file
    # ---------------------------------------------------------------------------
    commands = parser.add_subparsers(
        title='Commands',
        help='Subcommand to run',
        dest='command')
    settings.add_git_options(commands)
    parser._optionals.title = 'Optional arguments'
    return parser, commands

def main():
    r'''
    Parse command line options and then run git cat
    '''
    parser, commands = setup_command_line_parser(settings)
    if argcomplete:
        argcomplete.autocomplete(parser)
    options = parser.parse_args()
    settings.DEBUGGING = options.debugging

    if options.help > 0:
        parser.print_help()

        if options.help > 1:
            doc = __doc__.split('******')
            print(doc[1])


        if options.help > 2:
            for cmd in commands.choices:
                print('{}\n{}'.format(cmd, '-'*len(cmd)))
                commands.choices[cmd].print_help()
                print()

        sys.exit()

    elif options.command is None and options.moveto is None:
        parser.print_help()
        sys.exit(1)

    GitCat(options, settings)

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    main()
