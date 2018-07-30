#!/usr/bin/env python3

r'''
Simple script to  synchronise all git repositories at once. It uses the
catalogue of repositories as stored in the gitsyncrc, which is either in
the directory ~/.dotfiles/config or in the HOME directory.

Andrew Mathas 2018
'''

import argparse
import os
import subprocess
import sys

# ---------------------------------------------------------------------------------------
# Helper commands
is_git_repository = lambda rep: subprocess.run('git rev-parse --is-inside-work-tree', shell=True, capture_output=True).returncode==0
run_quiet   = lambda cmd: subprocess(cmd.split(' '), capture_output=True)
run_verbose = lambda cmd: subprocess(cmd.split(' '), stdout=open(os.devnull, 'wb'))

# ---------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
class GitSync:
    r"""
    Usage: GitSync(options)

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
        self.catalogue = {}
        self.read_catalogue()

        if options.quiet:
            self.run  = lambda cmd: run_quiet(cmd)
        else:
            self.run  = lambda cmd: run_verbose(cmd)

        # run corresponding command
        if options.command == 'list':

        if hasattr(options, 'commands'):
            getattr(self, options.command)(options.commands)
        else:
            getattr(self, options.command)()

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
                        else:
                            self.catalogue[dir] = rep.strip()
        except (FileNotFoundError, IOError):
            print('There was an error reading the catalogue file {}'.format(self.filename))
            sys.exit(1)

    def list_catalogue(self):
        r'''
        Return a string that lists the repositories in the catalogue.
        '''
        m = max(len(dir) for dir in self.catalogue)
        return '\n'.join('{dir:<{max}} = {rep}'.format(
                       dir=dir, rep=self.catalogue[dir], max=m) for dir in sorted(self.catalogue.keys())
                )

    def save_catalogue(self):
        r''' 
        Save the catalogue of git repositories to sync
        '''
        with open(self.filename, 'w') as catalogue:
            catalogue.write(r'# List of git repositories to sync using gitsync\n')
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
            dir = subprocess.check_output('git root', shell=True)
            rep = subprocess.check_output('git remote get-url --push origin', shell=True)

        except subprocess.CalledProcessError:
            raise ValueError('Error: Not a git repository')

        if len(dir)>0 and len(rep)>0:
            if rep in self.catalogue:
                # give an error if repository is already in the catalogue
                raise ValueError('The current repository {} is already being synced'.format(dir))
            else:
                # add to the repository and save
                self.catalogue[dir] = rep
                self.save_catalogue()
        elif len(dir)>0:
            raise ValueError('Unable to get remote repository details for the repository in {}'.format(dir))
        elif len(rep)>0:
            raise ValueError('Unable to get root directory for the repository {}'.format(rep))
        else:
            raise ValueError('Unable to get any repository details')

    def commit(self):
        raise NotImplementedError('commit not yet implemented')

    def git(self, commands):
        r''' Run git commands on every repository in the catalogue '''
        git_command = 'git {}'.format(' '.join(cmd for cmd in commands))
        for rep in self.catalogue:
            dir = os.path.join(self.prefix, rep)
            if is_git_repository(dir):
                os.chdir(dir)
                print('Repository = {}, command={}'.format(rep, git_command))
                self.run(git_command)

    def install(self):
        r'''
        Install all of the repositories in the catalogue
        '''
        self.pull(install=true)

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
            dir = os.path.join(self.prefix, rep)
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
            dir = os.path.join(self.prefix, rep)
            if is_git_repository(dir):
                os.chdir(dir)
                try:
                    self.run('git diff --quiet 2> /dev/null || git commit --quiet -m "{}" 2> /dev/null'.format(
                             'Saving and pushing repository')
                    )
                    self.run('git push')
                except:
                    print('There was an error pushing the repository in {}'.format(self.catalogue[repository]))

    def remove(self):
        r'''
        Remove the directory `dir` from the catalogue of repositories to sync
        '''
        if dir not in self.catalogue:
            raise ValueError('Unknown repository {}'.format(dir))

        del self.catalogue[dir]
        self.save_catalogue()

    def status(self):
        r'''
        Print the status of all of the repositories in the catalogue
        '''
        for rep in self.catalogue:
            dir = os.path.join(self.prefix, rep)
            if is_git_repository(dir):
                os.chdir(dir)
                try:
                    self.run('git status')
                except:
                    print('There was an error obtaining the status for {}'.format(dir))


# ---------------------------------------------------------------------------------------
# location of the gitsyncrc file
if os.path.isdir(os.path.expanduser('~/.dotfiles/config')):
    RC_FILE = os.path.expanduser('~/.dotfiles/config/gitsyncrc')
if not os.path.isfile(RC_FILE):
    RC_FILE = os.path.expanduser('~/.gitsyncrc')

# ---------------------------------------------------------------------------------------
if __name__ == '__main__':

    # set parse the command line options using argparse
    parser = argparse.ArgumentParser( 
           description = 'Synchronise multiple git repositories with external repositories',
           usage = 'gitsync [options] <command> [args]'
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

    subparsers.add_parser('pull', help='Pull all repositories in the catalogue')

    subparsers.add_parser('push', help='Push all repositories in the catalogue')

    subparsers.add_parser('remove', help='Remove current repository from the catalogue')

    subparsers.add_parser('status', help='Obtain the status of the repositories in the catalogue')

    options = parser.parse_args()
    if options.command is None:
        parser.print_help()
        sys.exit(1)

    GitSync(options)
