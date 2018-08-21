=======
git-cat
=======

Herding a catalogue of git repositories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Simultaneously push and pull to a catalogue of remote git repositories

    usage: git cat [-h] [-c CATALOGUE] [-p PREFIX] [-q] <command> [options] ...

A command line tool for synchronising a catalogue of git repositories. It uses
the catalogue of repositories, which is stored in the gitcatrc file, which is
either in the directory ~/.dotfiles/config or in the HOME directory.

Commands
--------

  add       Add repository to the catalogue
  remove    Remove repository from the catalogue

  commit    Commit all uncommitted repositories in the catalogue
  diff      Print a diff of the changes in each repository
  install   Install all repositories in the catalogue
  cat       List all of the repositories in the catalogue
  pull      Pull all repositories in the catalogue
  push      Push all repositories in the catalogue
  status    Print the status of each repository in the catalogue

  git       Run git commands on all repositories

Optional arguments:
  -h, --help            show this help message and exit
  -c CATALOGUE, --catalogue CATALOGUE
                        specify the catalogue of bitbucket repositories
  -q, --quiet           print messages
  -p PREFIX, --prefix PREFIX
                        Prefix directory name containing all repositories

Using git-cat
-------------

Git-cat makes it possible to manage multiple git repositories from the command
line. Git-cat makes it possible to push and pull from multiple git repositories
to and from remote servers, such as bitbucket_ and github_, automatically
committing changes when necessary. As the aim of git-cat is to manage multiple
repositories simultaneously, the output from git commands is tailored to be
succinct and to the point.

Git-cat does not support all git commands and nor does it support the full
functionality of those git commands that it does support. Instead, it provides
a crude way of synchronising multiple repositories with remote servers. The
git-cat philosophy is to "do no harm" so, when possible, it uses dry-runs
before changing any repository and only makes actual changes to the repository
if the dry-run succeeds.  Any problems encountered by git-cat are printed to
the terminal.


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
