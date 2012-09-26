from __future__ import with_statement

import os, codecs
pathjoin = os.path.join
from threading import RLock
from time import time
from path import path
from logging import getLogger; log = getLogger('fileutil')

import Queue as Q
import traceback

if os.name == 'nt':
    import ctypes
    GetDiskFreeSpaceEx = ctypes.windll.kernel32.GetDiskFreeSpaceExW
    bytes_free = ctypes.c_ulonglong()
    def free_disk_space():
        if not GetDiskFreeSpaceEx(None, ctypes.byref(bytes_free), None, None):
            try:
                raise ctypes.WinError()
            except Exception:
                traceback.print_exc()
                return 0

        return bytes_free.value
else:
    def free_disk_space():
        log.warning('free_disk_space not implemented for this platform')
        return 0


class cd(object):
    '''
    chdirs to path, always restoring the cwd

    >>> with cd('mydir'):
    >>>     do_stuff()
    '''
    def __init__(self, *path):
        self.path = path

    def __enter__(self):
        self.original_cwd = os.getcwd()
        new_cwd = pathjoin(*self.path)
        os.chdir(new_cwd)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.original_cwd)

def tail(filename, maxbytes, encoding = None):
    'Return the last "maxbytes" bytes of filename or fileobject.'

    if maxbytes <= 0:
        raise ValueError('maxbytes must be more than 0')

    seekargs = (-maxbytes, os.SEEK_END)

    if hasattr(filename, 'read'):
        f = filename
        will_close = False
    else:
        filesize = os.stat(filename).st_size
        if encoding is not None:
            f = codecs.open(filename, 'rb', encoding)

        else:
            f = open(filename, 'rb')

        # change seekargs because codecs.open doesn't support seek from the end
        if maxbytes > filesize:
            seek = 0
        else:
            seek = filesize - maxbytes

        seekargs = (seek,)

        will_close = True

    f.seek(*seekargs)

    s = f.read()

    if will_close:
        f.close()

    return s

def streamcopy(fobjin, fobjouts, limit = None, chunk = 4096):
    # TODO: Support multiple input sources? i.e. read from in[0] until it is exhausted,
    #         then read from in[1], etc.
    '''
    Copy data from 'fobjin' (must have read method) to 'fobjouts' (which may
    be an object with a write method or a list of such objets). Up to 'limit'
    bytes are copied in chunks of size 'chunk'.

    Returns the number of bytes written.

    Does not open or close streams and does not handle exceptions.
    These are the responsibility of the caller.
    '''
    if hasattr(fobjouts, 'write'):
        fobjouts = [fobjouts]

    def writer(data):
        for fobjout in fobjouts:
            fobjout.write(data)

    return functioncopy(fobjin.read, writer, limit, chunk)

def functioncopy(reader, writer, limit=None, chunk=4096):
    '''
    functioncopy(reader, writer, limit=None, chunk=4096)
      callable: reader(sz) -> data
        this function will be called with a number of bytes to be read. it should return that much data (as a string).
        An empty return value signifies no more data.
      callable: writer(data) -> None
        this function will be called with the data. its return value is ignored.
      int: limit (optional)
        this is the maximum amount to be transferred. if left as the default (None), copy will continue until
        reader returns no more data.
      int: chunk (optional)
        this is the size to be read for each iteration through the loop. Default is 4096
    '''
    if not callable(reader) or not callable(writer):
        raise TypeError("Both 'reader' and 'writer' must be callable. Got (%r, %r) instead.", reader, writer)
    written = 0

    if limit is not None:
        sz_to_read = min(limit, chunk)
    else:
        limit = -1
        sz_to_read = chunk

    bytes = reader(sz_to_read)
    while bytes:
        writer(bytes)

        limit -= len(bytes)
        written += len(bytes)

        if limit > 0:
            sz_to_read = min(limit, chunk)
        elif limit == 0:
            break
        else:
            sz_to_read = chunk

        bytes = reader(sz_to_read)
    return written

