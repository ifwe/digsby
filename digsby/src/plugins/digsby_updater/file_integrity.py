'''
Tools for determining the integrity of a file and the app.

The application is considered intact when all files that are expected are found, and no 'bad files' are detected.

Application integrity check in dev mode is achieved with svn status. Modified or deleted files are considered not
intact, and new files are considered 'bad'. svn:externals are ignored for simplicity.

Application integrity check in release mode (or dev mode with --force-update) is achieved by scanning the directory
and checking the integrity of each file.

If there are any files that are not intact or if there are any bad files (see below), the application is considered not
intact. This will trigger an update.

File integrity is determined by comparing file metadata from a manifest file to a file on disk.
A missing file is not intact.
A file that is not a 'regular' file (such as a symlink, a directory matching the expected file name, etc) is not intact.
A file with a different size from the metadata is not intact.
A file with a different hash (MD5) is not intact.

Bad files are files that are not in the manifest and and whose file extension is in the 'bad extensions' list, which is
currently: ('.py', '.pyo', '.pyc', '.dll', '.pyd', '.pth', '.so', '.dylib', '.exe', '.manifest', '.yaml')
There are also platform specific 'bad files' which are determined from platform_cleanup function in the the appropriate
{win|mac}helpers.py module.

Integrity checking can be perfomed as follows:
>>> pic = ProgramIntegrityChecker(
...     path_to_application_root,
...     path_to_temp_dir,
...     manifest_path, # required only if manifest_data is None
...     manifest_data, # required only if manifest_path is None
...     whitelist,     # optional, sequence of more allowed files
... )
>>> pic.start(success = lambda program_integrity_checker: None)
Also supported is a synchronous check, which is used when collecting data for bug reports:
>>> pic.synchronous_check() # pic.get_update_paths() + pic.get_delete_paths() will contain all files when this returns

Note that only success is called, when all files have been checked. The integrity checker itself is returned. It should
be inspected to determine the results of the scan. Use the get_update_paths and get_delete_paths methods. Another useful
property is expected_download_size.

The following hooks are also triggered:
 - digsby.updater.file_check_start(checker)
    When the first file is about to be processed
 - digsby.updater.file_checked(file_description)
    When any file is about to be processed
 - digsby.updater.file_check_complete(checker)
    When all files have been checked

ProgramIntegrityChecker also supports a 'fastmode' property. By default, the file checking happens in order, with a
delay between each file so as to avoid using as much of the system resources as possible. Setting fastmode to True will
disable this delay. It can be disabled by setting the property back to False.

NOTE: synchronous_check functions by setting fastmode to True before starting the check. If another thread sets fastmode
to False while the synchronous check is executing, then the synchronous check will return prematurely! Also, since
synchronous_check is performed without a callback, you will not receive notification when the check *actually* completes
(unless your code has registered for the digsby.updater.file_check_complete hook).

### Manifest (metadata) generationg
Generating a manifiest is easy:
>>> manifest_data = generate_manifest(directory, hashes=('md5',), ignore=())

hashes is a tuple that should contain keys that exist in the HashLib dictionary.
ignore can be a list of prefixes that should be ignored - this was once used to avoid including MessageStyles in the
manifest.

The data returned is a string with XML content. This is traditionally saved to a file named 'manifest'.
'''
import sys
import os
import stat
import hashlib
import traceback
import logging

log = logging.getLogger("d_updater.integrity")

import hooks
import path
import config
import util
import util.callbacks as callbacks

import lxml.etree as etree
import lxml.objectify as objectify
import lxml.builder as B

if config.platform == 'win':
    import winhelpers as helpers
elif config.platform == 'mac':
    import machelpers as helpers

needs_contents = dict (md5=True,
                       sha1=True,
                       adler32=True,
                       crc32=True,
                       mtime=False,
                       fsize=False)

def GetUserTempDir():
    import stdpaths

    if getattr(sys, 'is_portable', False):
        base_temp = stdpaths.temp / 'digsby'
    else:
        base_temp = stdpaths.userlocaldata

    pth = path.path(base_temp) / 'temp'
    if not pth.isdir():
        os.makedirs(pth)
    return pth

