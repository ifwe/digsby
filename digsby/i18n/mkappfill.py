#__LICENSE_GOES_HERE__
from __future__ import with_statement
import os.path
from path import path

EXTENSIONS = [
    '.py',
    '.cpp',
    '.c',
    '.h',
]

blacklist = [
    'ext/src/generated',
    'gui/pref/pg_dev.py', # don't include translated strings from dev pref pane
    'gui/bugreporter/bugreporterguiold.py',
    'gui/notificationview.py'
]
blacklist = [os.path.normpath(b) for b in blacklist]

def blacklisted(f):
    f = os.path.normpath(f)
    for b in blacklist:
        if b in f:
            return True

def generate_fil_file(filpath='app.fil', dirs=None, extensions=None):
    if dirs is None:
        dirs = ['../src']

    if extensions is None:
        extensions = EXTENSIONS
    assert not isinstance(extensions, str), 'extensions must be a seq of strings like [".cpp", ".h"]'

    with open(filpath, 'w') as appfile:
        for dir in dirs:
            for file in path(dir).walkfiles():
                f = file.normcase()
                for ext in extensions:
                    if f.endswith(os.path.normcase(ext)):
                        if not blacklisted(f):
                            appfile.write(file.relpath()+'\n')

def main():
    generate_fil_file()

if __name__ == '__main__':
    main()
