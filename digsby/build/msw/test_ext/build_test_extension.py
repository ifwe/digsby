'''

builds a small python test extension

'''

from __future__ import with_statement

import sys
import os

from shutil import rmtree
from os.path import exists
from traceback import print_exc

def clean():
    'Cleans results of previous builds.'

    if not exists('./spam.c'):
        raise Exception('wrong working directory: expected to be run from digsby\build\msw\test_ext')

    if exists('build'): rmtree('build')
    if exists('spam.pyd'): os.remove('spam.pyd')
    if exists('spam.pyd.manifest'): os.remove('spam.pyd.manifest')

def build():
    'Builds a small test Python extension.'

    from distutils.core import setup, Extension
    setup(name = 'spam',
          version='1.0',
          ext_modules=[Extension('spam', ['spam.c'])])

def run():
    'Tests the functionality of the extension.'

    import spam

    # spam should have a "system" function...try it out
    if spam.system('echo test') != 0 or spam.system('this_command_should_cause_an_error') != 1:
        raise AssertionError('test module did not function correctly')

    # unload
    del sys.modules['spam']

    print
    print 'Success!'
    print

def main():
    print 'Python executable is', sys.executable

    try:
        clean()
        build()
        run()
    except Exception:
        # return 1 on any kind of error
        print_exc()
        return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())
