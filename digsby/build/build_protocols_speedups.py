#__LICENSE_GOES_HERE__
'''
builds the speedups module for PyProtocols (a dependency of Twitter)

should work on any platform distutils does
'''
from buildutil import dpy, DEPS_DIR, DEBUG


if DEBUG:
    cargs = "['/Zi', '/Od']"
else:
    cargs = "['/GL', '/Zi', '/GS-']"

protocols_setup = (
"from distutils.core import setup, Extension; "
"setup(name = '_speedups', ext_modules = "
"[Extension('_speedups', ['../lib/protocols/_speedups.c'], extra_compile_args = %s, extra_link_args = ['/DEBUG', '/OPT:REF', '/OPT:ICF'])])"
% cargs
)


def build_protocols_speedups():
    dpy(['-c', protocols_setup, 'clean'])
    dpy(['-c', protocols_setup,
         'build_ext'] + (['--debug'] if DEBUG else []) +
        ['install', '--install-lib', DEPS_DIR]
        )

if __name__ == '__main__':
    build_protocols_speedups()
