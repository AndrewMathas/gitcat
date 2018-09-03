#!/usr/bin/env python

r'''
git-cat
=======

Herding a catalogue of git repositories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Simultaneously push and pull a catalogue of remote git repositories

    usage: git cat [-h] [-c CATALOGUE] [-p PREFIX] [-q] <command> [options] ...

A command line tool for synchronising a catalogue of git repositories, which is
stored in the gitcatrc file.

Commands:

  add     -  Add repository to the catalogue
  commit  -  Commit all uncommitted repositories in the catalogue
  diff    -  Print a diff of the changes in each repository
  install -  Install all repositories in the catalogue
  ls      -  List all of the repositories in the catalogue
  pull    -  Pull all repositories in the catalogue
  push    -  Push all repositories in the catalogue
  remove  -  Remove repository from the catalogue
  status  -  Print the status of each repository in the catalogue

Optional arguments:
  -h, --help            show this help message and exit
  -c CATALOGUE, --catalogue CATALOGUE
                        specify the catalogue of bitbucket repositories
  -p PREFIX, --prefix PREFIX
                        Prefix directory name containing all repositories
  -q, --quiet           print messages

Author
------
Andrew Mathas
(c) Copyright 2018

Licence
-------
GNU General Public License, Version 3, 29 June 2007

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License (GPL_) as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

'''

# ---------------------------------------------------------------------------------------
# TODO:
#   - README file/documentation
#   - debugging and testing...
#   - make "git cat git" command work
#   - make "git cat pull" first update the repository containing the gitcatrc file and
#     then reread it
#   - add a "git cat --set-as-defaults cmd [options]" option to set defaults
#     for a given command and then store the information into the gitcatrc
#     file. Will need to be clever to avoid code duplication...possibly add all
#     of the command-line options to the settings class and then use it to
#     automatically generate the command line options
#   - fix pull strategy options
#   - add options for sorting catalogue
#   - move read_catalogue and save_catalogue into Settings
#   - make status check that changes have been pushed

import argparse
import itertools
import os
import re
import shutil
import subprocess
import sys


# ---------------------------------------------------------------------------------------
# error messages and debugging

def error_message(err):
    r'''
    Print error message and exit.
    '''
    print('git cat error: {}'.format(err))
    sys.exit(1)


def debugging(message):
    """ print a debugging message if `debugging` is true"""
    if settings.DEBUGGING:
        print(message)

# ---------------------------------------------------------------------------------------
# compiled regular expressions

# section in an ini file
ini_section = re.compile(r'^\[([a-zA-Z]*)\]$')

# [ahead 1], or [behind 1] or [ahead # 2, behind 1] in status
ahead_behind = re.compile(r'\[((ahead|behind) [0-9]+(, )?)+\]')

# list of files that have changed
files_changed = re.compile(r'([0-9]+ file(?:s|))(?: changed)')

