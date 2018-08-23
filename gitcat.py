#!/usr/bin/env python3

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

import argparse
import itertools
import os
import re
import shutil
import subprocess
import sys

class Option:
    '''
    A keyword-value container
    '''
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

class CommandLineOptions:
    '''
    An argparse helper class for synchronising the git-cat options and their
    defaults with the settings in the rc file.  This is used to both set the
    default options and to automatically generate them in main() using
    argparse>
    '''

    # a dictionary of the git commands supported with their help messages
    commands = dict(
        branch = Option(help='List local and remote branches together with last commit message'),
        commit = Option(help='Commit all uncommitted repositories in the catalogue'),
        diff   = Option(help='Print a diff of the changes in each repository'),
        fetch  = Option(help='Fetch all repositories in the catalogue'),
        pull   = Option(help='Pull all repositories in the catalogue'),
        push   = Option(help='Push all repositories in the catalogue to their remote repositories'),
        status = Option(help='Print the status of each repository in the catalogue')
    )
    def __init__(self):
        # initialise an empty list of options for each command
        for cmd in self.commands:
            self.commands[cmd].options = []

    def add_option(self,
        command,             # the git-cat command name
        option,              # the name of the option
        help,                # help for option
        default=False,       # default value
        action='store_true', # default action
        shorthand=None,      # the option shorthand (default option[0])
        choices=None
        ):
        '''
        Add a command-line to the list of options for command
        '''
        self.commands[command].options.append(Option(
            long_option=option,
            short_hand = option[0] if shorthand is None else shorthand,
            git_cat_default = default,
            default = default,
            action = action,
            choices = choice
        ))

    def add_argparse_options(self, subparser):
        '''
        Generate all of the git-cat command options as parsers of `subparser`
        '''
        for cmd in self.commands:
            cmd = subparser.add_parser(cmd, help=self.commands[command]['help'])
            for option in self.commands[cmd].options:
                cmd.add_argument(
                    '-'+option.short_hand,
                    '--'+option.long_option,
                    action=option.action,
                    default=option.default,
                    dest='git_'+option.long_option,
                    help=option.help
                )
            # finally, add the optional repository filter option
            cmd.add_argument(
                dest='repositories',
                type=str,
                default='',
                nargs='?',
                help='optionally filter repositories for status'
            )

# ---------------------------------------------------------------------------------------
# settings
class Settings(dict):
    r"""
    A dummy class for reading and storing key-value pairs that are read from a file
    """
    DEBUGGING = False

    def __init__(self, filename):
        super().__init__()
        self.options = CommandLineOptions()
        with open(filename, 'r') as meta:
            for line in meta:
                key, val = line.split('=')
                if key.strip() != '':
                    setattr(self, '_'+key.strip().lower(), val.strip())

    def version(self):
        """ return gitcat version """
        return 'git cat version {}'.format(self._version)

    def command_line_options(self):
        r'''
        Set the command line options using argparse and specifications
        in `self.options`.
        '''
        pass

settings = Settings(os.path.join(os.path.dirname(__file__), 'gitcat.ini'))