class MTime(object):
    def __init__(self, filename=None):

        self.__val = 0

        self.filename = filename

        if self.filename is not None:
            self.fromfilename(self.filename)

    def update(self, bytes):
        pass

    def digest(self, final=None):
        import struct
        return struct.pack('!I', self.__val)

    def hexdigest(self, final=None):
        return util.to_hex(self.digest(final),'').lstrip('0')

    def fromfilename(self, fname):
        self.filename = fname
        self.__val = int(path.path(self.filename).mtime)

class FSize(object):
    def __init__(self, filename=None):
        self.__val = -1
        self.filename = filename

        if self.filename is not None:
            self.fromfilename(self.filename)

    def update(self, bytes):
        pass

    def digest(self, final=None):
        import struct
        return struct.pack('!Q', self.__val)

    def hexdigest(self, final=None):
        return util.to_hex(self.digest(final), '').lstrip('0')

    def fromfilename(self, fname):
        self.filename = fname
        self.__val = int(path.path(self.filename).size)


HashLib = util.Storage(md5=hashlib.md5,
                       sha1=hashlib.sha1,
                       mtime=MTime,
                       fsize=FSize,
                       )

@util.memoize
def _hashfile(pth, algs, mtime):
    hs = list(HashLib.get(alg)() for alg in algs)

    if any(needs_contents[x] for x in algs):
        with pth.open('rb') as f:
            bytes = f.read(4096)
            while bytes:
                for h in hs:
                    h.update(bytes)
                bytes = f.read(4096)

    for h in hs:
        if hasattr(h, 'fromfilename'):
            h.fromfilename(pth)

    return [h.hexdigest() for h in hs]

def hashfile(pth, algs):
    return _hashfile(pth, algs, os.path.getmtime(pth))

class FileMeta(object):
    def __init__(self, pth, size=-1, hashes=None):

        if hashes is None:
            hashes = {}

        self.size = size
        self.hashes = dict(hashes)
        self.path = path.path(pth)

    @classmethod
    def from_xml(cls, el):
        pth = unicode(el.path)
        size = int(getattr(el, 'size', None) or -1)
        hashes = {}
        for hash in el.hash.getchildren():
            hashes[hash.tag] = unicode(hash)

        return cls(pth, size, hashes)

    def to_tag(self):
        return B.E.file(
                        B.E.path(unicode(self.path)),
                        *(([B.E.size(str(self.size))] if self.size >= 0 else []) +
                          [B.E.hash(B.E(hash, hval))
                           for (hash, hval) in self.hashes.items()]
                          )
                        )

    def match_local(self, fname):
        try:
            p = path.path(fname)
            try:
                st = p.stat()
            except Exception:
                return False

            if not stat.S_ISREG(st.st_mode):
                # Is it a regular file?
                return False

            if self.size >= 0 and st.st_size != self.size:
                # We have a size but the on-disk size doesn't match it
                return False

            hashnames = tuple(self.hashes.keys())
            l_hashes = dict(zip(hashnames, hashfile(p, hashnames)))
            for alg in self.hashes:
                if l_hashes[alg] != self.hashes[alg]:
                    return False
            else:
                return True

        except Exception, e:
            traceback.print_exc()
            return False

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__,
                            ' '.join('%s=%r' % i for i in vars(self).items()))

def generate_manifest(root, hashes=('md5',), ignore=()):
    root = path.path(root)
    hashes = tuple(hashes)

    file_tags = []
    for file in root.walkfiles():
        if any(file.startswith(d) for d in ignore):
            continue
        file = path.path(file)
        short = root.relpathto(file)
        f = FileMeta(short, file.size, (zip(hashes, hashfile(file, hashes))))
        file_tags.append(f.to_tag())

    manifest = B.E('manifest', *file_tags)

    return etree.tostring(manifest)

