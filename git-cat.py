#!/usr/bin/env python3

r'''
Simple script to  synchronise all git repositories at once. It uses the
catalogue of repositories as stored in the gitcatrc, which is either in
the directory ~/.dotfiles/config or in the HOME directory.

Andrew Mathas 2018
'''

import argparse
import os
import subprocess
import sys

# ---------------------------------------------------------------------------------------
# Helper commands

# ---------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
class GitCat:
    r"""
    Usage: GitCat(options)

    A class for reading, accessing and storing details of the different git
    repositories. These are stored in `filename` in the form:

       directory1 = repository1
       directory2 = repository2
       ...

    a file. Any lines without a key-value pair are ignored.
    """

    def __init__(self, options):
        self.filename = options.catalogue
        self.options = options
        self.prefix = options.prefix
        self.verbose = options.verbose

        # read the catolgue from the rc file
        self.catalogue = {}
        self.read_catalogue()

        # run corresponding command
        getattr(self, options.command)()

    def changed_files(self):
        r'''
        Return `True` if the repository in the current directory has changed
        and `False` otherwise. We assume that we are in a git repository.
        '''
        try:
            changed = self.run_command('git diff-index --name-only HEAD')
        except subprocess.CalledProcessError:
            self.error('there was a problem running git')

        if changed.returncode != 0:
            self.error('there was a problem running git')

        return changed.stdout.decode().replace('\n', ' ')

    def commit_repository(self, dir):
        r'''
        Commit the files in the repository with root directory `dir`. The
        commit message is a list of the files being changed.
        '''
        changed_files = self.changed_files()
        if changed_files != '':
            commit_message = 'GitCat updating '+changed_files.strip()
            if self.options.dry_run:
                self.run_command('git commit --dry-run -a --message="{}"'.format(commit_message))
            else:
                self.run_command('git commit -a --message="{}"'.format(commit_message))

    def error(self, err):
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
            is_git = self.run_command('git rev-parse --is-inside-work-tree')
            return is_git.returncode == 0 and 'true' in is_git.stdout.decode()

        return False

    def message(self, msg, ending=None):
        r'''
        If `self.verbose` is `True` then print `msg` to stdout, with `ending`
        as the, well, ending. If `self.verbose` is `False` then do nothing.
        '''
        if self.verbose:
            print(msg, ending=end)

    def list_catalogue(self):
        r'''
        Return a string that lists the repositories in the catalogue.
        '''
        return '\n'.join('{dir:<{max}} = {rep}'.format(
                       dir=dir, rep=self.catalogue[dir], max=self.max) for dir in sorted(self.catalogue.keys())
                )

    def short_path(self, dir):
        r'''
        Return the shortened path to the directory `dir` obtained by removing `self.prefix` if
        necessary.
        '''
        return dir[len(self.prefix)+1:] if dir.startswith(self.prefix) else dir

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
                    if '=' in line:
                        dir, rep = line.split('=')
                        dir = dir.strip()
                        if dir in self.catalogue:
                            self.error('{} appears in the catalogue more than once!'.format(dir))
                        elif dir.lower == 'prefix':
                            self.prefix = rep.strip()
                        else:
                            self.catalogue[dir] = rep.strip()
        except (FileNotFoundError, IOError):
            self.error('there was a problem reading the catalogue file {}'.format(self.filename))

        # set the maximum length of a catelogue key
        self.max = max(len(dir) for dir in sorted(self.catalogue))

    def run_command(self, cmd):
        r'''
        Run the shell command `cmd` and print the output when `verbose` is `True`.
        The subprocess is returned.
        '''
        run = subprocess.run(cmd.strip(), shell=True, capture_output=True)
        if run.stderr != b'':
            self.verbose( 'stderr: {}'.format(run.stderr.decode()) )
        return run

    def save_catalogue(self):
        r''' 
        Save the catalogue of git repositories to sync
        '''
        with open(self.filename, 'w') as catalogue:
            catalogue.write('# List of git repositories to sync using gitcat\n\n')
            if self.prefix != os.environ['HOME']:
                print('prefix = {}\n\n'.format(self.prefix))
            catalogue.write(self.list_catalogue())

    # ---------------------------------------------------------------------------------------
    # Now implement the various commands available from the command line
    # ---------------------------------------------------------------------------------------

    def add(self):
        r'''
        Add the current repository to the catalogue
        '''
        if self.options.repository is not None:
            if self.options.repository.startswith('/'):
                os.chdir( self.options.repository )
            else:
                os.chdir( os.path.join(self.prefix, self.options.repository) )

        if not self.is_git_repository('.'):
            self.error('not a git repository')

        try:
            # find the root directory for the repository and the remote URL`
            dir = self.run_command('git root')
            rep = self.run_command('git remote get-url --push origin')

        except subprocess.CalledProcessError:
            self.error('not a git repository')

        if dir.returncode == 0 and rep.returncode == 0:
            dir = self.short_path( dir.stdout.decode().strip() )
            rep = rep.stdout.decode().strip()
            if dir in self.catalogue:
                # give an error if repository is already in the catalogue
                self.error('the git repository in {} is already in the catalogue'.format(dir))
            else:
                # add current directory to the repository and save
                self.catalogue[dir] = rep
                self.save_catalogue()
        elif rep.returncode > 0:
            self.error('Unable to get details of the remote repository for {}'.format(dir.stdout.decode().strip()))
        elif dir.returncode > 0:
            self.error('Unable to get root directory for the repository {}'.format(rep.stdout.decode().strip()))
        else:
            self.error('Unable to get any repository details')

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
                self.commit_repository(dir)

    def git(self, commands):
        r''' Run git commands on every repository in the catalogue '''
        git_command = 'git {}'.format(' '.join(cmd for cmd in commands))
        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                print('Repository = {}, command={}'.format(rep, git_command))
                self.run_command(git_command)

    def install(self):
        r'''
        Install all of the repositories in the catalogue
        '''
        self.pull(install=True)

    def list(self, verbose=False):
        r'''
        Print the list of repositories
        '''
        print(self.list_catalogue())

    def pull(self, install=False):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer or if `install==True`
        '''
        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                self.run_command('git pull')

            elif install:
                self.run_command('git clone {rep} {dir}'.format(dir=rep, rep=self.catalogue[rep]))

            else:
                self.message('')

    def push(self):
        r'''
        Run through all repositories and push them to bitbucket if their directories
        exist on this computer. Commit the repository if it has changes

        TODO: trap errors?/conflicts
        '''
        for rep in self.catalogue:
            self.message('Checking {:<{max}}'.format(rep, max=self.max), ending='')
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                self.commit_repository(dir)

            push = self.run_command('git push --dry-run --porcelain')
            if not options.dry_run:
                if 'up to date' in push.stdout.decode():
                    self.message(' - no changes')
                else:
                    push = self.run_command('git push --quiet --porcelain')
                    if push.returncode == 0:
                        self.message(' - updated')
            if push.returncode != 0:
                print('There was a problem pushing {}:\n  - {}'.format(rep, push.stderr.decode()))

    def remove(self):
        r'''
        Remove the directory `dir` from the catalogue of repositories to sync
        '''
        if self.options.repository is not None:
            dir = self.short_path(os.path.expanduser(self.options.repository))
        else:
            dir = self.short_path(os.getcwd())
        if dir not in self.catalogue:
            self.error('unknown repository {}'.format(dir))

        del self.catalogue[dir]
        self.save_catalogue()

    def status(self):
        r'''
        Print the status of all of the repositories in the catalogue
        '''
        if options.verbose:
            status_command = 'git status --porcelain --untracked-files={}'.format(self.options.untracked_files)
        else:
            status_command = 'git diff --no-color --shortstat HEAD'

        for rep in sorted(self.catalogue.keys()):
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                try:
                    status = self.run_command(status_command)
                except:
                    self.error('there was an error obtaining the status for {}'.format(dir))
                if status.returncode != 0:
                    self.error('There was an error obtaining the status for {}\n  - {}'.format(dir, status.stderr.decode()))
                elif status.stdout != b'':
                    if self.options.verbose:
                        print('{}\n  - {}'.format(rep, '\n  - '.join(f for f in status.stdout.decode().split('\n') if f!='')))
                    else:
                        print('{dir:<{max}} {status}'.format(dir=rep, max=self.max, status = status.stdout.decode().strip()))
                elif self.options.verbose:
                    print('{dir:<{max}} OK'.format(dir=rep, max=self.max))


# ---------------------------------------------------------------------------------------
# location of the gitcatrc file defaults to ~/.dotfiles/config/gitcatrc and
# then to ~/.gitcatrc
if os.path.isdir(os.path.expanduser('~/.dotfiles/config')):
    RC_FILE = os.path.expanduser('~/.dotfiles/config/gitcatrc')
if not os.path.isfile(RC_FILE):
    RC_FILE = os.path.expanduser('~/.gitcatrc')

# ---------------------------------------------------------------------------------------
DRYRUN='''Do not create a commit, but show a list of paths that are to be
committed, paths with local changes that will be left uncommitted and
paths that are untracked.'''

class _HelpAction(argparse._HelpAction):
    r'''
    Override default help and print extendded help for each option.
    Based, in part, on
    https://stackoverflow.com/questions/20094215/argparse-subparser-monolithic-help-output
    '''
    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        # retrieve subparsers from parser
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)]
        # there will probably only be one subparser_action,
        # but better safe than sorry
        m = max(len('{}'.format(choice)) for subparsers_action in subparsers_actions for choice in subparsers_action.choices)
        for subparsers_action in subparsers_actions:
            # get all subparsers and print help
            for choice, subparser in subparsers_action.choices.items():
                print('{choice:>{max}}|{help}\n\nDESCRIPTION: {description}\n\nFORMAT_USAGE: {uformat}\n\nFORMAT_HELP: {hformat}\n\nPRINT HELP: {phelp}\n\nPRINT USAGE: {pusage}\n\nPROG: {prog}\n\nUSAGE: {usage}\nSUBPARSER: {sub}'.format(
                          choice = choice,
                          max = m,
                          help = subparser.format_help(),
                          description = subparser.description,
                          hformat = subparser.format_help(),
                          uformat = subparser.format_usage(),
                          prog = subparser.prog,
                          usage = subparser.usage,
                          phelp = subparser.print_help(),
                          pusage = subparser.print_usage(),
                          sub = dir(subparser)
                      )
                )


        parser.exit()


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
            result = 'command'
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format


if __name__ == '__main__':

    # set parse the command line options using argparse
    parser = argparse.ArgumentParser( 
           #add_help=False,
           description = 'Simultaneously push and pull to a catalogue of remote git repositories',
           formatter_class=CustomHelpFormatter,
           prog = 'git cat',
    )
    parser._positionals.title = 'Commands'
    parser._optionals.title = 'Optional arguments'

    parser.add_argument('-c', '--catalogue', type=str, default=RC_FILE,
                        help='specify the catalogue of bitbucket repositories'
    )
    #parser.add_argument('-h', '--help', action=_HelpAction, help='show this help message and exit')  # add custom help
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='print messages'
    )
    parser.add_argument('-p', '--prefix', type=str, default=os.environ['HOME'],
                        help='Prefix directory name containing all repositories'
    )

    subparsers = parser.add_subparsers(help='Command', dest='command')

    add = subparsers.add_parser('add', help='Add repository to the catalogue',
                                       formatter_class=CustomHelpFormatter,
    )
    add.add_argument('repository', type=str, nargs='?', default=None,
                     help='Name of repository to add')

    commit = subparsers.add_parser('commit', help='Commit all uncommitted repositories in the catalogue')
    commit.add_argument('-n', '--dry-run', action='store_true', default=False, 
                     help=DRYRUN
    )


    git = subparsers.add_parser('git', help='Run git commands on all repositories')
    git.add_argument('commands', type=str, nargs='+', help='')

    install = subparsers.add_parser('install', help='Install all repositories in the catalogue')
    install.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='print messages'
    )

    list = subparsers.add_parser('list', help='List all repositories in the catalogue')

    pull = subparsers.add_parser('pull', help='Pull all repositories in the catalogue')
    pull.add_argument('commands', type=str, nargs='*', help='')
    pull.add_argument('-n','--dry-run', action='store_true', default=False,
                      help='Do everything except actually send the updates'
    )

    push = subparsers.add_parser('push', help='Push all repositories in the catalogue')
    push.add_argument('commands', type=str, nargs='*', help='')
    push.add_argument('-n','--dry-run', action='store_true', default=False,
                      help='Do everything except actually send the updates'
    )
    push.add_argument('-v', '--verbose', action='store_true', default=False,
                      help='Print messages each time a repository is pushed')

    remove = subparsers.add_parser('remove', help='Remove repository from the catalogue')
    remove.add_argument('repository', type=str, nargs='?', default=None,
                        help='Name of repository to remove')


    status = subparsers.add_parser('status', help='Print the status of each repository in the catalogue')
    status.add_argument('-v','--verbose', action='store_true', default=False,
                        help='List the file changes in all repositories')
    status.add_argument('-u','--untracked-files', choices=['no', 'normal','all'], default='no',
                        help='Show untracked files using git status mode'
    )

    options = parser.parse_args()
    if options.command is None:
        parser.print_help()
        sys.exit(1)

    GitCat(options)