def Debugging(message):
    """ print a debugging message if `debugging` is true"""
    if settings.DEBUGGING:
        print(message)

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
            Debugging('-'*40)
            print('{}: there was an error using git {}\n  {}\n'.format(
                rep,
                command,
                git.stderr.decode().strip().replace('\n', '\n  ').replace('\r','\n  '),
            ))
            Debugging('-'*40)
            self.git_command_ok = False
        else:
            self.git_command_ok = True

        # output is indented two spaces and has no blank lines
        self.output = git.stdout.decode()
        self.output = '\n'.join('  '+lin.strip()
             for lin in (git.stdout.decode().replace('\r','n').strip().split('\n')
                        +git.stderr.decode().replace('\r','n').strip().split('\n'))
                 if lin != ''
        )
        Debugging('{}\nstdout={}\nstderr={}'.format(self,git.stdout,git.stderr))

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
# regular expression for [ahead 1], or [behind 1] or [ahead # 2, behind 1] in status
ahead_behind = re.compile(r'\[((ahead|behind) [0-9]+(, )?)+\]')
files_changed = re.compile(r'([0-9]+ file(?:s|))(?: changed)')

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
        self.quiet = options.quiet

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
        Debugging('\nCOMMIT rep='+rep)
        changed_files = self.changed_files(rep)
        if changed_files and changed_files.output != '':
            commit_message = 'git cat: updating '+changed_files.output
            commit = '--all --message="{}"'.format(commit_message)
            if self.options.dry_run:
                commit += ' --porcelain'
            return Git(rep, 'commit', commit)


        return changed_files

    def error_message(self, err):
        r'''
        Print error message amd exit.
        '''
        print('git cat error: {}'.format(err))
        sys.exit(1)

    def expand_path(self, dir):
        r'''
        Return the path to the directory `dir`, adding `self.prefix` if
        necessary.
        '''
        return dir if dir.startswith('/') else os.path.join(self.prefix, dir)

    def is_git_repository(self, dir):
        r'''
        Return `True` if `dir` is a git repository and `False` otherwise. As
        part of testing for a repository the current working directory is also
        changed to `dir`.
        '''
        Debugging('\nCHECKING for git dir={}'.format(dir))
        if os.path.isdir(dir):
            os.chdir(dir)
            rep = dir.replace(self.prefix+'/', '')
            is_git = Git(rep, 'rev-parse', '--is-inside-work-tree')
            return is_git.returncode == 0 and 'true' in is_git.output

        return False

    def list_catalogue(self, listing):
        r'''
        Return a string that lists the repositories in the catalogue. If
        `listing` is `False` and the repository does not exist then the
        separator is an exclaimation mark, otherwise it is an equals sign.
        '''
        return '\n'.join('{dir:<{max}} {sep} {rep}'.format(
            dir=dir,
            rep=self.catalogue[dir],
            sep='=' if listing or self.is_git_repository(self.expand_path(dir)) else '!',
            max=self.max
            ) for dir in self.repositories()
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
                    Debugging('option {}={} ignored'.format(option, val))
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
                        dir, rep = line.split(' = ')
                        dir = dir.strip()
                        if dir in self.catalogue:
                            self.error_message('{} appears in the catalogue more than once!'.format(dir))
                        elif dir.lower == 'prefix':
                            self.prefix = rep.strip()
                        else:
                            self.catalogue[dir] = rep.strip()
        except (FileNotFoundError, IOError):
            self.error_message('there was a problem reading the catalogue file {}'.format(self.gitcatrc))

        # set the maximum length of a catalogue key
        try:
            self.max = max(len(dir) for dir in self.repositories()) + 1
        except ValueError:
            self.max = 0

    def save_catalogue(self):
        r'''
        Save the catalogue of git repositories to sync
        '''
        with open(self.gitcatrc, 'w') as catalogue:
            catalogue.write('# List of git repositories to sync using gitcat\n\n')
            if self.prefix != os.environ['HOME']:
                print('prefix = {}\n\n'.format(self.prefix))
            catalogue.write(self.list_catalogue(listing=True))

    def short_path(self, dir):
        r'''
        Return the shortened path to the directory `dir` obtained by removing `self.prefix`
        if necessary.
        '''
        return dir[len(self.prefix)+1:] if dir.startswith(self.prefix) else dir

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
            Debugging('-'*40)
            print(message, end=ending)
            Debugging('-'*40)

    def quiet_message(self, message, ending=None):
        r'''
        If `self.quiet` is `False` then print `message` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `True` then do nothing.
        '''
        if self.quiet:
            Debugging('-'*40)
            print(message, end=ending)
            Debugging('-'*40)

    def rep_message(self, rep, message='', quiet=True, ending=None):
        r'''
        If `self.quiet` is `True` then print `message` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `False` then do nothing.
        '''
        Debugging('rep message: quiet={}, self.quiet={} and quietness={}\n{}'.format(
                  quiet, self.quiet, not(quiet and self.quiet),'-'*40
                 )
        )
        if not(quiet and self.quiet):
            print('{:<{max}} {}'.format(rep, message, max=self.max, end=ending))
            Debugging('-'*40)

    # ---------------------------------------------------------------------------------------
    # Now implement the git cat commands available from the command line
    # ---------------------------------------------------------------------------------------

    def add(self):
        r'''
        Add the current repository to the catalogue
        '''
        if self.options.repository.startswith('/'):
            dir = self.options.repository
        else:
            dir = os.path.join(self.prefix, self.options.repository)

        if not (os.path.isdir(dir) and self.is_git_repository(dir)):
            self.error_message('{} not a git repository'.format(dir))

        # find the root directory for the repository and the remote URL`
        os.chdir(dir)
        root = Git(dir, 'root')
        if not root:
            self.error_message('{} is not a git repository:\n  {}'.format(
                dir, root.output)
            )

        rep = Git(dir, 'remote', 'get-url --push origin')
        if not rep:
            self.error_message('Unable to find remote repository for {} :\n  {}'.format(
                dir, rep.output)
            )

        dir = self.short_path(root.output)
        rep = rep.output
        if dir in self.catalogue:
            # give an error if repository is already in the catalogue
            self.error_message('the git repository in {} is already in the catalogue'.format(dir))
        else:
            # add current directory to the repository and save
            self.catalogue[dir] = rep
            self.save_catalogue()
            self.message('Adding {} to the catalogue'.format(dir))

            # check to see if the gitcatrc is in a git repository and, if so,
            # add a commit message
            catdir = os.path.dirname(self.gitcatrc)
            if self.is_git_repository(catdir):
                Git(dir, 'commit', '--all --message="{}"'.format('Adding {} to gitcatrc'.format(dir)))

    def branch(self):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer
        '''
        # need to use -q to stop output being printed to stderr, but then we
        # have to work harder to extract information about the pull
        options = self.process_options('--verbose')
        for rep in self.repositories():
            Debugging('\nBRANCH '+rep)
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
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
            Debugging('\nCOMMITTING '+rep)
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                self.commit_repository(rep)

    def diff(self):
        r'''
        Run git diff with various options on the repositories in the
        catalogue.
        '''
        options = self.process_options()
        options += ' HEAD'
        for rep in self.repositories():
            Debugging('\nDIFFING '+rep)
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
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
            Debugging('\nFETCHING '+rep)
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
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
            Debugging('\nGITTING '+rep)
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                print('Repository = {}, command = {}'.format(rep, git_command))
                Git(git_command)

    def install(self):
        r'''
        Install some or all of the repositories in the catalogue
        '''
        for rep in self.repositories():
            Debugging('\nINSTALLING '+rep)
            dir = self.expand_path(rep)
            if not os.path.exists(dir):
                self.rep_message(rep, 'installing')
                parent = os.path.dirname(dir)
                os.makedirs(parent, exist_ok=True)
                os.chdir(parent)
                if not self.options.dry_run:
                    install = Git(rep, 'clone', '--quiet {rep} {dir}'.format(
                        dir=os.path.basename(dir),
                        rep=self.catalogue[rep])
                    )
                    if install:
                        self.message(' - done!')
            if not (self.options.dry_run or self.is_git_repository(dir)):
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
            Debugging('\nPULLING '+rep)
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
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
            Debugging('\nPUSHING '+rep)
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                Debugging('Continuing with push')
                commit = self.commit_repository(rep)
                if commit:
                    if commit.output != '':
                        self.rep_message(rep, 'commit\n'+commit.output)
                    push = Git(rep, 'push', options+' --dry-run')
                    if push:
                        if '[up to date]' in push.output:
                            self.rep_message(rep, 'up to date')
                        elif not self.options.dry_run:
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
        Remove the directory `dir` from the catalogue of repositories to sync
        '''
        if self.options.repository is not None:
            rep = self.short_path(os.path.expanduser(self.options.repository))
        else:
            rep = self.short_path(os.getcwd())
        dir = self.expand_path(rep)
        if not (rep in self.catalogue and self.is_git_repository(dir)):
            self.error_message('unknown repository {}'.format(dir))

        del self.catalogue[rep]
        self.message('Removing {} from the catalogue'.format(dir))
        self.save_catalogue()

        if self.options.delete:
            # remove directory
            self.message('Removing directory {}'.format(dir))
            shutil.rmtree(dir)

            # check to see if the gitcatrc is in a git repository and, if so,
            # add a commit message
            catdir = os.path.dirname(self.gitcatrc)
            if self.is_git_repository(catdir):
                Git(dir, 'commit', '--all --message "{}"'.format('Removing {} from gitcatrc'.format(dir)))

    def status(self):
        r'''
        Print the status of all of the repositories in the catalogue
        '''
        status_options = self.process_options('--porcelain --short --branch')
        diff_options = '--shortstat --no-color'

        for rep in self.repositories():
            Debugging('\nSTATUS for {}'.format(rep))
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):

                # update with remote, unless local is true
                remote = self.options.local or Git(rep, 'remote', 'update')

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

                        Debugging('changes = {}\nchanged={}\nstatus={}'.format(changes, changed, status.output))

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
# location of the gitcatrc file defaults to ~/.dotfiles/config/gitcatrc and
# then to ~/.gitcatrc
if os.path.isdir(os.path.expanduser('~/.dotfiles/config')):
    RC_FILE = os.path.expanduser('~/.dotfiles/config/gitcatrc')
