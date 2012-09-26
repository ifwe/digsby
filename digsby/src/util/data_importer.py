from __future__ import with_statement
import sys
import path
import StringIO
import zipfile
import util
from contextlib import closing

def zipopen(fpath, dirs = None, zip = None):
    '''
    Returns a file-like object, in 'rb' mode, of the provided
    path object. if a zip file is encountered, the path lookup continues
    inside the zip file. Note: doesn't do so well with nested zip files.

    'dirs' is a variable used during this function's recursion.
    '''

    fpath = path.path(fpath)
    if dirs is None:
        dirs = fpath.splitall()

        if dirs[0] == '\\\\':
            uncstart = dirs[0]
            hostname = dirs[1]
            sharename = dirs[2]
            rest = dirs[3:]

            dirs = [uncstart + hostname + '\\' + sharename] + rest

    if not dirs:
        raise IOError('No such file or directory: %r' % fpath)

    if zip is None:
        # Normal file system operations
        nextdir = dirs.pop(0)

        if nextdir:
            curpath = fpath / nextdir
        else:
            curpath = fpath

        for ext in ('', '.zip', '.egg'):
            possible = curpath + ext

            if possible.isfile() or possible.isdir():
                if possible.isdir():
                    try:
                        return zipopen(possible, dirs = dirs, zip = None)
                    except IOError:
                        pass

                if not dirs:
                    # We got what we wanted!
                    return open(possible, 'rb')
                try:
                    zip = zipfile.ZipFile(possible)
                except zipfile.BadZipfile:
                    # OK so we found a non-directory, but we can't load it. raise an error
                    raise IOError('Could not open %r because %r is not a valid zip file' % (possible.joinpath(*dirs), curpath))
                else:
                    return zipopen(possible, dirs = dirs, zip = zip)
        else:
            raise IOError('No such file or directory: %r' % possible.joinpath(*dirs))
    else:
        # Need to pull things out of zip in order to continue
        bytes = None
        curpath = fpath
        while dirs and (bytes is None):
            nextdir = dirs.pop(0)
            curpath = curpath / nextdir
            for ext in ('', '.zip', '.egg'):
                possible = curpath + ext
                relpath = fpath.relpathto(curpath).replace('\\', '/') # zips use forward slashes
                try:
                    bytes = zip.read(relpath)
                except KeyError:
                    continue
                #return zipopen(fpath, dirs = dirs, zip = zip)

        if dirs and bytes:
            # hopefully, a zip inside the zip. otherwise, an IOError is in your future!
            with closing(StringIO.StringIO(bytes)) as fobj:
                try:
                    fobj = zipfile.ZipFile(fobj)
                except zipfile.BadZipfile:
                    raise IOError('Could not open %r because %r was found inside a zip '
                                  'file but the embedded file is not the endpoint nor '
                                  'another zip file.' % (curpath.join(*dirs), curpath))
                else:
                    return zipopen(fpath, dirs = dirs, zip = fobj)

        elif bytes:
            fobj = StringIO.StringIO(bytes)
            fobj.name = curpath
            return fobj
        else:
            raise IOError('No such file or directory %r' % curpath)


def ext_importer(*exts):
    exts = list(exts)
    def wrapped1(f):
        def wrapped2(dotted, loadpath = None):
            pth = find_dotted_resource(dotted, exts, loadpath = loadpath)
            if pth is None:
                raise ImportError('%r was not found' % dotted)

            return f(pth)
        return wrapped2
    return wrapped1

class YAMLModule(dict):
    def __init__(self, fname, d):
        self.__file__ = fname
        dict.__init__(self, d)

    def __getattr__(self, a):
        try:
            return dict.__getitem__(self, a)
        except KeyError:
            return dict.__getattribute__(self, a)

@ext_importer('.yaml')
def yaml_import(fname):
    return yaml_load(fname)

def yaml_load(fname):
    import syck as yaml
    with closing(zipopen(fname)) as f:
        modulefier = util.primitives.mapping.dictrecurse(lambda x: YAMLModule(fname, x))

        raw_values = yaml.load(f)
        if not isinstance(raw_values, dict):
            val = dict(__content__=raw_values)
        else:
            val = raw_values
        mod = modulefier(val)
        mod.__content__ = raw_values # in case it was a dictionary.
        return mod

def file_import(fname, loadpath = None):
    try:
        dotted_path, ext = fname.rsplit('.', 1)
        ext = '.' + ext
    except ValueError:
        dotted_path = fname
        ext = ''

    pth = find_dotted_resource(dotted_path, exts = [ext], loadpath = None, do_no_ext = False)

    if pth is None:
        raise ImportError("No file named %r was found" % fname)
    else:
        return zipopen(pth)


def find_dotted_resource(dotted, exts = [], loadpath = None, do_no_ext = True):
    '''
    Converts a.dotted.path to a/slashed/path and searches the folders in loadpath
    (or sys.path) for a resource that ends with an extension from exts (or no extension).

    returns path to the file.
    '''
    try:
        pth, name = dotted.rsplit('.', 1)
    except ValueError:
        # No dots
        pth = ''
        name = dotted


    if not ('/' in pth or '\\' in pth):
        pth = pth.replace('.', '/')

    if loadpath is None:
        loadpath = sys.path

    if do_no_ext:
        exts = list(exts) + ['']
    else:
        exts = list(exts)

    for pathdir in map(path.path, loadpath):
        for ext in exts:
            if (pathdir / pth).isdir():
                to_check = pathdir / pth / (name + ext)
                to_check = to_check.expand()
                if to_check.isfile():
                    return to_check
            full = pathdir / pth / name+ext
            if full.isfile():
                try:
                    with closing(zipopen(full)) as f:
                        return f.name
                except IOError:
                    continue

## Need to make this happen for each level
#                zipfilename = None
#                for ext in ('.egg', '.zip', ''):
#                    zipfilename = pathdir+ext
#                    if zipfilename.isfile():
#                        break
#                else:
#                    zipfilename = None
#
#                if zipfilename is None:
#                    continue
#
#                try:
#                    with closing(zipfile.ZipFile(pathdir)) as z:
#                        try:
#                            _info = z.getinfo(pth + '/' + (name + ext))
#                        except KeyError:
#                            # doesn't exist
#                            continue
#                        else:
#                            return pathdir / pth / (name + ext)
#                except (IOError, zipfile.BadZipfile):
#                    continue

if __name__ == '__main__':
    from pprint import pprint
    sys.path.append('c:\\workspace\\digsby\\')
    #sounds = yaml_import('res.sounds.default.sounds')
    #print sounds.__file__
    #pprint(sounds)
    #pprint(yaml_import('res.defaults'))

    sys.path.insert(0, 'c:\\')
    #pprint(yaml_import('test2.rawr'))
    #print repr(file_import('test2.rawr.txt', loadpath = ['c:\\']).read())

    #print zipopen('c:\\test.zip\\test2.zip\\test\\in_a_zip.yaml').read()

    netpath = path.path(r'\\mini\mike\test')
    sys.path.insert(0, netpath)
    print repr(yaml_import('test'))
