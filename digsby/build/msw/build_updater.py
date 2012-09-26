#__LICENSE_GOES_HERE__
'''
builds Digsby's windows autoupdater, and places resulting
binaries in digsby/ext/msw
'''

from __future__ import with_statement
import sys
sys.path.append('..') # for buildutil
sys.path.append('../../lib') # for path
from buildutil import run, cd
from path import path
from buildutil.signing import Authenticode

#
# configuration
#

# location of digsby source
DIGSBY_DIR = path('../../').abspath()

# location of updater project files
UPDATER_PROJECT_DIR = DIGSBY_DIR / 'lib/AutoUpdate/src/Digsby Update/msvc2008'
assert UPDATER_PROJECT_DIR.isdir(), 'could not find %s' % UPDATER_PROJECT_DIR
UPDATER_SOLUTION = 'Digsby Update MSVC2008.sln'

# exes and pdbs end up here
BINARIES_DEST_DIR = DIGSBY_DIR / 'ext/msw'

# check that DIGSBY_DIR is defined correctly
assert (DIGSBY_DIR / 'res').isdir() and \
       (DIGSBY_DIR / 'src').isdir() and \
       (DIGSBY_DIR / 'Digsby.py').isfile(), "invalid Digsby dir"

# check that the solution files are where we said they are
UPDATER_PATH = (UPDATER_PROJECT_DIR / UPDATER_SOLUTION).abspath()
assert UPDATER_PATH.isfile(), 'could not find solution %s' % UPDATER_PATH

artifacts = ['Digsby PreUpdater.exe', 'Digsby PreUpdater.pdb',
             'Digsby Updater.exe', 'Digsby Updater.pdb']

def update():
    'Updates digsby to trunk'

    with cd(DIGSBY_DIR):
        run(['svn', 'update'])

def build():
    # output the version of mt.exe--should be > 6
    # run('mt /', checkret = False)

    'Builds and deploys executables and debugging symbol files.'
    with cd(UPDATER_PROJECT_DIR):
        # remove the old Release directory
        run(['cmd', '/c', 'rmdir', '/s', '/q', 'Release'], checkret = False)

        # invoke MSVC2008
        print run(['devenv', '/build', 'release', UPDATER_SOLUTION], checkret = False)

        bindir = UPDATER_PROJECT_DIR / 'Release'
        if not (bindir / 'Digsby PreUpdater.exe').isfile():
            raise Exception('Visual Studio did not build the executables')

def deploy():
    with cd(UPDATER_PROJECT_DIR / 'Release'):
        dest = BINARIES_DEST_DIR.abspath()

        # deploy EXEs and PDBs to BINARIES_DEST_DIR
        for a in artifacts:
            p = path(a)
            print 'copying %s to %s' %  (p, dest)

            destfile = dest / p.name
            if destfile.isfile():
                print 'removing old %r' % destfile
                destfile.remove()
                assert not destfile.isfile()

            p.copy2(dest)
            destfile = dest / p.name
            assert destfile.isfile()

            # sign all executables
            if a.lower().endswith('.exe'):
                Authenticode(destfile)

        return dest

def commit():
    print '\nEnter a commit message, or press enter to skip:',
    message = raw_input()

    if message:
        with cd(BINARIES_DEST_DIR):
            run(['svn', 'commit'] + artifacts + ['-m', message])

def all():
    update()
    build()
    dest = deploy()

    print '\nSuccess!'
    print '\nNew binaries are in %s' % dest

    commit()

if __name__ == '__main__':
    all()