# ---------------------------------------------------------------------------------------
# settings
class Settings(dict):
    r"""
    A class for reading and saving the fgitcar settings and supported git
    command line options. 
    """
    DEBUGGING = False

    def __init__(self, ini_file, git_options_file):
        super().__init__()

        self.git_defaults = {} # will hold non-standard git defaults
        self.prefix = os.environ['HOME']

        # location of the gitcatrc file defaults to ~/.dotfiles/config/gitcatrc
        # and then to ~/.gitcatrc
        if os.path.isdir(os.path.expanduser('~/.dotfiles/config')):
            self.rc_file = os.path.expanduser('~/.dotfiles/config/gitcatrc')
        if not os.path.isfile(self.rc_file):
            self.rc_file = os.path.expanduser('~/.gitcatrc')

        self.read_init_file(ini_file)
        self.read_git_options(git_options_file)

    def add_git_options(self, subparser):
        '''
        Generate all of the git-cat command options as parsers of `subparser`
        '''
        for cmd in self.commands:
            command = subparser.add_parser(cmd, help=self.commands[cmd]['help'])
            for option in self.commands[cmd]:
                if option != 'help':
                    if 'short-option' in self.commands[cmd][option]:
                        options = self.commands[cmd][option].copy()
                        short_option = options['short-option']
                        del options['short-option']
                        debugging('short option = {}.'.format(short_option))
                        if short_option is None:
                            command.add_argument('--'+option, **options)
                        else:
                            command.add_argument('-'+short_option, '--'+option, **options)
                    else:
                        command.add_argument('-'+option[:1], '--'+option, **self.commands[cmd][option])

            # finally, add the optional repository filter option
            command.add_argument(
                dest='repositories',
                type=str,
                default='',
                nargs='?',
                help='optionally filter repositories for status'
            )

    def read_init_file(self, ini_file):
        '''
        Read and store the information in the ini file
        '''
        with open(ini_file, 'r') as ini:
            for line in ini:
                key, val = [w.strip() for w in line.split('=')]
                if key != '':
                    if '.' in key: 
                        command, option = ket.split('.')
                        if not command in self.git_defaults:
                            self.git_defaults[command] = {}
                        self.git_defaults[command][option] = val
                    else:
                        setattr(self, '_'+key.lower(), val)

    def read_git_options(self, options_file):
        '''
        Read and store the information in the command-line options file
        '''
        self.commands = {}
        with open(options_file, 'r') as options:
            for line in options:
                match =  ini_section.search(line.strip())
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
                        except (NameError, SyntaxError, TypeError) as err:
                            option['default'] = default.strip()
                        if isinstance(option['default'], bool):
                            option['action'] = 'store_{}'.format(str(not option['default']).lower())
                        if isinstance(option['default'], str):
                            option['type'] = str

                        # dest could be overwritten later in the ini file
                        option['dest'] = 'git_'+opt.replace('-', '_')
                        self.commands[command][opt] = option
                    elif len(choices) == 2:
                        # help for command or extra specifications for the current option
                        if choices[0] == 'help':
                            self.commands[command]['help'] = choices[1]
                        else:
                            try:
                                self.commands[command][opt][choices[0]] = eval(choices[1])
                            except (NameError, SyntaxError, TypeError) as err:
                                self.commands[command][opt][choices[0]] = choices[1]
                    else:
                        error_message('syntax error in {} on the line\n {}'.format(options_file, line))

    def save_settings(self):
        r'''
        Return a string for setting the non-standard settings in the gitcatrc file
        '''
        settings = ''
        if self.prefix != os.environ['HOME']:
            settings += 'prefix = {}\n'.format(self.prefix)
        return settings

    def version(self):
        """ return gitcat version """
        return 'git cat version {}'.format(self._version)
file = lambda f: os.path.join(os.path.dirname(__file__),  f)
settings = Settings(file('gitcat.ini'), file('git-options.ini'))

# ---------------------------------------------------------------------------------------
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
        git = subprocess.run(
            'git {} {}'.format(command, options).strip(),
            shell=True,
            capture_output=True
        )

        # store the output
        self.rep = rep
        self.returncode = git.returncode
        self.command = command + ' ' + options

        if self.returncode != 0:
            debugging('-'*40)
            print('{}: there was an error using git {}\n  {}\n'.format(
                rep,
                command,
                git.stderr.decode().strip().replace('\n', '\n  ').replace('\r', '\n  '),
            ))
            debugging('-'*40)
            self.git_command_ok = False
        else:
            self.git_command_ok = True

        # output is indented two spaces and has no blank lines
        self.output = git.stdout.decode()
        self.output = '\n'.join('  '+lin.strip()
             for lin in (git.stdout.decode().replace('\r', 'n').strip().split('\n')
                        +git.stderr.decode().replace('\r', 'n').strip().split('\n'))
                            if lin != ''
        )
        debugging('{}\nstdout={}\nstderr={}'.format(self, git.stdout, git.stderr))

    def __bool__(self):
        ''' return 'self.is_ok` '''
        return self.git_command_ok

    def __repr__(self):
        """ define a __repr__ method for debugging """
        return 'Git({})\n    rep={}, OK={}, returncode={}\n    output: {}.'.format(
            self.command,
            self.rep,
            self.git_command_ok,
            self.returncode,
            self.output.replace('\n', '\n  '),
        )