CHUNKSIZE = 32 * 1024
def trim_file(fname, cap, newsize):
    fobjin = fobjout = None

    fname = path(fname)
    if fname.size > cap:
        try:
            fobjin = open(fname, 'rb')
            fobjout = open(fname+'.new', 'wb')

            fobjin.seek(-newsize, os.SEEK_END)
            streamcopy(fobjin, fobjout, CHUNKSIZE)
        finally:
            for f in (fobjin, fobjout):
                if f is not None:
                    f.close()

        os.remove(fname)
        os.rename(fobjout.name, fname)


class PausableStream(object):
    '''
    A stream that can be paused. if s.pause() is called, no data will be written
    to the underlying stream until s.unpause() is called. Calling unpause will also
    write out all data that was written while it was paused.
    '''
    def __init__(self, stream):
        self._lock = RLock()
        self.paused = False
        self.stream = stream
        self._queue = Q.Queue()
    def pause(self):
        self.paused = True

    def unpause(self):
        if self._lock.acquire():
            try:
                while True:
                    try:
                        self.stream.write(self._queue.get_nowait())
                    except Q.Empty:
                        break
            finally:
                self._lock.release()

            self.paused = False

    def write(self, data):
        if self.paused:
            self._queue.put(data)
        else:
            if self._lock.acquire(0):
                try:
                    self.stream.write(data)
                finally:
                    self._lock.release()
            else:
                self._queue.put(data)

        return len(data)

    def flush(self):
        if not self.paused:
            self.unpause() # make sure to dump the Q to the stream.
        return self.stream.flush()
    def close(self):
        return self.stream.close()
    def tell(self):
        return self.stream.tell()

class SwappableStream(PausableStream):
    '''
    Call start_swap, do any further cleanup of old s.stream or prep for the newstream
    and then call finish_swap with the new stream.
    '''
    def start_swap(self):
        self.pause()
        self.stream.flush()
        self.stream.close()

    def finish_swap(self, newstream):
        self.stream = newstream
        self.unpause()

class LimitedFileSize(SwappableStream):
    def __init__(self, fname, filesize_limit, resize, initmode='wb'):
        '''
        Construct with a filename, a size_limit for the file, and the size to resize it to when size_limit is reached.
        Data is truncated from the beginning of the file.
        '''
        fobj = open(fname, initmode)
        if resize > filesize_limit:
            raise ValueError('resize must be smaller than filesize_limit. (resize=%r, filesize_limit=%r)', resize, filesize_limit)
        SwappableStream.__init__(self, fobj)
        self._szlimit = filesize_limit
        self._fname = fname
        self._resize = resize
        self._known_size = None

    def write(self, data):
        SwappableStream.write(self, data)

        if self._known_size is None:
            self._known_size = os.path.getsize(self._fname)
        else:
            self._known_size += len(data)

        if self._known_size > self._szlimit:
            self.start_swap()
            try:
                trim_file(self._fname, self._szlimit, self._resize)
            finally:
                self.finish_swap(open(self._fname, 'ab'))

from ratelimited import RateLimiter
class StreamLimiter(RateLimiter):
    '''
    Will not write more than 'limit' bytes per second (using a sliding window of 'window' seconds).
    If data is being written too fast, only a "writing too fast" message is printed.
    '''
    def __init__(self, stream, limit=4096, window=5):
        self.stream = stream
        RateLimiter.__init__(self, self.stream.write, limit, window)
    def write(self, data):
        self.handle_data(data)
    def flush(self):
        return self.stream.flush()
    def close(self):
        return self.stream.close()
    def tell(self):
        return self.stream.tell()

    def too_fast(self, data):
        s = self.stream
        s.write('Writing too fast: %r\n' % self.bps)
        s.flush()

