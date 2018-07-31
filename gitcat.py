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
run_quiet = lambda cmd: subprocess.run(cmd.strip().split(' '), capture_output=True)
run_verbose = lambda cmd: subprocess.run(cmd.strip().split(' '), stdout=open(os.devnull, 'wb'))

def is_git_repository(dir):
    r' Return `True` if `dir` is a git repository and `False` otherwise'
    if os.path.isdir(dir):
        os.chdir(dir)
        is_git = run_quiet('git rev-parse --is-inside-work-tree')
        return is_git.returncode == 0 and 'true' in is_git.stdout.decode()

    return False

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
        self.prefix = options.prefix
        self.filename = options.catalogue
        self.options = options
        self.catalogue = {}
        self.read_catalogue()

        if options.quiet:
            self.run  = lambda cmd: run_quiet(cmd)
        else:
            self.run  = lambda cmd: run_verbose(cmd)

        # run corresponding command
        print('options={}'.format(options))
        getattr(self, options.command)()

    def error(self, err):
        r'''
        Print error message amd exit.
        '''
        print('git cat: error - {}'.format(err))
        sys.exit(1)

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
                            raise ValueError('{} appears in the catalogue more than once!;'.format(dir))
                        elif dir.lower == 'prefix':
                            self.prefix = rep.strip()
                        else:
                            self.catalogue[dir] = rep.strip()
        except (FileNotFoundError, IOError):
            print('There was an error reading the catalogue file {}'.format(self.filename))
            sys.exit(1)

    def list_catalogue(self):
        r'''
        Return a string that lists the repositories in the catalogue.
        '''
        m = max(len(dir) for dir in sorted(self.catalogue))
        return '\n'.join('{dir:<{max}} = {rep}'.format(
                       dir=dir, rep=self.catalogue[dir], max=m) for dir in sorted(self.catalogue.keys())
                )

    def path(self, dir):
        r'''
        Return the path to the directory `dir`, adding `self.prefix` if
        necessary.
        '''
        return dir if dir.startswith('/') else os.path.join(self.prefix, dir)

    def short_path(self, dir):
        r'''
        Return the shortened path to the directory `dir` obtained by removing `self.prefix` if
        necessary.
        '''
        return dir[len(self.prefix)+1:] if dir.startswith(self.prefix) else dir

    def changed_files(self):
        r'''
        Return `True` if the repository in the current directory has changed
        and `False` otherwise. We assume that we are in a git repository.
        '''
        try:
            changed = run_quiet('git diff-index --name-only HEAD')
        except subprocess.CalledProcessError:
            self.error('there was a problem running git')

        if status.returncode != 0:
            self.error('there was a problem running git')

        return changed.stdout.decode().replace('\n', ' ')

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
        try:
            # find the root directory for the repository and the remote URL`
            dir = run_quiet('git root')
            rep = run_quiet('git remote get-url --push origin')

        except subprocess.CalledProcessError:
            self.error('not a git repository')

        if dir.returncode == 0 and rep.returncode == 0:
            dir = self.short_path( dir.stdout.decode().strip() )
            rep = rep.stdout.decode().strip()
            if dir in self.catalogue:
                # give an error if repository is already in the catalogue
                print('The git repository in {} is already being synced'.format(dir))
                sys.exit(1)
            else:
                # add current directory to the repository and save
                self.catalogue[dir] = rep
                self.save_catalogue()
        elif rep.returncode > 0:
            raise ValueError('Unable to get remote repository details for the repository in {}'.format(dir.stdout.decode().strip()))
        elif dir.returncode > 0:
            raise ValueError('Unable to get root directory for the repository {}'.format(rep.stdout.decode().strip()))
        else:
            raise ValueError('Unable to get any repository details')

    def commit(self):
        for rep in self.catalogue:
            dir = self.path(rep)
            changed_files = self.changed_files()
            if changed_files != '':
                changed_files = 'GitCat updating '+changed_files
                self.run('git commit -a --message "{}"'.format(changed_files)

    def git(self, commands):
        r''' Run git commands on every repository in the catalogue '''
        git_command = 'git {}'.format(' '.join(cmd for cmd in commands))
        for rep in self.catalogue:
            dir = self.path(rep)
            if is_git_repository(dir):
                os.chdir(dir)
                print('Repository = {}, command={}'.format(rep, git_command))
                self.run(git_command)

    def install(self):
        r'''
        Install all of the repositories in the catalogue
        '''
        self.pull(install=True)

    def list(self, verbose=False):
        r'''
        Print the list of repositories
        '''
        print(self.list_catalogue(verbose))

    def pull(self, install=False):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer or if `install==True`
        '''
        for rep in self.catalogue:
            dir = self.path(rep)
            if is_git_repository(dir):
                os.chdir(dir)
                self.run('git pull')

            elif install:
                self.run('git clone {rep} {dir}'.format(dir=rep, rep=self.catalogue[rep]))

            else:
                self.message('')

    def push(self):
        r'''
        Run through all repositories and push them to bitbucket if their directories
        exist on this computer. Commit the repository if it has changes

        TODO: trap errors?
        '''
        for rep in self.catalogue:
            dir = self.path(rep)
            if is_git_repository(dir):
                os.chdir(dir)
                commit = self.commit(rep)
                if commit:
                    push = self.run('git push --dry-run --porcelain')
                    if push.returncode == 0 and not options.dry_run:
                        run_quiet('git push --porcelain')
                    else:
                        print('{} - {}'.format(rep, push.stderr.decode()))
                except:
                    print('There was an error pushing the repository in {}'.format(rep))

    def remove(self):
        r'''
        Remove the directory `dir` from the catalogue of repositories to sync
        '''
        dir = self.short_path(os.getcwd())
        if dir not in self.catalogue:
            raise ValueError('Unknown repository {}'.format(dir))

        del self.catalogue[dir]
        self.save_catalogue()

    def status(self):
        r'''
        Print the status of all of the repositories in the catalogue
        '''
        m = max(len(dir) for dir in sorted(self.catalogue))
        if options.short:
            status_command = 'git diff --no-color --shortstat HEAD'
        else:
            status_command = 'git status --porcelain --untracked-files={}'.format(self.options.untracked_files)

        for rep in sorted(self.catalogue.keys()):
            dir = self.path(rep)
            if is_git_repository(dir):
                os.chdir(dir)
                try:
                    status = run_quiet(status_command)
                except:
                    print('There was an error obtaining the status for {}'.format(dir))
                if status.returncode != 0:
                    print('There was an error obtaining the status for {}\n  - {}'.format(dir, status.stderr.decode()))
                elif status.stdout != b'':
                    if self.options.short:
                        print('{dir:<{max}} {status}'.format(dir=rep, max=m, status = status.stdout.decode().strip()))
                    else:
                        print('{}\n  - {}'.format(rep, '\n  - '.join(f for f in status.stdout.decode().split('\n') if f!='')))


# ---------------------------------------------------------------------------------------
# location of the gitcatrc file defaults to ~/.dotfiles/config/gitcatrc and
# then to ~/.gitcatrc
if os.path.isdir(os.path.expanduser('~/.dotfiles/config')):
    RC_FILE = os.path.expanduser('~/.dotfiles/config/gitcatrc')
if not os.path.isfile(RC_FILE):
    RC_FILE = os.path.expanduser('~/.gitcatrc')

# ---------------------------------------------------------------------------------------
if __name__ == '__main__':

    # set parse the command line options using argparse
    parser = argparse.ArgumentParser( 
           description = 'Cathronise multiple git repositories with external repositories',
           usage = 'gitcat [options] <command> [args]'
    )
    parser.add_argument('-c', '--catalogue', type=str, default=RC_FILE,
                        help='specify the catalogue of bitbucket repositories'
    )

    parser.add_argument('-q','--quiet',action='store_true', default=False,
                        help='minimise messages'
    )
    parser.add_argument('-p', '--prefix', type=str, default=os.environ['HOME'],
                        help='Prefix directory name containing all repositories'
    )
    subparsers = parser.add_subparsers(help='Command', dest='command')

    subparsers.add_parser('add', help='Add current repository to the catalogue')

    subparsers.add_parser('commit', help='Commit all uncommitted repositories in the catalogue')

    git = subparsers.add_parser('git', help='Run git commands on all repositories')
    git.add_argument('commands', type=str, nargs='+', help='')

    subparsers.add_parser('install', help='Install all repositories in the catalogue')

    list = subparsers.add_parser('list', help='List all repositories in the catalogue')
    list.add_argument('-v', '--verbose', dest='commands', type=str, help='verbose')

    subparsers.add_parser('missing', help='List the repositories in the catalogue')

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
    subparsers.add_parser('remove', help='Remove current repository from the catalogue')

    status = subparsers.add_parser('status', help='Print the status of each repository in the catalogue')
    status.add_argument('-s','--short', action='store_true', default=False,
                        help='Give the output in the short-format')
    status.add_argument('-u','--untracked-files', choices=['no', 'normal','all'], default='no',
                        help='Show untracked files using git status mode'
    )

    options = parser.parse_args()
    if options.command is None:
        parser.print_help()
        sys.exit(1)

    GitCat(options)