# ---------------------------------------------------------------------------------------
class GitCat:
    r"""
    Usage: GitCat(options)

    A class for reading, accessing and storing details of the different git
    repositories. These are stored in `filename` in the form:

       directory1 = repository1
       directory2 = repository2
       ...

    Any lines without a key-value pair are ignored.
    """

    def __init__(self, options):
        self.gitcatrc = options.catalogue
        self.options = options
        self.prefix = options.prefix

        self.dry_run = False
        self.quiet = False

        if hasattr(options, 'git_quiet'):
            self.quiet = options.git_quiet

        if hasattr(options, 'git_dry_run'):
            self.dry_run = options.git_dry_run

        # read the catalogue from the rc file
        self.read_catalogue()

        # run corresponding command
        getattr(self, options.command)()

    def changed_files(self, rep):
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
        debugging('\nCOMMIT rep='+rep)
        changed_files = self.changed_files(rep)
        if changed_files and changed_files.output != '':
            commit_message = 'git cat: updating '+changed_files.output
            commit = '--all --message="{}"'.format(commit_message)
            if self.dry_run:
                commit += ' --porcelain'
            return Git(rep, 'commit', commit)


        return changed_files

    def expand_path(self, dire):
        r'''
        Return the path to the directory `dire`, adding `self.prefix` if
        necessary.
        '''
        return dire if dire.startswith('/') else os.path.join(self.prefix, dire)

    def is_git_repository(self, dire):
        r'''
        Return `True` if `dire` is a git repository and `False` otherwise. As
        part of testing for a repository the current working directory is also
        changed to `dire`.
        '''
        debugging('\nCHECKING for git dire={}'.format(dire))
        if os.path.isdir(dire):
            os.chdir(dire)
            rep = dire.replace(self.prefix+'/', '')
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
            sep='=' if listing or self.is_git_repository(self.expand_path(dire)) else '!',
            max=self.max
            ) for dire in self.repositories()
        )

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
                    options += ' --'+opt
                elif isinstance(val, list):
                    options += ' --{}={}'.format(opt, ','.join(val))
                elif isinstance(val, str):
                    options += ' --{}={}'.format(opt, val)
                else:
                    debugging('option {}={} ignored'.format(option, val))
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
            with open(self.gitcatrc, 'r') as catalogue:
                for line in catalogue:
                    if ' = ' in line:
                        dire, rep = line.split(' = ')
                        dire = dire.strip()
                        if dire in self.catalogue:
                            error_message('{} appears in the catalogue more than once!'.format(dire))
                        elif dire.lower == 'prefix':
                            self.prefix = rep.strip()
                        else:
                            self.catalogue[dire] = rep.strip()
        except (FileNotFoundError, IOError):
            error_message('there was a problem reading the catalogue file {}'.format(self.gitcatrc))

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
            catalogue.write('# List of git repositories to sync using gitcat\n\n')
            catalogue.write(settings.save_settings())
            catalogue.write(self.list_catalogue(listing=True)+'\n')

    def short_path(self, dire):
        r'''
        Return the shortened path to the directory `dire` obtained by removing `self.prefix`
        if necessary.
        '''
        debugging('prefix = {}.'.format(self.prefix))
        debugging('dire = {}, prefixed={}'.format(dire, dire.startswith(self.prefix)))
        return dire[len(self.prefix)+1:] if dire.startswith(self.prefix) else dire

    def repositories(self):
        ''' return the list of repositories to iterate over by
            filtering by options.repositories
        '''
        # if there is no filter then return the catalogue keys
        if not hasattr(self.options, 'repositories'):
            return self.catalogue.keys()

        repositories = re.compile(self.options.repositories)
        return filter(repositories.search, self.catalogue.keys())

    # ---------------------------------------------------------------------------------------
    # messages
    # ---------------------------------------------------------------------------------------

    def message(self, message, ending=None):
        r'''
        If `self.quiet` is `True` then print `message` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `False` then do nothing.
        '''
        if not self.quiet:
            debugging('-'*40)
            print(message, end=ending)
            debugging('-'*40)

    def quiet_message(self, message, ending=None):
        r'''
        If `self.quiet` is `False` then print `message` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `True` then do nothing.
        '''
        if self.quiet:
            debugging('-'*40)
            print(message, end=ending)
            debugging('-'*40)

    def rep_message(self, rep, message='', quiet=True, ending=None):
        r'''
        If `self.quiet` is `True` then print `message` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `False` then do nothing.
        '''
        debugging('rep message: quiet={}, self.quiet={} and quietness={}\n{}'.format(
                  quiet, self.quiet, not(quiet and self.quiet), '-'*40
                 )
        )
        if not(quiet and self.quiet):
            print('{:<{max}} {}'.format(rep, message, max=self.max, end=ending))
            debugging('-'*40)

    # ---------------------------------------------------------------------------------------
    # Now implement the git cat commands available from the command line
    # ---------------------------------------------------------------------------------------

    def add(self):
        r'''
        Add the current repository to the catalogue
        '''
        if self.options.repository.startswith('/'):
            dire = self.options.repository
        else:
            dire = os.path.join(self.prefix, self.options.repository)

        if not (os.path.isdir(dire) and self.is_git_repository(dire)):
            error_message('{} not a git repository'.format(dire))

        # find the root directory for the repository and the remote URL`
        os.chdir(dire)
        root = Git(dire, 'root')
        if not root:
            error_message('{} is not a git repository:\n  {}'.format(
                dire, root.output)
            )

        rep = Git(dire, 'remote', 'get-url --push origin')
        if not rep:
            error_message('Unable to find remote repository for {} :\n  {}'.format(
                dire, rep.output)
            )

        dire = self.short_path(root.output.strip())
        rep = rep.output.strip()
        if dire in self.catalogue:
            # give an error if repository is already in the catalogue
            error_message('the git repository in {} is already in the catalogue'.format(dire))
        else:
            # add current directory to the repository and save
            self.catalogue[dire] = rep
            self.save_catalogue()
            self.message('Adding {} to the catalogue'.format(dire))

            # check to see if the gitcatrc is in a git repository and, if so,
            # add a commit message
            catdir = os.path.dirname(self.gitcatrc)
            if self.is_git_repository(catdir):
                Git(dire, 'commit', '--all --message="{}"'.format('Adding {} to gitcatrc'.format(dire)))

    def branch(self):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer
        '''
        # need to use -q to stop output being printed to stderr, but then we
        # have to work harder to extract information about the pull
        options = self.process_options('--verbose')
        for rep in self.repositories():
            debugging('\nBRANCH '+rep)
            dire = self.expand_path(rep)
            if self.is_git_repository(dire):
                pull = Git(rep, 'branch', options)
                if pull:
                    if '\n' not in pull.output:
                        self.rep_message(rep, 'already up to date')
                    else:
                        self.rep_message(rep, pull.output[pull.output.index('\n'):])
            else:
                self.rep_message(rep, 'not on system')

    def ls(self):
        r'''
        List the repositories managed by git cat
        '''
        print(self.list_catalogue(listing=False))

    def commit(self):
        r'''
        Commit all of the repositories in the catalogue where files have
        changed. The work is actually done by `self.commit_repository`, which
        commits only one repository, since other methods need to call this as
        well.
        '''
        for rep in self.repositories():
            debugging('\nCOMMITTING '+rep)
            dire = self.expand_path(rep)
            if self.is_git_repository(dire):
                self.commit_repository(rep)

    def diff(self):
        r'''
        Run git diff with various options on the repositories in the
        catalogue.
        '''
        options = self.process_options()
        options += ' HEAD'
        for rep in self.repositories():
            debugging('\nDIFFING '+rep)
            dire = self.expand_path(rep)
            if self.is_git_repository(dire):
                diff = Git(rep, 'diff' 'options')
                if diff:
                    if diff.output != '':
                        self.rep_message(rep, diff.output, quiet=False)
                    else:
                        self.rep_message(rep, 'up to date')

    def fetch(self):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer
        '''
        # need to use -q to stop output being printed to stderr, but then we
        # have to work harder to extract information about the pull
        options = self.process_options('-q --progress')
        for rep in self.repositories():
            debugging('\nFETCHING '+rep)
            dire = self.expand_path(rep)
            if self.is_git_repository(dire):
                pull = Git(rep, 'fetch', options)
                if pull:
                    if pull.output == '':
                        self.rep_message(rep, 'already up to date')
                    else:
                        self.rep_message(rep, pull.output)
            else:
                self.rep_message(rep, 'not on system')

    def git(self, commands):
        r''' Run git commands on every repository in the catalogue '''
        git_command = '{}'.format(' '.join(cmd for cmd in commands))
        for rep in self.repositories():
            debugging('\nGITTING '+rep)
            dire = self.expand_path(rep)
            if self.is_git_repository(dire):
                print('Repository = {}, command = {}'.format(rep, git_command))
                Git(git_command)

    def install(self):
        r'''
        Install some or all of the repositories in the catalogue
        '''
        for rep in self.repositories():
            debugging('\nINSTALLING '+rep)
            dire = self.expand_path(rep)
            if not os.path.exists(dire):
                self.rep_message(rep, 'installing')
                parent = os.path.dirname(dire)
                os.makedirs(parent, exist_ok=True)
                os.chdir(parent)
                if not self.dry_run:
                    install = Git(rep, 'clone', '--quiet {rep} {dire}'.format(
                        dire=os.path.basename(dire),
                        rep=self.catalogue[rep])
                    )
                    if install:
                        self.message(' - done!')
            if not (self.dry_run or self.is_git_repository(dire)):
                print('{} is not a git repository!?'.format(rep))

    def pull(self):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer
        '''
        # need to use -q to stop output being printed to stderr, but then we
        # have to work harder to extract information about the pull
        options = self.process_options('-q --progress')
        for rep in self.repositories():
            debugging('\nPULLING '+rep)
            dire = self.expand_path(rep)
            if self.is_git_repository(dire):
                pull = Git(rep, 'pull', options)
                if pull:
                    if pull.output == '':
                        self.rep_message(rep, 'already up to date')
                    else:
                        self.rep_message(rep, 'pulling\n'+pull.output)
            else:
                self.rep_message(rep, 'repository not installed')

    def push(self):
        r'''
        Run through all repositories and push them to bitbucket if their directories
        exist on this computer. Commit the repository if it has changes
        '''
        options = self.process_options('--porcelain --follow-tags')
        for rep in self.repositories():
            debugging('\nPUSHING '+rep)
            dire = self.expand_path(rep)
            if self.is_git_repository(dire):
                debugging('Continuing with push')
                commit = self.commit_repository(rep)
                if commit:
                    if commit.output != '':
                        self.rep_message(rep, 'commit\n'+commit.output)
                    push = Git(rep, 'push', options+' --dry-run')
                    if push:
                        if '[up to date]' in push.output:
                            self.rep_message(rep, 'up to date')
                        elif not self.dry_run:
                            push = Git(rep, 'push', options)

                            if push:
                                if push.output.startswith('  To ') and push.output.endswith('Done'):
                                    if commit.output == '' and 'up to date' not in commit.output:
                                        self.rep_message(rep, 'pushed\n'+push.output)
                                    else:
                                        self.message('  {}'+push.output.split('\n')[0])
                                else:
                                    if commit.output == '' and 'up to date' not in commit.output:
                                        self.rep_message(rep, 'pushed\n'+push.output)
                                    else:
                                        self.message(push.output)

            else:
                self.rep_message(rep, 'not on system')

    def remove(self):
        r'''
        Remove the directory `dire` from the catalogue of repositories to sync
        '''
        if self.options.repository is not None:
            rep = self.short_path(os.path.expanduser(self.options.repository))
        else:
            rep = self.short_path(os.getcwd())
        dire = self.expand_path(rep)
        if not (rep in self.catalogue and self.is_git_repository(dire)):
            error_message('unknown repository {}'.format(dire))

        del self.catalogue[rep]
        self.message('Removing {} from the catalogue'.format(dire))
        self.save_catalogue()

        if self.options.delete:
            # remove directory
            self.message('Removing directory {}'.format(dire))
            shutil.rmtree(dire)

            # check to see if the gitcatrc is in a git repository and, if so,
            # add a commit message
            catdir = os.path.dirname(self.gitcatrc)
            if self.is_git_repository(catdir):
                Git(dire, 'commit', '--all --message "{}"'.format('Removing {} from gitcatrc'.format(dire)))

    def status(self):
        r'''
        Print the status of all of the repositories in the catalogue
        '''
        status_options = self.process_options('--porcelain --short --branch')
        diff_options = '--shortstat --no-color'

        for rep in self.repositories():
            debugging('\nSTATUS for {}'.format(rep))
            dire = self.expand_path(rep)
            if self.is_git_repository(dire):

                # update with remote, unless local is true
                remote = self.options.git_local or Git(rep, 'remote', 'update')

                if remote:
                    # use status to work out relative changes
                    status = Git(rep, 'status', status_options)
                    if status:
                        if '\n' in status.output:
                            status.output = status.output[status.output.index('\n')+1:]
                        elif status.output.startswith('  ##'):
                            status.output = ''

                        changes = ahead_behind.search(status.output)
                        changes = '' if changes is None else changes.group()[1:-1]

                        # use diff to work out which files have changed
                        diff = Git(rep, 'diff', diff_options)
                        changed = ''
                        if diff:
                            changed = files_changed.search(diff.output)
                            changed = '' if changed is None else 'uncommitted changes in ' + changed.groups()[0]

                        debugging('changes = {}\nchanged={}\nstatus={}'.format(changes, changed, status.output))

                        if changes != '':
                            changed += changes if changed == '' else ', '+changes

                        if status.output != '':
                            self.rep_message(rep, changed+'\n'+status.output, quiet=False)
                        elif changed != '':
                            self.rep_message(rep, changed, quiet=False)
                        else:
                            self.rep_message(rep, 'up to date')

            else:
                self.rep_message(rep, 'not on system')

# ---------------------------------------------------------------------------------------

class CustomHelpFormatter(argparse.HelpFormatter):

    def _format_action(self, action):
        if type(action) == argparse._SubParsersAction:
            # inject new class variable for subcommand formatting
            subactions = action._get_subactions()
            invocations = [self._format_action_invocation(a) for a in subactions]
            self._subcommand_max_length = max(len(i) for i in invocations)

        if type(action) == argparse._SubParsersAction._ChoicesPseudoAction:
            # format subcommand help line
            subcommand = self._format_action_invocation(action) # type: str
            width = self._subcommand_max_length
            help_text = ""
            if action.help:
                help_text = self._expand_help(action)
            return "  {:{width}} -  {}\n".format(subcommand, help_text, width=width)

        elif type(action) == argparse._SubParsersAction:
            # process subcommand help section
            message = '\n'
            for subaction in action._get_subactions():
                message += self._format_action(subaction)
            return message
        else:
            return super(CustomHelpFormatter, self)._format_action(action)

    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        elif action.choices is not None:
            result = '<command> [options]'
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result

            return (result, ) * tuple_size
        return format

class CollectArguments(argparse.Action):
    r'''
    Collect all unknown arguments. Anwer by Jiří J on
        https://stackoverflow.com/questions/33432648/
    '''
    def __init__(self, option_strings, dest, nargs=None, *args, **kwargs):
        nargs = argparse.REMAINDER
        super().__init__(option_strings, dest, nargs, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        def all_opt_strings(parser):
            nested = (x.option_strings for x in parser._actions
                      if x.option_strings)
            return itertools.chain.from_iterable(nested)

        all_opts = list(all_opt_strings(parser))

        collected = []
        while len(values) > 0:
            if values[0] in all_opts:
                break
            collected.append(values.pop(0))
        setattr(namespace, self.dest, collected)

        _, extras = parser._parse_known_args(values, namespace)
        try:
            getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR).extend(extras)
        except AttributeError:
            setattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR, extras)

# ---------------------------------------------------------------------------------------
def main():
    # allow the command line options to change the DEBUGGING flag
    global settings

    # set parse the command line options using argparse
    parser = argparse.ArgumentParser(
        #add_help=False,
        description='Simultaneously push and pull to a catalogue of remote git repositories',
        formatter_class=CustomHelpFormatter,
        prog='git cat',
    )

    # ---------------------------------------------------------------------------------------
    # catalogue options
    # ---------------------------------------------------------------------------------------

    parser.add_argument('-c', '--catalogue', type=str, default=settings.rc_file,
                        help='specify the catalogue of git repositories'
    )
    parser.add_argument('-p', '--prefix', type=str, default=settings.prefix,
                        help='Prefix directory name containing all repositories'
    )
    parser.add_argument('-s', '--set-as-default', action='store_true', default=False,
                        help='use the current options for <command> as the default'
    )

    # help suppressed options
    parser.add_argument('--debugging',
                        action='store_true',
                        default=False,
                        help=argparse.SUPPRESS
    )
    parser.add_argument('-v', '--version',
                        action='version',
                        version=settings.version(),
                        help=argparse.SUPPRESS
    )

    subparsers = parser.add_subparsers(help='Subcommand to run', dest='command')

    # ---------------------------------------------------------------------------------------
    # catalogue commands
    # ---------------------------------------------------------------------------------------
    parser._positionals.title = 'Commands'
    parser._optionals.title = 'Optional arguments'

    add = subparsers.add_parser('add', help='Add repository to the catalogue')
    add.add_argument('repository',
                     type=str,
                     nargs='?',
                     default=os.getcwd(),
                     help='Name of repository to add'
    )

    install = subparsers.add_parser('install', help='Install all repositories in the catalogue')
    install.add_argument('install_reps',
                         type=str,
                         nargs='?',
                         help='Install only specified repository'
    )
    install.add_argument('-d', '--dry-run',
                         action='store_true',
                         default=False,
                         help='Do everything except actually send the updates'
    )
    install.add_argument('-q', '--quiet',
                         action='store_true',
                         default=False,
                         help='print messages'
    )

    ls = subparsers.add_parser('ls', help='List all of the repositories in the catalogue')
    ls.add_argument(dest='repositories', type=str, default='', nargs='?',
                    help='optionally filter the repositories to list'
    )

    remove = subparsers.add_parser('remove', help='Remove repository from the catalogue')
    remove.add_argument('-d', '--delete',
                        action='store_true',
                        default=False,
                        help='Delete directory as well'
    )
    remove.add_argument('repository',
                        type=str,
                        nargs='?',
                        default=None,
                        help='Name of repository to remove'
    )

    # ---------------------------------------------------------------------------------------
    # add git commands using settings and the git-options.ini file
    # ---------------------------------------------------------------------------------------
    settings.add_git_options(subparsers)

    options = parser.parse_args()
    settings.DEBUGGING = options.debugging
    if options.command is None:
        parser.print_help()
        sys.exit(1)

    GitCat(options)

# ---------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
