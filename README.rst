
git-cat
=======

*Herding a catalogue of git repositories*


usage: git cat [-h] [-c CATALOGUE] [-p PREFIX] [-q] <command> [options] ...

Simultaneously synchronise multiple local and remote git repositories

Optional arguments:
  -h, --help            show this help message and exit
  -c CATALOGUE, --catalogue CATALOGUE
                        specify the catalogue of git repositories (default:
                        /Users/andrew/.dotfiles/config/gitcatrc)
  -p PREFIX, --prefix PREFIX
                        Prefix directory name containing all repositories
  -q, --quiet           Print messages only if repository changes

Commands:
  :add:       Add current repository to the catalogue
  :branch:    Print status of all branches in repository
  :commit:    Commit changes in all repositories
  :diff:      Print a diff of the changes in each repository
  :fetch:     Fetch all repositories from remote repositories
  :install:   Install repository from the catalogue
  :ls:        List all repositories in the catalogue
  :pull:      Pull all repositories from remote repositories
  :push:      Commit and push local repositories to remote repositories
  :remove:    Remove repository from the catalogue
  :status:    Print the status of all repositories


**add**

usage: git cat add [-h] [-d GIT_DIRECTORY] [-q]

Add current repository to the catalogue

optional arguments:
  -h, --help            show this help message and exit
  -d GIT_DIRECTORY, --directory GIT_DIRECTORY
                        Add repository from specified directory
  -q, --quiet           only print "important" messages

Add the current repository to the catalogue stored in gitcatrc. An
error is returned if the current directory is not a git repository, if
it is a git repository but has no remote or if the repository is
already in the catalogue.

**branch**

usage: git cat branch [-h] [-q] [repositories]

Print status of all branches in repository

positional arguments:
  repositories  optionally filter repositories for status

optional arguments:
  -h, --help    show this help message and exit
  -q, --quiet   only print "important" messages

Run `git branch --verbose` in selected repositories in the
catagalogue.

Example:

.. code-block::

    > git cat branch Code
    Code/Autoweb
      python3 6c2fcd5 Converting to python 3
    Code/Bibupdate
      master  2d2614e [ahead 1] Adding annouce and notes to ctan_specs
    Code/GitCat        already up to date
    Code/GitLPDF       already up to date
    Code/GradedSpecht
      Antons_deformation 14fc541 Adding braid method to tableau
      * cartan_type        68480a4 git cat: updating   graded_specht/klr_algebras.py
      master             862e2f4 Adding braid method to tableau
    Code/PG            already up to date
    Code/SmartUnits
      master cdb337a Minor bug fixes
    Code/WebQuiz       already up to date

**commit**

usage: git cat commit [-h] [-a] [-b] [-d] [-v] [-q] [repositories]

Commit changes in all repositories

positional arguments:
  repositories   optionally filter repositories for status

optional arguments:
  -h, --help     show this help message and exit
  -a, --all      automatically stage files that have been modified and deleted
  -b, --branch   Show the branch and tracking information
  -d, --dry-run  Show what would be committed without committing
  -v, --verbose  Print a unified diff for the commit
  -q, --quiet    only print "important" messages

Commit all of the repositories in the catalogue where files have
changed. The work is actually done by `self.commit_repository`, which
commits only one repository, since other methods need to call this as
well.

**diff**

usage: git cat diff [-h] [--name-only] [--name-status] [--numstat]
                    [--shortstat] [--summary] [-q]
                    [repositories]

Print a diff of the changes in each repository

positional arguments:
  repositories   optionally filter repositories for status

optional arguments:
  -h, --help     show this help message and exit
  --name-only    Show only names of changed files
  --name-status  Show only names and status of changed files
  --numstat      Show number of added and deleted lines without abbreviating
  --shortstat    Print number of modified files and number of added/deleted line
  --summary      Print condensed summary of changes
  -q, --quiet    only print "important" messages

Run git diff with various options on the repositories in the
catalogue.

**fetch**

usage: git cat fetch [-h] [--all] [--dry-run] [-f] [-p] [-t] [-q]
                     [repositories]

