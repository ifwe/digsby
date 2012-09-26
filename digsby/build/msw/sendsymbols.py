#__LICENSE_GOES_HERE__
'''
sendsymbols.py

  stores binaries and PDBs on the symbol server

  Without arguments, reads a list of binaries to send from binaries.txt.
  With arguments, sends the files specified on the commandline, like:

    > python sendsymbols.py mybinary.pyd myotherbinary.pyd ...

  If there is a PDB file adjacent to a DLL or PYD it will be sent as well.
'''

import sys; sys.path.append('..')
from buildutil import DEPS_DIR, DEBUG
import os.path

# where to find symstore.exe
dbugtools_paths = [
        r'c:\Program Files\Debugging Tools for Windows (x86)',
        r'c:\Program Files (x86)\Debugging Tools for Windows (x86)',
        r'd:\Program Files\Debugging Tools for Windows (x64)',
]

# Ensure we can find symstore.exe
for p in dbugtools_paths:
    if os.path.isdir(p):
        dbugtools_path = p
        break
else:
    print >> sys.stderr, "missing symstore.exe: Please download Debugging Tools for Windows."
    raise Exception("missing symstore.exe: Please download Debugging Tools for Windows.")

class SymStoreException(Exception):
    pass

symstore_exe   = dbugtools_path + r'\symstore.exe'

# where to store symbols
symbol_server = r'\\mini\symbols\digsby'

# stored as an identifier with each transaction
appname = 'Digsby'

# pass /compress to symstore.exe?
compress = False

# filesnames are checked for these extensions before being passed to symstore.exe
known_binary_extensions = frozenset(('.exe', '.pyd', '.dll', '.pdb'))


import os, sys
from hashlib import sha1
from subprocess import Popen
from os.path import isfile, splitext, normpath, join as pathjoin, dirname, \
    abspath, basename
from string import Template

def storesym(binary):
    '''
    Calls storesym.exe on binary and its corresponding PDB, which is assumed to
    be next to it. If the PDB is not found a warning is printed to the console.
    '''

    filename = binary

    filebase, ext = splitext(filename)
    if not ext.lower() in known_binary_extensions:
        fatal('not a valid binary extension: %r' % filename)

    if not isfile(filename):
        fatal('file does not exist: %r' % filename)

    _leaf_func(binary)

    if not binary.lower().endswith('.pdb'):
        pdb = filebase + '.pdb'
        if isfile(pdb):
            print 'Also sending %r' % pdb
            _leaf_func(pdb)
        elif MODE == 'sendsymbols':
            warn('PDB missing: %r' % pdb)

from shutil import copy2

def _storesym(filename):
    if isinstance(filename, tuple):
        # send the file as it's packaged Py2EXE name
        filename, distname = filename
        assert not isfile(distname)
        copy2(filename, distname)

        try:
            _runstoresym(distname)
        finally:
            os.remove(distname)
    else:
        _runstoresym(filename)

def _runstoresym(filename):
    args = [symstore_exe, 'add',
            '/f', filename,
            '/s', symbol_server]

    if compress:
        args.append('/compress')

    args.extend(['/t', appname])

    run(*args)

def _compare_to_installed(filename):
    install_lib = r'c:\Program Files\Digsby\Lib'

    installed_binary = pathjoin(install_lib, basename(filename))

    if not isfile(installed_binary):
        return

    installed_sha, workspace_sha = sha(installed_binary), sha(filename)

    okstr = ' OK ' if installed_sha == workspace_sha else ' X  '
    print okstr, installed_sha[:5], workspace_sha[:5], basename(filename)

MODE = 'compare' if '--compare' in sys.argv else 'sendsymbols'

if MODE == 'compare':
    VERB = 'Checking'
    _leaf_func = _compare_to_installed
elif MODE == 'sendsymbols':
    VERB = 'Sending'
    _leaf_func = _storesym
else:
    raise AssertionError(MODE)

def _send_symbols(files):
    total = len(files)
    for i, filename in enumerate(files):
        if MODE == 'sendsymbols':

            filebase, ext = splitext(filename)

            # PYDs have _d postfix in debug mode
            if DEBUG and ext == '.pyd':
                filename = filebase + '_d' + ext

            space = '  ' if i < 10 else ' '
            print '\n%s (%d/%d):%s%s' % (VERB, i + 1, total, space, filename)

        storesym(filename)

def run(*cmd):
    'Run a command, exiting if the return code is not 0.'

    process = Popen(cmd)
    stdout, stdin = process.communicate()

    # exit with non-zero return code
    if process.returncode:
        raise Exception(SymStoreException(process.returncode, stdout))

    return stdout

def sha(filename):
    return sha1(open(filename, 'rb').read()).hexdigest()

def fatal(msg):
    print >> sys.stderr, msg
    sys.exit(1)

def warn(msg):
    print >> sys.stderr, msg

def send_default_symbols():
    # a list of all binaries we want to store is in binaries.txt

    # variables which appear in binaries.txt, like ${DPYTHON}
    DPYTHON_DIR = dirname(abspath(sys.executable))
    binaries_vars = dict(DPYTHON = DPYTHON_DIR,
                         PLATLIB = DEPS_DIR,
                         DEBUG = 'd' if DEBUG else '',
                         _DEBUG = '_d' if DEBUG else '',
                         WX_POSTFIX = 'ud' if DEBUG else 'uh')

    def template(s):
        return Template(s).safe_substitute(binaries_vars)

    working_dir = os.getcwd()
    digsby_dir = normpath(pathjoin(dirname(abspath(__file__)), '../..'))

    try:
        os.chdir(digsby_dir)

        files = []
        for line in open('build/msw/binaries.txt'):
            line = template(line).strip()

            if line and not line.startswith('#'):
                files.append(line)

        _send_symbols(files)
    finally:
        os.chdir(working_dir)

def main():
    # if files to send were specified on the command line, send them
    cmdline_files = sys.argv[1:]
    if cmdline_files:
        return _send_symbols(cmdline_files)

    # otherwise get from binaries.txt
    # change to the correct directory
    send_default_symbols()


if __name__ == '__main__':
    main()
