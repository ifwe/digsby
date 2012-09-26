from __future__ import with_statement
from contextlib import contextmanager
import logging
import os
import time

log = logging.getLogger('util.primitives.files')

__all__ = [
           'filecontents',
           'atomic_write',
           'replace_file',
           ]

def filecontents(filename, mode = 'rb'):
    'Returns the contents of a file.'
    with open(filename, mode) as f: return f.read()

@contextmanager
def atomic_write(filename, mode = 'w'):
    '''
    Returns a file object opened with the given mode. After the with statement,
    data written to the file object will be written to <filename> atomically.
    '''
    path, filepart = os.path.split(filename)
    tempfile = os.path.join(path, '%s.tmp' % filepart)

    f = open(tempfile, mode)

    # yield the file object to the caller
    try:
        yield f
    except Exception:
        f.close()
        os.remove(tempfile)
        raise
    finally:
        f.close()

    assert os.path.isfile(tempfile)

    if os.path.isfile(filename):
        # If the file already exists, we need to replace it atomically.
        replace_file(filename, tempfile) # atomic on win32
    else:
        # Otherwise, just rename the temp file to the actual file.
        os.rename(tempfile, filename)

import ctypes
if hasattr(ctypes, 'windll'):
    ReplaceFileW = ctypes.windll.kernel32.ReplaceFileW

    def _make_filename_unicode(f):
        if isinstance(f, str):
            f = f.decode('filesys')
        elif not isinstance(f, unicode):
            raise TypeError

        return f

    # implement with atomic win32 function ReplaceFile
    def replace_file(filename, replacement):
        if not ReplaceFileW(_make_filename_unicode(filename),
                            _make_filename_unicode(replacement),
                            None, 0, 0, 0):
            raise ctypes.WinError()
else:
    # implement with os.rename
    def replace_file(filename, replacement):
        backup = filename + '.backup.' + str(time.time())
        os.rename(filename, backup)

        try:
            os.rename(replacement, filename)
        except Exception:
            os.rename(backup, filename)
            raise
