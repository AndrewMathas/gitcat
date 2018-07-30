#!/usr/bin/env python3

r'''
Simple script to  synchronise all bitbucket repositories at once. It uses
the catalogue of repositories as stored in CATALOGUE, in the home directory

Andrew Mathas February 2018
'''

CATALOGUE = '.dotfiles/config/gitsync'

import argparse
import os
import subprocess
import sys

# ---------------------------------------------------------------------------------------
PROLOG=r'''# List of git repositories to sync using gitsync'''

class Catalogue(dict):
    r"""
    A class for reading, accessing and storing details of the different git
    repositories. These are stored in `filename` in the form:

       directory1 = repository1
       directory2 = repository2
       ...

    a file. Any lines without a key-value pair are ignored.

    The key-value pairs are available as both attributes and items

    Usage: MetaData(filename)
    """
    def __init__(self, filename):
        super().__init__()
        dict.__init__(self)
        self.filename = filename
        self.prolog=''
        self.repositories = dict()
        self.catalogue = {}
        repository = None
        lineNum = 0
        self.read_catalogue()

    def __getitem__(self, key):
        r'''
        Override setitem so that it looks in the catalogue dictionary
        '''
        if key in self.catalogue:
            return self.catalogue[key]
        else:
            return dict.__getitem__(key)

    def __setitem__(self, key, value):
        r'''
        Override setitem so that it looks in the catalogue dictionary
        '''
        self.catalogue[key] = value

    def __getattr__(self, name):
        if key in self.catalogue:
            return self.catalogue[key]
        else:
            raise ValueError('Unknown key {}'.format(key))

    def add_repository(self):
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
                raise ValueError('The current repository {} is already n thng synced'.format(dir))
            else:
                # add to the repository and save
                self.catalogue[dir] = rep
                self.save_catalogue()
        else:
            raise ValueError('Not a valid git repository?'.format(entry))

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
        with open(self.filename, 'r') as catalogue:
            for line in catalogue:
                if '=' in line:
                    dir, rep = line.split('=')
                    dir = dir.strip()
                    if dir in self.catalogue:
                        raise ValueError('{} appears in the catalogue more than once!;'.format(dir))
                    else:
                        self.catalogue[dir] = rep.strip()

    def remove_repository(self, dir):
        r'''
        Remove the directory `dir` from the catalogue of repositories rto sync
        '''
        if rdir in self.catalogue:
            del self.catalogue[dir]
        else:
            raise ValueError('Unknown repository {}'.format(dir))
        self.save_catalogue()

    def save_catalogue(self):
        r''' Save the catalogue of git repositories to sync '''
        max = max(len(dir) for dir in self.catalogue)
        with open(self.filename, 'w') as catalogue:
            catalogue.write(PROLOG+'\n')
            catalogue.write('\n'.join(
                ['{dir:<{max}} = {rep}'.format(dir=dir, rep=self.catalogue[rep], max=max)]
            )


# ---------------------------------------------------------------------------------------
class bitbucket_sync(object):

    def __init__(self, options):
        self.catalogue = Catalogue( self.catalogue )

        # directory manipulation routines
        self.directory_exists = lambda dir: os.path.isdir(os.path.join(os.environ['HOME'], dir))
        self.chdir = lambda dir: os.chdir(os.path.join(os.environ['HOME'], dir))
        self.mkdir = lambda dir: os.makedirs(os.path.join(os.environ['HOME'], dir))

        if options.quiet:
            self.run  = lambda cmd: subprocess.call(cmd, shell=True, stdout=open(os.devnull, 'wb'))
        else:
            self.run  = lambda cmd: subprocess.call(cmd, shell=True)

        if options.push:
            self.push_respositories()

        elif options.install:
            self.update_respositories(install=True)

        elif options.update:
            self.update_respositories()

        elif options.add is not None:
            self.catalogue.add_repository( options.add )
            self.catalogue.save_catalogue()

        elif options.remove is not None:
            self.catalogue.remove_repository( options.add )
            self.catalogue.save_catalogue()


    def push_respositories():
        r'''
        Run through all repositories and push them to bitbucket if their directories
        exist on this computer. Commit the repository if it has changes

        TODO: trap errors?
        '''
        for repository in self.catalogue:
            if self.directory_exists(self.catalogue[repository]):
                self.chdir(self.catalogue[repository])
                try:
                    self.run('git diff --quiet 2> /dev/null || git commit --quiet -m "{}" 2> /dev/null'.format(
                             'Saving and pushing repository')
                    )
                except:
                    print('There was an error pushing the repository in {}'.format(self.catalogue[repository]))

    def update_respositories(self, install=False):
        r'''
        Run through all repositories and update them if their directories
        already exist on this computer or if `install==True`
        '''
        for repository in self.catalogue:
            for rep in self.catalogue[repository]:
            if not self.directory_exists(self.catalogue[repository]) and install:
                self.mkdir( self.catalogue[repository])

            if self.directory_exists(self.catalogue[repository]):
                self.chdir( self.catalogue[repository])
                if not self.directory_exists(self.catalogue[repository]+'/.git'):
                    self.run('git clone https://{0.host}/{0.rep}.git {0.dir}'.format(rep))
                else:
                    self.run('git pull')

# ---------------------------------------------------------------------------------------
if __name__ == '__main__':

    # set parse the command line options using argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--add', action='store_true', default=False,
                        help='Add current repository to the catalogue'
    )
    parser.add_argument('-r', '--remove', action='store_true', default=False,
                        help='Remove current repository from the catalogue'
    )
    parser.add_argument('-c', '--catalogue', type=str, default=CATALOGUE,
                        help='specify the catalogue of bitbucket repositories'
    )
    parser.add_argument('-s','--update',action='store_true', default=False,
                        help='Syncronise, or pull, all repositories in the catalogue'
    )
    parser.add_argument('-i','--install',action='store_true', default=False,
                        help='Install of the repositories listed in the catalogue'
    )
    parser.add_argument('-p','--push',action='store_true', default=False,
                        help='Commit and push all repositories to bitbucket'
    )
    parser.add_argument('-q','--quiet',action='store_true', default=False,
                        help='minimise messages'
    )

    options = parser.parse_args()
    if options.add is None and options.install==False and optios.push==False:
        parser.print_help()
        sys.exit(1)

    bitbucket_sync(options)


