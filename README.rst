
==========
`git cat`_
==========

*Herding a catalogue of git repositories*

usage: git cat [-c CATALOGUE] [-p PREFIX] [-q] [-h] <command> [options] ...

Simultaneously synchronise multiple local and remote git repositories

Optional arguments:
  -c CATALOGUE, --catalogue CATALOGUE
                        specify the catalogue of git repositories (default:
                        /Users/andrew/.dotfiles/config/gitcatrc)
  -p PREFIX, --prefix PREFIX
                        Prefix directory name containing all repositories
  -q, --quiet           Print messages only if repository changes
  -h, --help            help: for extended help use -hh and -hhh

Commands::

  add        Add current repository to the catalogue
  branch     Print status of all branches in each repository
  commit     Commit changes in all repositories
  diff       Print a diff of the changes in each repository
  fetch      Fetch all repositories from remote repositories
  install    Install repository from the catalogue
  ls         List all repositories in the catalogue
  pull       Pull all repositories from remote repositories
  push       Change all remote URLs to use ssh access
  remove     Remove repository from the catalogue
  status     Print the status of all repositories



`Git cat` is a command line tool for synchronising multiple git repositories
with remote servers from the command line. This tool is not intended to be used
on large projects with multiple developers but, instead, it is aimed at the
lone developer who has wants to synchronise multiple git repositories that live
on several computers. In particular, with one `git cat` command you can run git
commands on multiple git repositories, such as pushing or pulling from remote
servers, such as bitbucket_ and github_. When pushing, any local changes to the
repositores will be automatically commited.

`Git cat` provides only a thin veneer over git. It does not support all git
commands and nor does it support the full functionality of those git commands
that it does support. The `git cat` philosophy is to "do no harm" so, when
possible, it uses dry-runs before changing any repository and it wil only
change a repository if the dry-run succeeds. Any problems encountered by `git
cat` are printed to the terminal (stdout). The aim of `git cat` is to
streamline the management of multiple git repositories so, by default, it
prints a summary of what it does to each repository to the terminal.

By default, the `git cat` commands are applied to all of the repositories that
are managed by `git cat`, however, repositories that the command is applied to
by supplying a regular expression.

*Examples*:

.. code-block:: bash

    > git cat pull       # pull from all repositories
    > git cat pull Code  # pull from all "Code" repositories

This makes it possible, for example, to push or pull from related git
repositories that are in different directories.

The remote repositories are accessed in the normal way using git. Ideally, they
will be set up with ssh access so that passwords are not required. If git
requires a password for a repository then you will be prompted to supply it in
the usual way.

The gitcatrc file
.................

The gitcatrc file contains the catalogue of repositories maintained by `git
cat`. This file will be stored in the directory ~/.dotfiles/config, if it
exists, and otherwise it defaults to `~/.gitcatrc`. This location of this file
can be changed from the command line using the `-c` command line option.

The `git cat` commands are only applied to those repositories that have been
"installed" using `git cat install`. Consequently, if the gitcatrc file is
itself in a git repository then different computers that use this file can
syncrhonise different repositories using `git cat`.


------------

**git cat add**

usage: git cat add [-h] [-d GIT_DIRECTORY] [-q]

Add current repository to the catalogue

optional arguments:
  -h, --help            show this help message and exit
  -d GIT_DIRECTORY, --directory GIT_DIRECTORY
                        Add repository from specified directory
  -q, --quiet           only print "important" messages

Add the current repository to the catalogue stored in the gitcatrc
file. An error is returned if any of the following hold:
- the current directory is already in the git cat catalogue
- the current directory is not contained in a git repository
- the current directory does not have a remote a git repository

*Example*:

.. code-block:: bash

    > git cat add  # add the current directory to the catalogue

------------

**git cat branch**

usage: git cat branch [-h] [-q] [repositories]

Print status of all branches in each repository

positional arguments:
  repositories  optionally filter repositories for status

optional arguments:
  -h, --help    show this help message and exit
  -q, --quiet   only print "important" messages

Run `git branch --verbose` in selected repositories in the
catalogue. This gives a summary of the status of the branches in the
repositories managed by git cat.

*Example*:

.. code-block:: bash

    > git cat branch Code
    Code/Prog1
      python3 6c2fcd5 Putting out the washing
    Code/Prog2
      master  2d2614e [ahead 1] Making some important changes
    Code/Prog3        already up to date
    Code/Prog4        already up to date
    Code/Prog5
      branch1 14fc541 Adding braid method to tableau
      * branch2       68480a4 git cat: updating   doc/README.rst
      master             862e2f4 Adding good stuff
    Code/Prog6            already up to date

------------

**git cat commit**

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

Commit all changes in the selected repositories in the catalogue. The
commit message will list the files that were changed. This command is
provided mainly for completeness and, instead, `git cat push` would
probably be used.

*Example*:

.. code-block:: bash

    > git cat commit

------------

**git cat diff**

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

*Example*:

.. code-block:: bash


    > git cat diff Code
    Code/Prog1   up to date
    Code/Prog2   up to date
    Code/GitCat  diff --git c/gitcat.py w/gitcat.py
    index b32a07f..c32a435 100644
    --- c/gitcat.py
    +++ w/gitcat.py
    @@ -29,16 +29,25 @@ *Examples*:

.. code-block:: bash

    -gitcatrc:
    +The gitcatrc file:

------------

**git cat fetch**

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

Run `git fetch -q --progress` on the installed git cat repositories.

*Example*:

.. code-block:: bash

    > git cat fetch
    Rep1  already up to date
    Rep2  already up to date
    Rep3  remote: Counting objects: 3, done.
      remote: Compressing objects:  33% (1/3)
      remote: Compressing objects:  66% (2/3)
      remote: Compressing objects: 100% (3/3)
      remote: Compressing objects: 100% (3/3), done.
      remote: Total 3 (delta 2), reused 0 (delta 0)

------------

**git cat install**

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

By default all repositories are installed, however, by specifying a
regular expression for the repositories you can install a subset of the
repositories managed by git cat.abs

*Examples*:

.. code-block:: bash


    > git cat install       # install all repositories managed by git cat
    > git cat install Code  # install all "Code" repositories managed by git cat

------------

**git cat ls**

usage: git cat ls [-h] [-q] [repositories]

List all repositories in the catalogue

positional arguments:
  repositories  optionally filter repositories for status

optional arguments:
  -h, --help    show this help message and exit
  -q, --quiet   only print "important" messages

List the repositories managed by git cat, together with the location of
their remote repository.

*Example*:

.. code-block:: bash

    > git cat ls
    Code/Prog1    = git@bitbucket.org:AndrewsBucket/prog1.git
    Code/Prog2    = git@bitbucket.org:AndrewsBucket/prog2.git
    Code/Prog3    = git@bitbucket.org:AndrewsBucket/prog3.git
    Code/Prog4    = git@bitbucket.org:AndrewsBucket/prog4.git
    Code/GitCat   = git@gitgithub.com:AndrewMathas/gitcat.git
    Notes/Life    = git@gitgithub.com:AndrewMathas/life.git
    Stuff         = git@some.random.rep.com:Me/stuffing.git

------------

**git cat pull**

usage: git cat pull [-h] [--all] [-d] [--ff-only] [--squash] [--stat] [-t]
                    [-s <STRATEGY>] [--recursive] [--theirs] [--ours] [-q]
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
  -s <STRATEGY>, --strategy <STRATEGY>
                        Use the specified merge strategy
  --recursive           Use recursive three-way merge
  --theirs              Resolve merge conflicts favouring remote repository
  --ours                Resolve merge conflicts favouring local repository
  -q, --quiet           only print "important" messages

Run through all repositories and update them if their directories
already exist on this computer. Unless the  `--quiet` option is used,
a message is printed to give the summarise the status of the
repository.

*Example*:

.. code-block:: bash

    > git cat pull
    Code/Prog1    already up to date
    Code/Prog2    already up to date
    Code/GitCat   already up to date
      remote: Counting objects: 8, done.
      remote: Total 8 (delta 6), reused 0 (delta 0)
    Notes/Life    already up to date

------------

**git cat push**

usage: git cat push [-h] [-d] [--all] [--prune] [--tags] [-q] [repositories]

Change all remote URLs to use ssh access

positional arguments:
  repositories   optionally filter repositories for status

optional arguments:
  -h, --help     show this help message and exit
  -d, --dry-run  Do everything except actually send the updates
  --all          Push all branches
  --prune        Remove remote branches that don't have a local counterpart
  --tags         Push all tags
  -q, --quiet    only print "important" messages

Run through all installed repositories and push them to their remote
repositories. Any uncommitted repository with local changes will be
committed and the commit message listing the files that have changed.
Unless the `-quiet` option is used, a summary of the status of
each repository is printed with each push.

*Example*:

.. code-block:: bash

    > git cat push
    Code/Prog1    pushed
      To bitbucket.org:AndrewsBucket/dotfiles.git
      refs/heads/master:refs/heads/master	e128dd9..904f96a
      Done
    Code/Prog2    up to date
    Code/Prog3    up to date
    Code/Prog4    up to date
    Code/GitCat   commit
      [master 442822d] git cat: updating   gitcat.py
      1 file changed, 44 insertions(+), 5 deletions(-)
      To bitbucket.org:AndrewsBucket/gitcat.git
      refs/heads/master:refs/heads/master	6ffeb9d..442822d
      Done
    Notes/Life    up to date

------------

**git cat remove**

usage: git cat remove [-h] [-e] [-d GIT_DIRECTORY] [-q]

Remove repository from the catalogue

optional arguments:
  -h, --help            show this help message and exit
  -e, --everything      Delete everything, including the directory
  -d GIT_DIRECTORY, --directory GIT_DIRECTORY
                        Remove repository from specified directory
  -q, --quiet           only print "important" messages

Remove the current repository to the catalogue stored in the gitcatrc
file. An error is returned if any of the following hold:
- the current directory is not in the git cat catalogue
- the current directory is not contained in a git repository

*Example*:

.. code-block:: bash

    git cat remove  # remove the current directory to the catalogue

------------

**git cat status**

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

Print a summary of the status of all of the repositories in the
catalogue. The name is slightly misleading as this command does not
just run `git status` on each repository and, instead, it queries the
remote repositories to determine whether each repository is ahead or
behind the remote repository.

*Example*:

.. code-block:: bash

    > git cat status
    Code/Prog1    up to date
    Code/Prog2    ahead 1
    Code/Prog3    = git@bitbucket.org:AndrewsBucket/prog3.git
    Code/Prog4    up to date= git@bitbucket.org:AndrewsBucket/prog4.git
    Code/GitCat   behind 1
    Notes/Life    up to date= gitgithub.com:AndrewMathas/life.git


Author
......

Andrew Mathas

`git cat` Version 1.0

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
.. _`git cat`: https://bitbucket.org/AndrewsBucket/gitcat/