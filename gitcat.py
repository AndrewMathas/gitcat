#!/usr/bin/env python3

r'''
A command line tool for synchroning a catalogue of git repositories. It uses
the catalogue of repositories as stored in the gitcatrc, which is either in the
directory ~/.dotfiles/config or in the HOME directory.

Andrew Mathas 2018
'''

import argparse
import os
import re
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------------------
# settings
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
    def Version(self):
        return 'git cat version {}'.format(self.version)

settings = Settings(os.path.join(os.path.dirname(__file__),'gitcat.ini'))

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
     - stdout     the output from the subprocess command
     - stdout     the stderr from the subprocess command
     Both stdout and stderr are decoded and stripped.
    """
    def __init__(self, rep, command, options=None):
        # run command
        git = subprocess.run(
                'git {} {}'.format(command, options).strip(),
                shell=True,
                capture_output=True
        )

        # store the output
        self.rep=rep
        self.returncode = git.returncode
        self.stderr = git.stderr.decode().strip()
        self.stdout = git.stdout.decode().strip()
        self.git = git

        if self.returncode != 0 or self.stderr != '':
            print('{}: there was an error using git {}\n  {}\n'.format(
                rep,
                command,
                self.stderr.replace('\n', '\n  '),
            ))
            self.git_command_ok = False
        else:
            self.git_command_ok = True

    def __bool__(self):
        ''' return 'self.is_ok` '''
        return self.git_command_ok

# ---------------------------------------------------------------------------------------
# regular expression for [ahead 1], or [behind 1] or [ahead # 2, behind 1] in status
ahead_behind = re.compile(r'\[((ahead|behind) [0-9]+(, )?)+\]')
files_changed = re.compile(r'[0-9]+ file(s|) changed')

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
        self.filename = options.catalogue
        self.options = options
        self.prefix = options.prefix
        self.quiet = options.quiet

        # read the catolgue from the rc file
        self.catalogue = {}
        self.read_catalogue()

        # run corresponding command
        getattr(self, options.command)()

    def changed_files(self, rep):
        r'''
        Return list of files repository in the current directory that have
        changed.  We assume that we are in a git repository.
        '''
        return Git(rep, 'diff-index', '--name-only HEAD')

    def commit_repository(self, rep, dir):
        r'''
        Commit the files in the repository with root directory `dir`.
        The commit message is a list of the files being changed. Return
        the Git() record of the commit.
        '''
        changed_files = self.changed_files(rep)
        if changed_files and changed_files.stdout != '':
            commit_message = 'git cat: updating '+changed_files.stdout.replace('\n', ' ')
            commit =  '-a --message="{}"'.format(commit_message)
            if self.options.dry_run:
                commit += ' --porcelain'
            return Git(rep, 'commit', commit)
        # return False as nothing was committed
        changed_files.git_command_ok = False
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
        if os.path.isdir(dir):
            os.chdir(dir)
            rep = dir.replace(self.prefix+'/', '')
            is_git = Git(rep, 'rev-parse', '--is-inside-work-tree')
            return is_git.returncode == 0 and 'true' in is_git.stdout

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
                sep = '=' if listing or self.is_git_repository(self.expand_path(dir)) else '!',
                max=self.max)
            for dir in sorted(self.catalogue.keys())
        )

        # if no error then return True
        return True

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
        try:
            with open(self.filename, 'r') as catalogue:
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
            self.error_message('there was a problem reading the catalogue file {}'.format(self.filename))

        # set the maximum length of a catelogue key
        self.max = max(len(dir) for dir in sorted(self.catalogue)) + 1

    def save_catalogue(self):
        r'''
        Save the catalogue of git repositories to sync
        '''
        with open(self.filename, 'w') as catalogue:
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

    # ---------------------------------------------------------------------------------------
    # messages
    # ---------------------------------------------------------------------------------------

    def message(self, msg, ending=None):
        r'''
        If `self.quiet` is `True` then print `msg` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `False` then do nothing.
        '''
        if not self.quiet:
            print(msg, end=ending)

    def quiet_message(self, msg, ending=None):
        r'''
        If `self.quiet` is `False` then print `msg` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `True` then do nothing.
        '''
        if self.quiet:
            print(msg, end=ending)

    def rep_message(self, rep, msg='', quiet=True, ending=None):
        r'''
        If `self.quiet` is `True` then print `msg` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `False` then do nothing.
        '''
        if not(quiet and self.quiet):
            print('{:<{max}} {}'.format(rep, msg, max=self.max, end=ending))

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
                dir,
                root.stderr.replace('\n', '\n  ')
                )
            )

        rep = Git(dir, 'remote', 'get-url --push origin')
        if not rep:
            self.error_message('Unable to find remote repository for {} :\n  {}'.format(
                dir,
                rep.stderr.replace('\n', '\n  ')
                )
            )

        dir = self.short_path(root.stdout)
        rep = rep.stdout
        if dir in self.catalogue:
            # give an error if repository is already in the catalogue
            self.error_message('the git repository in {} is already in the catalogue'.format(dir))
        else:
            # add current directory to the repository and save
            self.catalogue[dir] = rep
            self.save_catalogue()
            self.message('Adding {} to the catalogue'.format(dir))

    def cat(self):
        r'''
        Print the list of repositories
        '''
        print(self.list_catalogue(listing=False))

    def commit(self):
        r'''
        Commit all of the repositories in the catalogue where files have
        changed. The work is actually done by `self.commit_repository`, which
        commits only one repository, since other methods need to call this as
        well.
        '''
        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                self.commit_repository(rep, dir)

    def diff(self):
        r'''
        Run git diff with various options on the repositories in the
        catalogue.
        '''
        options = ''
        for option in ['dirstat', 'numstat', 'stat', 'shortstat']:
            opt = getattr(self.options, option)
            if opt == True or opt == None:
                options += ' --'+option
            elif opt != False:
                options += ' --{}={}'.format(option, opt)

        options += ' HEAD'
        for rep in sorted(self.catalogue.keys()):
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                diff = Git(rep, 'diff' 'options')
                if diff:
                    if diff.stdout != '':
                        self.rep_message(
                            rep,
                            '\n  {}'.format(rep, '\n  '.join(f for f in diff.stdout.split('\n') if f != '')),
                            quiet=False
                        )
                    else:
                        self.rep_message(rep, 'up to date')

    def git(self, commands):
        r''' Run git commands on every repository in the catalogue '''
        git_command = '{}'.format(' '.join(cmd for cmd in commands))
        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                print('Repository = {}, command = {}'.format(rep, git_command))
                Git(git_command)

    def install(self):
        r'''
        Install some or all of the repositories in the catalogue
        '''
        if self.options.install != None:
            reps_to_install = self.options.install
        else:
            reps_to_install = self.catalogue.keys()

        for rep in reps_to_install:
            dir = self.expand_path(rep)
            if not os.path.exists(dir):
                self.rep_message(rep, 'installing')
                parent = os.path.dirname(dir)
                os.makedirs(parent, exist_ok=True)
                os.chdir(parent)
                if not self.options.dry_run:
                    install = Git(rep, 'clone', '--quiet {rep} {dir}'.format(dir=os.path.basename(dir), rep=self.catalogue[rep]))
                    if install:
                        self.message(' - done!')
            if not (self.options.dry_run or self.is_git_repository(dir)):
                print('{} is not a git repository!?'.format(rep))

    def pull(self):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer
        '''
        options = '-q'
        for option in ['ff_only', 'strategy', 'stat']:
            opt = getattr(self.options, option)
            if opt == True or opt == None:
                options += ' --'+option.replace('_','-')
            elif opt != False:
                options += ' --{}={}'.format(option, opt)

        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                pull = Git(rep, 'pull', options)
                if pull:
                    stdout = pull.stdout
                    if stdout == 'Already up to date.\n':
                        self.rep_message(rep, stdout.lower())
                    else:
                        self.rep_message(
                            rep,
                            '\n  '.join(f for f in stdout.split('\n') if f != '')
                        )
            else:
                self.rep_message(rep, 'not on system')

    def push(self):
        r'''
        Run through all repositories and push them to bitbucket if their directories
        exist on this computer. Commit the repository if it has changes
        '''
        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                commit = self.commit_repository(rep, dir)
                if commit:
                    if commit.stdout == '':
                        self.rep_message(rep)
                    push = Git(rep, 'push', '--dry-run --porcelain')
                    if push:
                        if '[up to date]' in push.stdout:
                            self.message('up to date')
                        elif self.options.dry_run:
                            self.rep_message(
                                rep,
                                'dry-run\n {}'.format(push.stdout.replace('\n','\n  '))
                            )
                        else:
                            push = Git(rep, 'push', '--porcelain')
                            if push:
                                if push.stdout.startswith('To ') and push.stdout.endswith('Done'):
                                    self.rep_message(rep, 'pushed')
                                else:
                                    self.rep_message(rep, 'pushed\n  {}'.format(push.stdout.replace('\n','\n  ')))

                else:
                    self.rep_message(rep, 'no changes')
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

    def status(self):
        r'''
        Print the status of all of the repositories in the catalogue
        '''
        status_options = '--branch --short --porcelain --untracked-files={}'.format(
                              self.options.untracked_files
                          )
        diff_options = '--shortstat --no-color'

        for rep in sorted(self.catalogue.keys()):
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):

                # update with remote, unless local is true
                remote = self.options.local or Git(rep, 'remote','update')

                if remote:
                    # use status to work out relative changes
                    status = Git(rep, 'status', status_options)
                    if status:
                        stdout = status.stdout.split('\n')
                        changes = ahead_behind.search(stdout.pop(0))
                        changes = '' if changes is None else changes.group()[1:-1]

                        # use diff to work out which files have changed
                        changed = ''
                        diff = Git(rep, 'diff', diff_options)
                        if diff:
                            changed = files_changed.search(diff.stdout)
                            changed = '' if changed is None else changed.group()

                        if changes!='':
                            changed += changes if changed=='' else ', '+changes

                        if stdout != [] and not self.quiet:
                            self.rep_message(
                                rep,
                                '{}\n  {}'.format(changed, '\n  '.join(lin for lin in stdout)),
                                quiet=False
                            )
                        elif changes != '':
                            self.rep_message(rep, changes)
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
            return "  {:{width}} -  {}\n".format(subcommand, help_text, width = width)

        elif type(action) == argparse._SubParsersAction:
            # process subcommand help section
            msg = '\n'
            for subaction in action._get_subactions():
                msg += self._format_action(subaction)
            return msg
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
            else:
                return (result, ) * tuple_size
        return format

import itertools
class CollectUnknown(argparse.Action):
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

    # set parse the command line options using argparse
    parser = argparse.ArgumentParser(
           #add_help=False,
           description='Simultaneously push and pull to a catalogue of remote git repositories',
           formatter_class=CustomHelpFormatter,
           prog='git cat',
    )
    parser._positionals.title = 'Commands'
    parser._optionals.title = 'Optional arguments'

    parser.add_argument('-c', '--catalogue', type=str, default=RC_FILE,
                        help='specify the catalogue of bitbucket repositories'
    )
    parser.add_argument('-p', '--prefix', type=str, default=os.environ['HOME'],
                        help='Prefix directory name containing all repositories'
    )
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='print messages'
    )
    parser.add_argument(
            '-v', '--version',
            action='version',
            version=settings.Version(),
            help=argparse.SUPPRESS
    )

    subparsers = parser.add_subparsers(help='Subcommand to run', dest='command')

    add = subparsers.add_parser('add', help='Add repository to the catalogue',
                                       formatter_class=CustomHelpFormatter,
    )
    add.add_argument('repository', type=str, nargs='?', default=os.getcwd(),
                     help='Name of repository to add')

    commit = subparsers.add_parser('commit', help='Commit all uncommitted repositories in the catalogue')
    commit.add_argument('-n', '--dry-run', action='store_true', default=False,
                     help=DRYRUN
    )

    diff = subparsers.add_parser('diff', help='Print a diff of the changes in each repository')
    diff.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='List the file changes in all repositories'
    )
    diff.add_argument('--shortstat', action='store_true', default=False,
                      help='Output only the last line of the --stat format'
    )
    diff.add_argument('--numstat', action='store_true', default=False,
                      help='Similar to --stat, but shows number of added and deleted lines without abbreviation'
    )
    diff.add_argument('--dirstat', nargs='?', type=str, default=False,
                        help='Output the distribution of relative amount of changes for each sub-directory'
    )
    diff.add_argument('--stat', nargs='?', type=str, default=False,
                        help='Generate a diffstat using git diff --stat = ...'
    )

#    git = subparsers.add_parser(
#        'git', 
#        action = CollectUnknown,
#        help='Run git commands on all repositories'
#    )

    install = subparsers.add_parser('install', help='Install all repositories in the catalogue')
    install.add_argument('install_reps', type=str, nargs='?',
                         help='Install only specified repository'
    )
    install.add_argument('-n', '--dry-run', action='store_true', default=False,
                      help='Do everything except actually send the updates'
    )
    install.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='print messages'
    )

    installed = subparsers.add_parser('cat', help='List all of the repositories in the catalogue')

    pull = subparsers.add_parser('pull', help='Pull all repositories in the catalogue')
    pull.add_argument('commands', type=str, nargs='*', help='')
    pull.add_argument('-n', '--dry-run', action='store_true', default=False,
                      help='Print what would be done without doing it'
    )
    pull.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='Print messages when pulling each repository')
    pull.add_argument('-f', '--ff-only', action='store_true', default=False,
                      help='Fast-forward only merge')
    pull.add_argument('-s', '--strategy', nargs='?', type=str, default=False,
                      help='Use the given merge strategy.')
    pull.add_argument('--stat', action='store_true', default=False,
                      help='Show a diffstat at the end of the merge.')

    push = subparsers.add_parser('push', help='Push all repositories in the catalogue')
    push.add_argument('commands', type=str, nargs='*', help='')
    push.add_argument('-n', '--dry-run', action='store_true', default=False,
                      help='Do everything except actually send the updates'
    )
    push.add_argument('-q', '--quiet', action='store_true', default=False,
                      help='Print messages each time a repository is pushed')

    remove = subparsers.add_parser('remove', help='Remove repository from the catalogue')
    remove.add_argument('-d', '--delete', action='store_true', default=False,
                        help='Delete directory as well'
    )
    remove.add_argument('repository', type=str, nargs='?', default=None,
                        help='Name of repository to remove'
    )

    status = subparsers.add_parser('status', help='Print the status of each repository in the catalogue')
    status.add_argument('-l', '--local', action='store_true', default=False,
                        help='Only compare with local repositories'
    )
    status.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='Only list changes the repositories'
    )
    status.add_argument('-u', '--untracked-files', choices = ['no', 'normal', 'all'], default='no',
                        help='Show untracked files using git status mode'
    )

    options = parser.parse_args()
    if options.command is None:
        parser.print_help()
        sys.exit(1)

    GitCat(options)

# ---------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
