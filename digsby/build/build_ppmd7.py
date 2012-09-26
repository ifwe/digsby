#__LICENSE_GOES_HERE__
from buildutil import tardep, DEBUG, git, cd, run, DEPS_DIR, copy_different
from os.path import isdir
import os.path
thisdir = os.path.dirname(os.path.abspath(__file__))

lzma_sdk = tardep('http://mini/mirror/', 'lzma920', '.tar.bz2', 534077, indir='lzma920')

ppmd7_git_url = 'http://mini/git/pyppmd.git'
ppmd7_dir = 'pyppmd'

def build():
    with cd(thisdir):
        lzma_dir = lzma_sdk.get()

        if not isdir(ppmd7_dir):
            git.run(['clone', ppmd7_git_url])
            assert isdir(ppmd7_dir)

        with cd(ppmd7_dir):
            libname = 'ppmd7'
            config = 'Release' if not DEBUG else 'Debug'
            run(['vcbuild', 'libppmd7.sln', '%s|Win32' % config])
            for ext in ('.dll', '.pdb'):
                copy_different(os.path.join(config, libname + ext), DEPS_DIR)

if __name__ == '__main__':
    build()


