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
# Helper commands
def run_command(cmd):
    r'''
    Run the shell command `cmd` and print the output when `verbose` is `True`.
    The subprocess is returned.
    '''
    run = subprocess.run(cmd.strip(), shell=True, capture_output=True)
    return run

# regular expression for [ahead 1], or [behind 1] or [ahead # 2, behind 1] in status
ahead_behind = re.compile(r'\[((ahead|behind) [0-9]+(, )?)+\]')
files_changed = re.compile(r'[0-9]+ file(s|) changed')

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
        changed = run_command('git diff-index --name-only HEAD')
        self.no_warning(rep, 'diff-index', changed)
        return changed.stdout.decode().replace('\n', ' ')

    def commit_repository(self, rep, dir):
        r'''
        Commit the files in the repository with root directory `dir`. The
        commit message is a list of the files being changed.
        '''
        changed_files = self.changed_files(rep)
        if changed_files != '':
            commit_message = 'git cat: updating '+changed_files.strip()
            if self.options.dry_run:
                commit = run_command('git commit -a --porcelain --message="{}"'.format(commit_message))
            else:
                commit = run_command('git commit -a --message="{}"'.format(commit_message))

            return commit

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
            is_git = run_command('git rev-parse --is-inside-work-tree')
            return is_git.returncode == 0 and 'true' in is_git.stdout.decode()

        return False

    def quiet_message(self, msg, ending=None):
        r'''
        If `self.quiet` is `False` then print `msg` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `True` then do nothing.
        '''
        if self.quiet:
            print(msg, end=ending)

    def message(self, msg, ending=None):
        r'''
        If `self.quiet` is `True` then print `msg` to stdout, with `ending`
        as the, well, ending. If `self.quiet` is `False` then do nothing.
        '''
        if not self.quiet:
            print(msg, end=ending)

    def list_catalogue(self):
        r'''
        Return a string that lists the repositories in the catalogue.
        '''
        return '\n'.join('{dir:<{max}} = {rep}'.format(
            dir=dir,
            rep=self.catalogue[dir],
            max=self.max) for dir in sorted(self.catalogue.keys())
        )

    def no_warning(self, rep, action, runcommand):
        r'''
        Print a warning message for the repository `rep`. Here `stderr` is the
        output to stderr from run_command. Return `True` is not warning is
        needed and `False` otherwise
        '''
        #print('Warning: rep={}, action={}, run={}'.format(rep, action,runcommand))
        if runcommand.returncode != 0 or runcommand.stderr != b'':
            print('{rep}: there was an error using {action}\n  {stderr}'.format(
                rep=rep,
                message=action,
                stderr=runcommand.stderr.decode().replace('\n', '\n  ')
            ))
            return False

        # if no error then return True
        return True

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
            catalogue.write(self.list_catalogue())

    # ---------------------------------------------------------------------------------------
    # Now implement the various commands available from the command line
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
        root = run_command('git root')
        if root.returncode != 0:
            self.error_message('{} is not a git repository:\n  {}'.format(
                dir,
                root.stderr.decode().replace('\n', '\n  ')
                )
            )

        rep = run_command('git remote get-url --push origin')
        if rep.returncode != 0:
            self.error_message('Unable to find remote repository for {} :\n  {}'.format(
                dir,
                rep.stderr.decode().replace('\n', '\n  ')
                )
            )

        dir = self.short_path(root.stdout.decode().strip())
        rep = rep.stdout.decode().strip()
        if dir in self.catalogue:
            # give an error if repository is already in the catalogue
            self.error_message('the git repository in {} is already in the catalogue'.format(dir))
        else:
            # add current directory to the repository and save
            self.catalogue[dir] = rep
            self.save_catalogue()
            self.message('Adding {} to the catalogue'.format(dir))

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
                commit = self.commit_repository(rep, dir)


    def diff(self):
        r'''
        Run git diff with various options on the repositories in the
        catalogue.
        '''
        diff_command = 'git diff'
        for option in ['dirstat', 'numstat', 'stat', 'shortstat']:
            opt = getattr(self.options, option)
            if opt == True or opt == None:
                diff_command += ' --'+option
            elif opt != False:
                diff_command += ' --{} = {}'.format(option, opt)

        diff_command += ' HEAD'
        for rep in sorted(self.catalogue.keys()):
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                diff = run_command(diff_command)
                if diff.returncode != 0:
                    self.warning(rep, 'diff-ing', diff)
                elif diff.stdout != b'':
                    if self.quiet:
                        print('{dir:<{max}} {diff}'.format(dir=rep, max=self.max, diff=diff.stdout.decode().strip()))
                    else:
                        print('{}\n  {}'.format(rep, '\n  '.join(f for f in diff.stdout.decode().split('\n') if f != '')))
                else:
                    self.message('{dir:<{max}} up to date'.format(dir=rep, max=self.max))

    def git(self, commands):
        r''' Run git commands on every repository in the catalogue '''
        git_command = 'git {}'.format(' '.join(cmd for cmd in commands))
        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                print('Repository = {}, command = {}'.format(rep, git_command))
                run_command(git_command)

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
                self.message('Installing {:{max}}'.format(rep, max=self.max), ending='')
                parent = os.path.dirname(dir)
                os.makedirs(parent, exist_ok=True)
                os.chdir(parent)
                if not self.options.dry_run:
                    install = run_command('git clone --quiet {rep} {dir}'.format(dir=os.path.basename(dir), rep=self.catalogue[rep]))
                    if self.no_warning(rep, 'clone', install):
                        self.message(' - done!')
            if not (self.options.dry_run or self.is_git_repository(dir)):
                print('{} is not a git repository!?'.format(rep))

    def installed(self):
        r'''
        Print the list of repositories
        '''
        print(self.list_catalogue())

    def pull(self):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer

        TODO: trap errors?/conflicts
        '''
        pull_command = 'git pull'
        for option in ['ff_only', 'strategy', 'stat']:
            opt = getattr(self.options, option)
            if opt == True or opt == None:
                pull_command += ' --'+option.replace('_','-')
            elif opt != False:
                pull_command += ' --{} = {}'.format(option, opt)

        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if os.path.isdir(dir):
                if self.is_git_repository(dir):
                    #self.message('{:<{max}}'.format(rep, max=self.max), ending='')
                    pull = run_command(pull_command)
                    if no_warning(rep, 'pulling', pull):
                        stdout = pull.stdout.decode()
                        if stdout == 'Already up to date.\n':
                            self.message('{rep:<{max}} {pull}'.format(rep=rep, max=self.max, pull=stdout.strip().lower()))
                        else:
                            self.message('{}\n  {}'.format(rep, '\n  '.join(f for f in pull.stdout.decode().split('\n') if f != '')))

    def push(self):
        r'''
        Run through all repositories and push them to bitbucket if their directories
        exist on this computer. Commit the repository if it has changes

        TODO: trap errors?/conflicts
        '''
        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                commit = self.commit_repository(rep, dir)
                if commit is None or self.no_warning(rep, 'committing', commit):
                    if commit is None or commit.stdout == b'':
                        self.message('{:<{max}}'.format(rep, max=self.max), ending='')
                    push = run_command('git push --dry-run --porcelain')
                    if self.no_warning(rep, "pushing", push):
                        if '[up to date]' in push.stdout.decode():
                            self.message('up to date')

                        elif not options.dry_run:
                            push = run_command('git push --porcelain')
                            if self.no_warning(rep, 'pushing', push):
                                stdout = push.stdout.decode().strip()
                                if stdout.startswith('To ') and stdout.endswith('Done'):
                                    self.message('pushed')
                                else:
                                    self.message('pushed\n  {}'.format(stdout.replace('\n','\n  ')))

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
        self.message('Removing {} from the catalgue'.format(dir))
        self.save_catalogue()

        if self.options.delete:
            # remove directory
            self.message('Removing directory {}'.format(dir))
            shutil.rmtree(dir)

    def status(self):
        r'''
        Print the status of all of the repositories in the catalogue
        '''
        status_command = 'git status --branch --short --porcelain --untracked-files={}'.format(self.options.untracked_files)
        diff_command = 'git diff --shortstat --no-color'

        for rep in sorted(self.catalogue.keys()):
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):

                # update  wit remote, unless local is true
                if not self.options.local:
                    remote = run_command('git remote update')
                    self.no_warning(rep, 'updating', remote)

                # use status to work out relative changes
                status = run_command(status_command)
                if self.no_warning(rep, 'status', status):
                    stdout = status.stdout.decode().split('\n')
                    stdout.pop(-1) # remove trailing ''
                    changes = ahead_behind.search(stdout.pop(0))
                    changes = '' if changes is None else changes.group()[1:-1]

                    # use diff to work out which files have changed
                    diff = run_command(diff_command)
                    if self.no_warning(rep, 'diff', diff):
                        changed = files_changed.search(diff.stdout.decode())
                        changed = '' if changed is None else changed.group()

                    if changes!='':
                        changed += changes if changed=='' else ', '+changes

                    if stdout!=[] and not self.quiet:
                        print('{:<{max}} {}\n  {}'.format(
                            rep, changed, '\n  '.join(lin for lin in stdout), 
                            max=self.max)
                        )
                    elif changed!='':
                        print('{:<{max}} {}'.format(rep, changed, max=self.max))
                    else:
                        self.message('{:<{max}} up to date'.format(rep, max=self.max))

    def uninstalled(self):
        r'''
        List the uninstalled repositories in the catalogue
        '''
        for rep in self.catalogue:
            dir = self.expand_path(rep)
            if not os.path.exists(dir):
                self.message('{:<{max}} not installed'.format(rep, max=self.max))

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
                          choice=choice,
                          max=m,
                          help=subparser.format_help(),
                          description=subparser.description,
                          hformat=subparser.format_help(),
                          uformat=subparser.format_usage(),
                          prog=subparser.prog,
                          usage=subparser.usage,
                          phelp=subparser.print_help(),
                          pusage=subparser.print_usage(),
                          sub=dir(subparser)
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


if __name__ == '__main__':

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
    #parser.add_argument('-h', '--help', action=_HelpAction, help='show this help message and exit')  # add custom help
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='print messages'
    )
    parser.add_argument('-p', '--prefix', type=str, default=os.environ['HOME'],
                        help='Prefix directory name containing all repositories'
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

    git = subparsers.add_parser('git', help='Run git commands on all repositories')
    git.add_argument('git', type=str, nargs='+', 
                     help='Run git command on each repository'
    )

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

    installed = subparsers.add_parser('installed', help='List the installed repositories from the catalogue')

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

    subparsers.add_parser('uninstalled', help='List the uninstalled repositories in the catelogue')

    options = parser.parse_args()
    if options.command is None:
        parser.print_help()
        sys.exit(1)

    GitCat(options)
