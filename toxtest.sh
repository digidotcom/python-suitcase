#!/bin/bash
#
# Script that will try to test this codebase against as many
# python versions as is possible.  It does this using a combination
# of pyenv (for building various interpreters) and tox for
# testing using each of those interpreters.
#

pyversions=(2.7.7
            3.2.5
            3.3.5
            3.4.3
            pypy-2.3.1)

# parse options
for i in "$@"
do
    case $i in
        --fast)
            FAST=YES
            ;;
    esac
done

if [ ! FAST="YES" ]; then
    # first make sure that pyenv is installed
    if [ ! -s "$HOME/.pyenv/bin/pyenv" ]; then
        curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
    fi
fi

# Update pyenv (required for new python versions to be available)
(cd $HOME/.pyenv && git pull)

# add pyenv to our path and initialize (if this has not already been done)
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"

# install each python version that we want to test with
for pyversion in ${pyversions[*]};
do
    pyenv install -s ${pyversion}
done
pyenv rehash

# This is required
pyenv global ${pyversions[*]}

# Now, run the tests after sourcing venv for tox install/use
if [ ! FAST="YES" ]; then
    virtualenv -q .toxenv
fi
source .toxenv/bin/activate
if [ ! FAST="YES" ]; then
    pip install -q -r dev-requirements.txt
fi

if FAST="YES"; then
    tox
else
    # will ensure all depencies are pulled in
    tox --recreate
fi
