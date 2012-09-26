from __future__ import with_statement
import shutil
import sys
import sipconfig

sys.path.append('../../../lib')
from path import path

def different(file1, file2, start = 0):
    if not file1.isfile() or not file2.isfile():
        return True

    if file1.size != file2.size or file1.bytes() != file2.bytes():
        return True


def manage_cache(gendir, show_diffs = True):
    """
    This function keeps a cache of all sip-generated *.cpp and *.h files
    and restores the stats of the newly generated set whenever the content
    is unchanged
    """
    sipconfig.inform("Managing the module cache: %s" % gendir)

    gendir = path(gendir)
    cache = gendir / 'cache'
    if not cache.isdir():
        cache.makedirs()

    if 'clean' in sys.argv:
        cache.rmtree()

    changed_count = 0
    for newfile in gendir.files('*.cpp') + gendir.files('*.h'):
        oldfile = cache / newfile.name
        if different(newfile, oldfile):
            changed_count += 1

            if oldfile.isfile():
                assert newfile.mtime > oldfile.mtime


            shutil.copy2(newfile, oldfile) # src, dest
            a, b = newfile.stat().st_mtime, oldfile.stat().st_mtime
            #assert a == b, "copy2 failed: mtimes are different! (%s and %s)" % (a, b)

            sipconfig.inform("--> changed: %s" % newfile.name)
        else:
            #sipconfig.inform("--> same:    %s" % newfile.name)
            shutil.copystat(oldfile, newfile)

    sipconfig.inform('%d file%s changed.' %
                     (changed_count, 's' if changed_count != 1 else ''))

    sys.stdout.flush()
