#__LICENSE_GOES_HERE__
from __future__ import with_statement

import os
import sys
sys.path.append('..') if '..' not in sys.path else None

from buildutil import run, fatal, inform, DEBUG_POSTFIX
from os.path import abspath, isdir, split as pathsplit, join as pathjoin

def check_msvc():
    'Ensures that Microsoft Visual Studio 2008 paths are setup correctly.'

    try:
        devenvdir = os.environ['DevEnvDir']
    except KeyError:
        fatal('DevEnvDir environment variable not set -- did you start a Visual Studio 2008 Command Prompt?')

    if '9.0' not in devenvdir:
        fatal('error: not visual studio 2008')

    inform('Microsoft Visual Studio 2008 check: OK')

def main():
    check_msvc()

if __name__ == '__main__':
    main()
