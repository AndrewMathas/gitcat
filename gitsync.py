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
class Catalogue(dict):
    r"""
    A class for reading, accessing and storing details of the different git
    repositories. These are stored in `filename` in the form:

       rep1 = host1:repository1:directory1
       rep2 = host2:repository2:directory2
       ...

    a file. Any internal spaces in the key name are replaced with underscores
    and lines without a key-value pair are ignored.

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

    def add_repository(self, repository, entry):
        r'''
        Add an `entry` of the form 'key = value' to the catalogue dictionary
        '''
        if '=' in entry:
            rep, dir = entry.split('=')
            rep = rep.lower().replace('-',' ').replace('  ',' ')
            if len(key)>0:
                if rep in self.catalogue[repository]:
                    # give an error if entry does ot match what we have already
                    if self.calogue[repository][rep] != dir:
                        raise ValueError('Repository {} is already catalogued but with rep={}, and dir={}'.format(
                                         self.catalogue[key]['rep'], self.catalogue[key]['dir']))
                else:
                    self.catalogue[repository][key] = dir
        else:
            raise ValueError('{} has no repository-directory pair'.format(entry))

    def read_catalogue(self):
        r'''
        Read the catalogue of git repositories to sync. These are stored in the
        form:
           rep1 = host1:repository1:directory1
           rep2 = host2:repository2:directory2
           ...
        and then put into
        '''
        with open(self.filename, 'r') as catalogue:
            for line in catalogue:
                lineNum += 1
                if line[0] == '#':
                    self.prolog += line
                elif '=' in line:

                    self.add_repository(respository, line)
                elif len(line.strip())>0:
                    raise ValueError('Syntax error in {} on line {}'.format(filename, lineNum))

    def remove_repository(self, rep):
        r'''
        Remove the key-value pair index by `key` from the catalogue dictionary
        '''
        if rep in self.catalogue:
            del self.catalogue[rep]
        else:
            raise ValueError('Unknown repository {}'.format(rep))

    def save_catalogue(self):
        repositories = self.catalogue.keys()
        with open(self.filename, 'w') as catalogue:
            if self.prolog != '':
                catalogue.write(self.prolog+'\n')
            catalogue.write('\n'.join(['{key} = {value}'.format(
                key = key.replace('-',' '), value=self.catalogue[key])
                for key in self.catalogue]))


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

    def get_repository(self):
        r''' 
        Get the repository details for the current directory
        '''
        try:
            details = subprocess.check_output("git remote -v | awk '/fetch/ {print $2}'", shell=True)
            if '/' in details:
                rep, dir = details.split('/')

        except subprocess.CalledProcessError:
            print('Error: Not a git repository')
            sys.exit(1)

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
    parser.add_argument('-a', '--add', nargs=1, type=str, action='store', default=None)
    parser.add_argument('-c', '--catalogue', type=str, default=CATALOGUE,
                        help='Catalogue of bitbucket repositories
    )
    parser.add_argument('-u','--update',action='store_true', default=False,
    parser.add_argument('-i','--install',action='store_true', default=False,
    parser.add_argument('-p','--push',action='store_true', default=False,
                        help='commit and push all repositories to bitbucket'
    )
    parser.add_argument('-q','--quiet',action='store_true', default=False,
                         help='minimise messages'
    )

    options = parser.parse_args()
    if options.add is None and options.install==False and optios.push==False:
        parser.print_help()
        sys.exit(1)

    bitbucket_sync(options)


