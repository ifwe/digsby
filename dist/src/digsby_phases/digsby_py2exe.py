'''
Created on Apr 10, 2012

@author: "Michael Dougherty <mdougherty@tagged.com>"
'''
import os
import sys
import stat
import deploy
import distutils

import py2exe.build_exe as build_exe
import py2exe.mf as mf

build_exe.EXCLUDED_DLLS = \
    map(str.lower, build_exe.EXCLUDED_DLLS + \
        ('msvcp90d.dll', 'msvcr90d.dll',
         'usp10.dll', 'wldap32.dll',
         'WININET.dll', 'urlmon.dll',
         'Normaliz.dll', 'iertutil.dll',
         'API-MS-Win-Core-LocalRegistry-L1-1-0.dll'.lower(),
         ))

# We need to use a builder that doesnt put all the files into a single zip,
# and also doesn't choke on modules it can't find.


class mf_fixed(mf.ModuleFinder, object):
    def import_hook(self, name, caller = None, fromlist = None, level = -1):
        try:
            super(mf_fixed, self).import_hook(name, caller, fromlist, level)
        except ImportError:
            self.missing_modules.add(name)
            raise
        else:
            self.found_modules.add(name)


class py2exeSafe(build_exe.py2exe):
    boolean_options = build_exe.py2exe.boolean_options + ['retain_times']
    _module_finder = None

    def get_boot_script(self, boot_type):
        # return the filename of the script to use for com servers.
        thisfile = __file__
        pth = os.path.join(os.path.dirname(thisfile),
                           "boot_" + boot_type + ".py")
        if os.path.exists(pth):
            return pth

        return build_exe.py2exe.get_boot_script(self, boot_type)

    def initialize_options(self):
        build_exe.py2exe.initialize_options(self)
        self.retain_times = 0

    def make_lib_archive(self, zip_filename, base_dir, files=None, verbose=0, dry_run=0):
        if files is None:
            files = []
        # Don't really produce an archive, just copy the files.
        from distutils.dir_util import copy_tree
        copy_tree(base_dir, os.path.dirname(zip_filename),
                  verbose=verbose, dry_run=dry_run)
        return '.'

    def create_modulefinder(self):
        from modulefinder import ReplacePackage
        ReplacePackage('_xmlplus', 'xml')
        py2exeSafe._module_finder = mf_fixed(excludes = self.excludes)
        return py2exeSafe._module_finder

    def create_loader(self, item):
        ##
        ## Copied from build_exe.py2exe to add `if self.retain_times:` block
        ##

        # Hm, how to avoid needless recreation of this file?
        pathname = os.path.join(self.temp_dir, "%s.py" % item.__name__)
        if self.bundle_files > 2:  # don't bundle pyds and dlls
            # all dlls are copied into the same directory, so modify
            # names to include the package name to avoid name
            # conflicts and tuck it away for future reference
            fname = item.__name__ + os.path.splitext(item.__file__)[1]
            item.__pydfile__ = fname
        else:
            fname = os.path.basename(item.__file__)

        # and what about dry_run?
        if self.verbose:
            print "creating python loader for extension '%s' (%s -> %s)" % (item.__name__, item.__file__, fname)

        source = build_exe.LOADER % fname
        if not self.dry_run:
            open(pathname, "w").write(source)
            if self.retain_times:  # Restore the times.
                st = os.stat(item.__file__)
                os.utime(pathname, (st[stat.ST_ATIME], st[stat.ST_MTIME]))
        else:
            return None
        from modulefinder import Module
        return Module(item.__name__, pathname)


class Py2EXE(deploy.Freeze):
    strategy = 'py2exe'

    def pre(self):
        super(Py2EXE, self).pre()
        sys.setrecursionlimit(5000)
        # Needed for byte-compiling to succeed
        os.environ['PYTHONPATH'] = self.options.get('pythonpath')

        mf_fixed.missing_modules = set()
        mf_fixed.found_modules = set()

        self.distutils_options.update({'cmdclass': {'py2exe' : py2exeSafe}})

        with (self.source / 'srcrev.py').open('w') as f:
            f.write('REVISION = %r' % self.options.get('product_version'))

    def do(self):
        #import distutils.log
        #distutils.log.set_verbosity(self.options.get('distutils_verbosity', 2))
        distutils.core.setup(**self.distutils_options)

    def post(self):
        real_missing = (mf_fixed.missing_modules - mf_fixed.found_modules) - set(py2exeSafe._module_finder.modules.keys())
        if (real_missing):
            print ('missing %d modules' % len(real_missing))
            for x in sorted(real_missing):
                print '\t', x

        (self.source / 'srcrev.py').remove()
