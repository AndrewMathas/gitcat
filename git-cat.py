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

        print('options = {}'.format(options))
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

    def list_catalogue(self):
        r'''
        Return a string that lists the repositories in the catalogue.
        '''
        m = max(len(dir) for dir in sorted(self.catalogue))
        return '\n'.join('{dir:<{max}} = {rep}'.format(
                       dir=dir, rep=self.catalogue[dir], max=m) for dir in sorted(self.catalogue.keys())
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

    def run_command(self, cmd):
        r'''
        Run the shell command `cmd` and print the output when `verbose` is `True`.
        The subprocess is returned.
        '''
        run = subprocess.run(cmd.strip(), shell=True, capture_output=True)
        if self.verbose:
            if run.stderr != b'':
                print('stderr: {}'.format(run.stderr.decode()) )
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
                self.error('the git repository in {} is already being synced'.format(dir))
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

        TODO: trap errors?
        '''
        for rep in self.catalogue:
            if self.verbose:
                print('pushing from the repository {}'.format(rep))
            dir = self.expand_path(rep)
            if self.is_git_repository(dir):
                self.commit_repository(dir)

            push = self.run_command('git push --dry-run --porcelain')
            if push.returncode != 0:
                print('push = {}'.format(push))
                print('{} - {}'.format(rep, push.stderr.decode()))
            elif not options.dry_run:
                self.run_command('git push --quiet --porcelain')

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
        m = max(len(dir) for dir in sorted(self.catalogue))
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
                        print('{dir:<{max}} {status}'.format(dir=rep, max=m, status = status.stdout.decode().strip()))
                elif self.options.verbose:
                    print('{dir:<{max}} OK'.format(dir=rep, max=m))


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

if __name__ == '__main__':

    # set parse the command line options using argparse
    parser = argparse.ArgumentParser( 
           description = 'Cathronise multiple git repositories with external repositories',
           usage = 'gitcat [options] <command> [args]'
    )
    parser.add_argument('-c', '--catalogue', type=str, default=RC_FILE,
                        help='specify the catalogue of bitbucket repositories'
    )

    parser.add_argument('-v','--verbose', action='store_true', default=False,
                        help='minimise messages'
    )
    parser.add_argument('-p', '--prefix', type=str, default=os.environ['HOME'],
                        help='Prefix directory name containing all repositories'
    )
    subparsers = parser.add_subparsers(help='Command', dest='command')

    add = subparsers.add_parser('add', help='Add repository to the catalogue')
    add.add_argument('repository', type=str, nargs='?', default=None,
                     help='Name of repository to add')

    commit = subparsers.add_parser('commit', help='Commit all uncommitted repositories in the catalogue')
    commit.add_argument('-n', '--dry-run', action='store_true', default=False, 
                     help=DRYRUN
    )


    git = subparsers.add_parser('git', help='Run git commands on all repositories')
    git.add_argument('commands', type=str, nargs='+', help='')

    subparsers.add_parser('install', help='Install all repositories in the catalogue')

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
    push.add_argument('-v','--verbose', action='store_true', default=False,
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
