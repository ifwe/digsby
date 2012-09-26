#__LICENSE_GOES_HERE__
import os
import os.path
import buildutil

GIT_BIN = ['git']

## look up msys-git installation in %ProgramFiles% (%ProgramFiles(x86)% in case of 64bit python)
if os.name == 'nt':
    progfiles = os.environ.get('ProgramFiles(x86)', os.environ.get('ProgramFiles', None))
    if progfiles is not None:
        git_bin = buildutil.which('git', os.path.join(progfiles, 'Git', 'cmd', 'git.cmd'))
        GIT_BIN = [git_bin]
        if git_bin.lower().endswith('.cmd'):
            cmd = buildutil.which('cmd', buildutil.which('command'))
            if cmd is not None:
                GIT_BIN[:0] = [cmd, '/c']

def run(cmd):
    buildutil.run(GIT_BIN + cmd)