Fetch all repositories from remote repositories

positional arguments:
  repositories  optionally filter repositories for status

optional arguments:
  -h, --help    show this help message and exit
  --all         Fetch all branches
  --dry-run     Print what would be done without doing it
  -f, --force   Fetch even if there are changes
  -p, --prune   Before fetching, remove any remote-tracking references that no longer exist on the remote
  -t, --tags    Fetch all tags from remote repositories
  -q, --quiet   only print "important" messages

Run through all repositories and update them if their directories
already exist on this computer

**install**

usage: git cat install [-h] [-d] [-q] [repositories]

Install repository from the catalogue

positional arguments:
  repositories   optionally filter repositories for status

optional arguments:
  -h, --help     show this help message and exit
  -d, --dry-run  Do everything except actually install the repositories
  -q, --quiet    only print "important" messages

Install listed repositories from the catalogue.

If a directory exists but is not a git repository then initialise the
repository and fetch from the remote.

**ls**

usage: git cat ls [-h] [-q] [repositories]

List all repositories in the catalogue

positional arguments:
  repositories  optionally filter repositories for status

optional arguments:
  -h, --help    show this help message and exit
  -q, --quiet   only print "important" messages

List the repositories managed by git cat

**pull**

usage: git cat pull [-h] [--all] [-d] [--ff-only] [--squash] [--stat] [-t]
                    [-s [STRATEGY]] [--recursive] [--theirs] [--ours] [-q]
                    [repositories]

Pull all repositories from remote repositories

positional arguments:
  repositories          optionally filter repositories for status

optional arguments:
  -h, --help            show this help message and exit
  --all                 Pull all branches
  -d, --dry-run         Print what would be done without doing it
  --ff-only             Fast-forward only merge
  --squash              Squash the merge
  --stat                Show a diffstat at the end of the merge
  -t, --tags            Fetch all tags from remote repositories
  -s [STRATEGY], --strategy [STRATEGY]
                        Use the specified merge strategy
  --recursive           Use recursive three-way merge
  --theirs              Resolve merge conflicts favouring remote repository
  --ours                Resolve merge conflicts favouring local repository
  -q, --quiet           only print "important" messages

Run through all repositories and update them if their directories
already exist on this computer

**push**

usage: git cat push [-h] [-d] [--all] [--prune] [--tags] [-q] [repositories]

Commit and push local repositories to remote repositories

positional arguments:
  repositories   optionally filter repositories for status

optional arguments:
  -h, --help     show this help message and exit
  -d, --dry-run  Do everything except actually send the updates
  --all          Push all branches
  --prune        Remove remote branches that don't have a local counterpart
  --tags         Push all tags
  -q, --quiet    only print "important" messages

Run through all repositories and push them to bitbucket if their directories
exist on this computer. Commit the repository if it has changes

**remove**

usage: git cat remove [-h] [-e] [-d GIT_DIRECTORY] [-q]

Remove repository from the catalogue

optional arguments:
  -h, --help            show this help message and exit
  -e, --everything      Delete everything, including the directory
  -d GIT_DIRECTORY, --directory GIT_DIRECTORY
                        Remove repository from specified directory
  -q, --quiet           only print "important" messages

Remove the directory `dire` from the catalogue of repositories to sync

**status**

usage: git cat status [-h] [-l] [-u CHOICE] [-q] [repositories]

Print the status of all repositories

positional arguments:
  repositories          optionally filter repositories for status

optional arguments:
  -h, --help            show this help message and exit
  -l, --local           Only compare with local repositories
  -u CHOICE, --untracked-files CHOICE
                        Show untracked files using git status mode (all, no, or normal)
  -q, --quiet           only print "important" messages

Print the status of all of the repositories in the catalogue
Author
======

Andrew Mathas

git-cat Version 1.0

Copyright (C) 2018

GNU General Public License, Version 3, 29 June 2007

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License (GPL_) as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

.. _bitbucket: https://bitbucket.org/
.. _github: https://github.com
.. _GPL: http://www.gnu.org/licenses/gpl.html
.. _Python: https://www.python.org/
