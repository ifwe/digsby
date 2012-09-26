#__LICENSE_GOES_HERE__
from buildutil import dpy, cd, tardep
import os.path

DIGSBY_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
assert os.path.isdir(DIGSBY_ROOT)

i18bin = tardep('http://mini/deps/i18n/win/', 'i18nbin', '.zip', 1037011)

def download_i18n_tools():
    with cd(DIGSBY_ROOT, 'build', 'msw'):
        d = i18bin.get()
        return os.path.abspath(d)

def make_po_files():
    toolsdir = download_i18n_tools()
    path = os.pathsep.join((toolsdir, os.environ.get('PATH', '')))

    with cd(DIGSBY_ROOT):
        dpy(['mki18n.py', '-m', '-v', '--domain=Digsby', DIGSBY_ROOT],
            addenv=dict(PATH=path))

if __name__ == '__main__':
    make_po_files()