if not os.path.isfile(RC_FILE):
    RC_FILE = os.path.expanduser('~/.gitcatrc')

# ---------------------------------------------------------------------------------------
DRYRUN = '''Do not create a commit, but show a list of paths that are to be
committed, paths with local changes that will be left uncommitted and
paths that are untracked.'''

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

    parser.add_argument('-c', '--catalogue', type=str, default=RC_FILE,
                        help='specify the catalogue of bitbucket repositories'
    )
    parser.add_argument('-p', '--prefix', type=str, default=os.environ['HOME'],
                        help='Prefix directory name containing all repositories'
    )
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='print messages'
    )
    parser.add_argument('-s', '--set-as-default', action='store_true', default=False,
                        help='use the current options as the default'
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
    install.add_argument(dest='repositories', type=str, default='', nargs='?',
                         help='optionally filter the repositories to install')

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
    # git commands
    # ---------------------------------------------------------------------------------------

    # options with destinations of the form git_<name> designate command line
    # options for git that gitcat will pass through for the relevant command
    branch = subparsers.add_parser('branch',
        help = 'List local and remote branches together with last commit message'
    )

    commit = subparsers.add_parser('commit', help='Commit all uncommitted repositories in the catalogue')
    commit.add_argument('-d', '--dry-run',
                        action='store_true',
                        default=False,
                        dest='git_dry_run',
                        help=DRYRUN
    )
    commit.add_argument(dest='repositories', type=str, default='', nargs='?',
                        help='optionally filter the repositories to commit')

    diff = subparsers.add_parser('diff', help='Print a diff of the changes in each repository')
    diff.add_argument('-q', '--quiet',
                      action='store_true',
                      default=False,
                      dest='git_quiet',
                      help='List the file changes in all repositories'
    )
    diff.add_argument('--shortstat',
                      action='store_true',
                      default=False,
                      dest='git_shortstat',
                      help='Output only the last line of the --stat format'
    )
    diff.add_argument('--numstat',
                      action='store_true',
                      default=False,
                      dest='git_numstat',
                      help='Similar to --stat, but shows number of added and deleted lines without abbreviation'
    )
    diff.add_argument('--dirstat',
                      nargs='?',
                      type=str,
                      default=False,
                      dest='git_dirstat',
                      help='Output the distribution of relative amount of changes for each sub-directory'
    )
    diff.add_argument('--stat',
                      nargs='?',
                      type=str,
                      default=False,
                      dest='git_stat',
                      help='Generate a diffstat using git diff --stat = ...'
    )
    diff.add_argument(dest='repositories', type=str, default='', nargs='?',
                      help='optionally filter the repositories to diff')

    fetch = subparsers.add_parser('fetch', help='Fetch all repositories in the catalogue')
    fetch.add_argument('--all',
                      action='store_true',
                      default=False,
                      dest='git_all',
                      help='Pull all branches'
    )
    fetch.add_argument('-d', '--dry-run',
                      action='store_true',
                      default=False,
                      dest='git_dry_run',
                      help='Print what would be done without doing it'
    )
    fetch.add_argument('-q', '--quiet',
                      action='store_true',
                      default=False,
                      dest='git_quiet',
                      help='Print messages when fetching each repository'
    )
    fetch.add_argument('-f', '--force',
                      action='store_true',
                      default=False,
                      dest='git_force',
                      help='Before fetching, remove any remote-tracking references that no longer exist on the remote'
    )
    fetch.add_argument('-p', '--prune',
                      action='store_true',
                      default=False,
                      dest='git_prune',
                      help='Before fetching, remove any remote-tracking references that no longer exist on the remote'
    )
    fetch.add_argument('--tags',
                      action='store_true',
                      default=False,
                      dest='git_tags',
                      help='Fetch all refs under refs/tags'
    )
    fetch.add_argument(dest='repositories', type=str, default='', nargs='?',
                      help='optionally filter the repositories to fetch'
    )

#    git = subparsers.add_parser(
#        'git',
#        action = CollectArguments,
#        help='Run git commands on all repositories'
#    )

    pull = subparsers.add_parser('pull', help='Pull all repositories in the catalogue')
    pull.add_argument('--all',
                      action='store_true',
                      default=False,
                      dest='git_all',
                      help='Pull all branches'
    )
    pull.add_argument('-d', '--dry-run',
                      action='store_true',
                      default=False,
                      dest='git_dry_run',
                      help='Print what would be done without doing it'
    )
    pull.add_argument('-q', '--quiet',
                      action='store_true',
                      default=False,
                      help='Print messages when pulling each repository'
    )
    pull.add_argument('-f', '--ff-only',
                      action='store_true',
                      default=False,
                      dest='git_ff_only',
                      help='Fast-forward only merge'
    )
    pull.add_argument('--stat',
                      action='store_true',
                      default=False,
                      dest='git_stat',
                      help='Show a diffstat at the end of the merge.')
    pull.add_argument(dest='repositories', type=str, default='', nargs='?',
                      help='optionally filter the repositories to pull'
    )
    pull.add_argument('--tags',
                      action='store_true',
                      default=False,
                      dest='git_tags',
                      help='Pull all refs under refs/tags'
    )
    # shorthands for merge strategies
    pull.add_argument('-s', '--strategy',
                      nargs='?', type=str,
                      action='append',
                      default=None,
                      dest='git_strategy',
                      help='Use the given merge strategy.'
    )
    # TODO: these options are not quiet right: need to fix
    for strategy in [ 'ours', 'ignore-all-space', 'ignore-cr-at-eol',
        'ignore-space-at-eol', 'ignore-space-change', 'octopus', 'patience',
        'recursive' 'renormalize', 'resolve', 'subtree', 'theirs']:
        pull.add_argument('--'+strategy,
            action='append_const',
            const=strategy,
            dest='git_strategy',
            help="Use merge strategy '{}' when pulling repositories".format(strategy)
        )

    push = subparsers.add_parser('push', help='Push all repositories in the catalogue to their remote repositories')
    push.add_argument('-d', '--dry-run',
                      action='store_true',
                      default=False,
                      help='Do everything except actually send the updates'
    )
    push.add_argument('--all',
                      action='store_true',
                      default=False,
                      dest='git_all',
                      help='Push all branches'
    )
    push.add_argument('--follow-tags',
                      action='store_true',
                      default=False,
                      dest='git_follow_tags',
                      help='Push all the refs that would be pushed without this option, and also push annotated tags in refs/tags that are missing from the remote but are pointing at commit-ish that are reachable from the refs being pushed'
    )
    push.add_argument('--tags',
                      action='store_true',
                      default=False,
                      dest='git_tags',
                      help='All refs under refs/tags are pushed'
    )
    push.add_argument('-q', '--quiet',
                      action='store_true',
                      default=False,
                      help='Print messages each time a repository is pushed')
    push.add_argument(dest='repositories', type=str, default='', nargs='?',
                      help='optionally filter the repositories to push')

    status = subparsers.add_parser('status',
                                   help='Print the status of each repository in the catalogue'
    )
    status.add_argument('-l', '--local',
                        action='store_true',
                        default=False,
                        help='Only compare with local repositories'
    )
    status.add_argument('-q', '--quiet',
                        action='store_true',
                        default=False,
                        help='Only list changes the repositories'
    )
    status.add_argument('-u', '--untracked-files',
                        choices=['no', 'normal', 'all'],
                        default='no',
                        dest='git_untracked_files',
                        help='Show untracked files using git status mode'
    )
    status.add_argument(dest='repositories', type=str, default='', nargs='?',
                        help='optionally filter repositories for status')

    options = parser.parse_args()
    settings.DEBUGGING = options.debugging
    if options.command is None:
        parser.print_help()
        sys.exit(1)

    GitCat(options)

# ---------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