class DelayedStreamLimiter(StreamLimiter):
    '''
    same as stream limiter but continues writing for a length of time after going over the limit.
    '''
    DELAY = .25 # seconds
    def __init__(self, *a, **k):
        StreamLimiter.__init__(self, *a, **k)
        self._process_stop_time = 0
    def handle_data(self, data):
        should_write = None
        if not StreamLimiter.handle_data(self, data):
            now = time()
            if self._process_stop_time == 0:
                if (now - self._process_stop_time) < self.DELAY:
                    # Write it anyway!
                    should_write = True
                else:
                    # have been 'writing too fast' for more than DELAY seconds
                    # store the time for later calls of this method
                    self._process_stop_time = now
                    should_write = False
            else:
                # We've already stored the time in a previous iteration of this
                # method, see if it's been longer than DELAY since then.
                if (now - self._process_stop_time) < self.DELAY:
                    # it hasn't been that long yet
                    should_write = True
                else:
                    # it has been too long
                    should_write = False
        else:
            # The data was already written for us
            should_write = False

            # clear the stored time
            self._process_stop_time = 0

        if should_write:
            self.f_process(data)

        if should_write:
            # data was written by this method
            return True
        else:
            if self._process_stop_time == 0:
                # Data was written in superclass
                return True
            else:
                # Data was not written
                return False


class DisablingStream(object):
    '''
    An output stream that disables itself if there is an error in writing or flushing.
    After that, it can only be re-enabled with a call to s.enable()

    While disabled, all data written is lost.
    '''
    def __init__(self, target):
        self.target = target

        self.write = self.write_enabled
        self.flush = self.flush_enabled

    def write_enabled(self, s):
        try:    self.target.write(s)
        except: self.disable()

    def flush_enabled(self):
        try:    self.target.flush()
        except: self.disable()

    def disable(self):
        self.set_enabled(False)
    def enable(self):
        self.set_enabled(True)

    def disabled(self, data=None):
        '''
        sink hole for data.
        '''

    def set_enabled(self, val):
        if val:
            self.flush = self.flush_enabled
            self.write = self.write_enabled
        else:
            self.flush = self.write = self.disabled


if __name__ == '__main__':
    from primitives.bits import getrandbytes
    data = getrandbytes(100)
    half_len = len(data)/2

    from StringIO import StringIO
    in_ = StringIO(data)
    out = None

    def reset(i):
        i.seek(0)
        return StringIO()

    def check(i,o,l,w):
        '''
        in, out, limit, written
        '''
        return i.getvalue()[:l] == o.getvalue() and w == l

    # TODO: Tests for multiple 'out' streams.
    __test_stream_copy = '''\
>>> out = reset(in_); written = streamcopy(in_, out); check(in_, out, len(data), written)
True
>>> out = reset(in_); written = streamcopy(in_, out, chunk = len(data)); check(in_, out, len(data), written)
True
>>> out = reset(in_); written = streamcopy(in_, out, limit = half_len); check(in_, out, half_len, written)
True
>>> out = reset(in_); written = streamcopy(in_, out, limit = half_len, chunk = half_len+1); check(in_, out, half_len, written)
True
>>> out = reset(in_); written = streamcopy(in_, out, limit = half_len, chunk = half_len-1); check(in_, out, half_len, written)
True
'''
    # TODO: tests for actual files!
    __test_tail = '''\
>>> in_.seek(0); tail(in_, 5) == in_.getvalue()[-5:]
True
>>> in_.seek(0); tail(in_, 1000) == in_.getvalue()
True
'''

    __test__ = dict(
                    streamcopy = __test_stream_copy,
                    tail = __test_tail,
                    )

    import doctest
    doctest.testmod(verbose=True)

    import sys
    f = DelayedStreamLimiter(sys.stdout, limit = 8, window=1)
    import time as time_mod
    for i in range(20):
        f.write(str(i) + '\n')
        time_mod.sleep(.04 * i)