def dev_integrity_check(dir):
    import subprocess
    process = subprocess.Popen(["svn", "status", "--ignore-externals", dir],
                               stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stdout, stderr = process.communicate()

    updated_files = []
    deleted_files = []

    for line in stdout.splitlines():
        if line == '': break
        flags, fname = line[:7], line[8:]
        if flags[0] != 'X':
            if flags[0] in ("D!"):
                deleted_files.append(fname)
            else:
                updated_files.append(fname)

    return deleted_files, updated_files

class ProgramIntegrityChecker(object):
    '''
    Uses manifest data to determine what files need to be updated and deleted.
    '''

    whitelist = set(['uninstall.exe'])
    '''Files that are not in the manifest but are considered allowed anyway'''

    def __init__(self, local_dir = None, temp_dir = None, manifest_path = None, manifest_data = None,
                 whitelist = None):

        self.cancelling = False
        self.fast_mode = False
        self.quiet_mode = False
        self.unchecked_files = None
        self.delete_files = []
        self.update_files = []
        self.good_files = []

        if local_dir is None:
            local_dir = util.program_dir()
        if manifest_path is None:
            manifest_path =  local_dir / 'manifest'
        if manifest_data is None and manifest_path.isfile():
            manifest_data = manifest_path.bytes()

        self.manifest_path = manifest_path
        self.temp_dir = temp_dir or path.path(GetUserTempDir())
        self.local_dir = local_dir

        self.got_manifest_data(manifest_data)

        if whitelist is not None:
            self.whitelist = set(whitelist)

        known_files = set((self.local_dir/file.path).abspath() for file in self.unchecked_files)
        known_files.update((self.local_dir / file).abspath() for file in self.whitelist)
        self.delete_files = Cleanup(self.local_dir, known_files)
        self.callback = None

    @callbacks.callsback
    def start(self, callback = None):
        self.callback = callback
        hooks.notify('digsby.updater.file_check_start', self)
        self.next_file()

    def synchronous_check(self):
        self.fast_mode = True
        self.quiet_mode = True
        self.start()

    def cancel(self):
        self.cancelling = True

    def got_manifest_data(self, mdata):
        if mdata is None:
            self.unchecked_files = []
            return

        self.unchecked_files = map(FileMeta.from_xml, objectify.fromstring(mdata).file)

        self.write_manifest_data(mdata)

    def write_manifest_data(self, data):
        with open(self.temp_dir/'manifest', 'wb') as f:
            f.write(data)

    def _check_file(self):
        file = self.unchecked_files.pop()
        if file.match_local(self.local_dir / file.path):
            if not self.quiet_mode:
                log.debug("is latest: %r", file.path)
            self.good_files.append(file)
        elif file.path in self.whitelist:
            if not self.quiet_mode:
                log.debug("is whitelisted: %r", file.path)
            self.good_files.append(file)
        else:
            log.debug("is changed: %r", file.path)
            self.update_files.append(file)

        hooks.notify("digsby.updater.file_checked", file)

    def next_file(self):
        if self.cancelling:
            return

        if sys.DEV and not sys.opts.force_update:
            self.unchecked_files = []
            self.delete_files, self.update_files = dev_integrity_check(self.local_dir)
            self.files_processed()
            return

        if self.unchecked_files:
            if self.fast_mode:
                while self.fast_mode and self.unchecked_files and not self.cancelling:
                    self._check_file()
            else:
                self._check_file()

            import common
            interval = common.pref('digsby.updater.file_integrity_interval', type = int, default = 0.01)
            if interval == 0:
                interval = 0.01

            t = util.Timer(interval, self.next_file)
            t._verbose = False
            t.start()
        else:
            self.files_processed()

    def files_processed(self):
        hooks.notify('digsby.updater.file_check_complete', self)
        cb, self.callback = self.callback, None
        if cb is not None:
            cb.success(self)

    @property
    def expected_download_size(self):
        return sum(f.size for f in self.update_files if f.size > 0)

    def get_update_paths(self):
        return [getattr(x, 'path', x) for x in self.update_files]

    def get_delete_paths(self):
        return list(self.delete_files)

def Cleanup(local_root, known_files):
    if not getattr(sys, 'frozen', False):
        return []

    to_delete = set()

    local_root = path.path(local_root)

    # now find out which files shouldn't be there

    badexts = ('.py', '.pyo', '.pyc', '.dll', '.pyd', '.pth', '.so', '.dylib', '.exe', '.manifest', '.yaml')

    for file in local_root.walk():
        file = file.abspath()

        if file.isdir():
            continue

        if (file not in known_files) and any(file.endswith(ext) for ext in badexts):
            if file.endswith('.yaml') and \
               (file.parent == local_root or                        # update.yaml, tag.yaml, branch.yaml, etc.
                'res' in local_root.relpathto(file).splitall()):    # skin.yaml, sounds.yaml, etc

                continue

            to_delete.add(file)

    more_bad_files = helpers.platform_cleanup()
    to_delete.update(more_bad_files)

    return sorted(to_delete, reverse=True)

