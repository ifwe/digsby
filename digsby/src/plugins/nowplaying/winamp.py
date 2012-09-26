'''

Retrieves information about the currently playing song from Winamp.

see http://www.winamp.com/development/sdk

'''

__all__ = ['WinampSongChecker']

import sys

from util.ffi import cimport, Struct
from ctypes.wintypes import DWORD
from ctypes import byref, create_string_buffer, create_unicode_buffer, WinError, \
                   c_int, c_char_p, addressof, c_char
from path import path
from traceback import print_exc
from nowplaying import SongChecker, register

import logging; log = logging.getLogger('nowplaying.winamp')

class WinampSongChecker(SongChecker):
    PROCESS_NAME = 'winamp.exe'
    app_name = 'Winamp'
    name_id = 'winamp'
    CLASS_NAME = u'Winamp v1.x'

    # TODO: Create get_instance and release methods to manage hwnd, hprocess so we only have to
    # requeset them when necessary

    important_keys = ('title', 'artist')

    def __init__(self):
        SongChecker.__init__(self)
        self.hwnd = None
        self.hProcess = None
        self.WinampData = None

        self.methods = [self._currentSongFromMetadata, self._currentSongFromPlaylistTitle, self._currentSongFromAppTitle]

    def running(self, processes=None):
        '''
        There are so many programs that masquerade as winamp, this is nearly impossible to discover.
        '''

        try:
            self.get_instance()
        except:
            self.release()
            return False

        return True

    def WASend(self, *a):
        return SendMessageW(self.hwnd, WM_WA_IPC, *a)

    def WAWrite(self, what, towhere):
        if type(what) is str:
            buf = create_string_buffer(what)
        else:
            buf = what

        outsize = c_int()

        success = WriteProcessMemory(self.hProcess, towhere._ptr, addressof(buf), len(buf), byref(outsize))
        if not success:
            raise WinError()

        if len(buf) != outsize.value:
            raise Exception("Didn't write enough data (wrote %d, should have written %d)", len(buf), outsize.value)

    def WARead(self, address, bufsize = 512):
        if not self.hProcess:
            return None

        if address in (0, 1, -1):
            raise AssertionError('invalid address')

        string = create_string_buffer(bufsize)

        if not ReadProcessMemory(self.hProcess, address, byref(string), bufsize, 0):
            raise WinError()

        return string.value

    def get_metadata(self, filename, metaname):
        if not self.hProcess:
            return None
        metaname = metaname.upper()

        WinampData = self.WinampData
        WAWrite = self.WAWrite
        WASend = self.WASend
        WARead = self.WARead

        efiRemote = fileNameRemote = fieldRemote = resultRemote = None
        efiRemote      = WinampData(extendedFileInfoStruct())
        fileNameRemote = WinampData(len(filename)+1)
        fieldRemote    = WinampData(len(metaname)+1)
        resultRemote   = WinampData(512)

        WAWrite(filename, fileNameRemote)
        WAWrite(metaname, fieldRemote)
        WAWrite(extendedFileInfoStruct(filename = fileNameRemote._ptr,
                                       metadata = fieldRemote._ptr,
                                       ret = resultRemote._ptr,
                                       retlen = 512),
                efiRemote)

        if not WASend(efiRemote._ptr, IPC.GET_EXTENDED_FILE_INFO):
            err = WinError()
            if err.winerror != 0:
                raise err

        result = WARead(resultRemote._ptr)
        return result

    def _currentSong(self):
        "Returns information about Winamp's currently playing song."

        if not self.hProcess:
            return None

        WinampData = self.WinampData
        WAWrite = self.WAWrite
        WASend = self.WASend
        WARead = self.WARead

        filename, position = self.get_current_filename()

        info = dict(status            = isplaying.get(WASend(1, IPC.ISPLAYING), 'stopped'),
                    length            = WASend(1, IPC.GETOUTPUTTIME),
                    #play_seconds      = WASend(0, IPC.GETOUTPUTTIME) / 1000,
                    playlist_position = position)

        extrainfo = {}

        # Store the errors and report them all at the end if we didnt find the info we want.
        # Because errors have traceback/frame info associated with them, we aggressively del
        # things around here ;-)
        errors = {}
        print_errors = False
        for method in self.methods[:]:
            try:
                moreinfo = method(filename, position)
                for k,v in moreinfo.iteritems():
                    if v: extrainfo[k] = v
            except Exception, e:
                errors[method] = e
                del e

            if all((key in extrainfo) for key in self.important_keys):
                break
        else:
            print_errors = True

        if (sys.DEV or print_errors) and errors:
            for method, error in errors.items():
                log.info('Exception calling %r: %r', method, error)
            del method, error
        del errors

        if not extrainfo:
            return None

        if filename:
            filepath = path(filename.decode(sys.getfilesystemencoding()))
            extrainfo.update(filepath = unicode(filepath),
                             filename = filepath.namebase)

        info.update(extrainfo)
        return info

    def _currentSongFromAppTitle(self, filename = None, position = None):
        if not self.hProcess:
            return {}

        try:
            title = fix_title(GetWindowText(self.hwnd)).decode('fuzzy utf8')
        except WindowsError, e:
            if e.winerror == 1400: # invalid window handle
                log.debug('invalid window handle for winamp. releasing process handles, etc.')
                self._release()
                return {}
            else:
                raise e

        # When no song is playing, Winamp just says "Winamp X.XX"
        if re.match('Winamp [0-9]\.[0-9]+', title): # nothing playing
            return {}
        else:
            try:
                artist, title = title.split(' - ', 1)
            except ValueError:
                return {}
            return dict(artist = artist, title = title)

    def _currentSongFromPlaylistTitle(self, filename = None, position = None):
        if not (filename and position):
            filename, position = self.get_current_filename()

        try:
            playlist_title = self.WARead(self.WASend(position, IPC.GETPLAYLISTTITLE)).decode('fuzzy utf8')
            if not playlist_title:
                raise Exception('Couldn\'t get playlist title')
        except Exception, e:
            return {}

        try:
            artist, title = playlist_title.split(' - ', 1)
        except ValueError:
            return {}

        return dict(artist = artist, title = title)

    def _currentSongFromMetadata(self, filename = None, position = None):
        if not self.hProcess:
            return {}

        if not (filename and position):
            filename, position = self.get_current_filename()
            if filename is None:
                return {} # no songs in playlist

        metas='title artist genre album comment length year'.split()
        metainfo = {}
        for meta in metas:
            try:
                metainfo[meta] = self.get_metadata(filename, meta).decode('fuzzy utf8') # Winamp gives us extended ascii but who knows what encoding it is.
            except Exception, e:
                if sys.DEV:
                    print_exc()
                return {}

        return metainfo


    def get_current_filename(self):
        WASend = self.WASend
        WARead = self.WARead

        filename = None

        position        = WASend(0, IPC.GETLISTPOS)
        playlist_length = WASend(0, IPC.GETLISTLENGTH)

        if playlist_length:
            filename = WARead(WASend(position, IPC.GETPLAYLISTFILE))

        return filename, position

    def get_instance(self):
        if self.hwnd and self.hProcess:
            return

        hwnd = FindWindowW(self.CLASS_NAME, None)
        if not hwnd:
            log.debug('couldn\'t get window handle for winamp')
            self.release()
            raise Exception("No instance found for %r", self)

        self.hwnd = hwnd

        # Get the process handle
        processId = DWORD()
        GetWindowThreadProcessId(hwnd, byref(processId))
        hProcess = OpenProcess(PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION, 0, processId)
        hProcess = hProcess or None

        if not hProcess:
            log.debug('couldn\'t get process handle for winamp')
            self.release()
        else:
            self.hProcess = hProcess
            self.WinampData = MakeIPCDatatype(hProcess)

    def release(self):
        if self.hProcess is not None:
            CloseHandle(self.hProcess)
            self.hwnd = None
            self.hProcess = None
            self.WinampData = None

register(WinampSongChecker)

import re
num_matcher = re.compile('^([0-9]+\. )')

def fix_title(s):
    # Remove the "- Winamp" part at the end.
    #
    idx = s.find(' - Winamp')
    if idx >= 0:
        s = s[:idx]

    # Remove leading numbers like "5. "
    match = num_matcher.match(s)
    if match: s = s[len(match.group()):]

    return s

gwt_buffer = create_unicode_buffer(256)
def GetWindowText(hwnd):
    if not GetWindowTextW(hwnd, byref(gwt_buffer), 256):
        raise WinError()

    return gwt_buffer.value


cimport(user32 = ['SendMessageW',
                  'FindWindowW',
                  'GetWindowTextW',
                  'GetWindowThreadProcessId'],
        kernel32 = ['ReadProcessMemory',
                    'WriteProcessMemory',
                    'VirtualAllocEx',
                    'VirtualFreeEx',
                    'OpenProcess',
                    'CloseHandle'])

def MakeIPCDatatype(hProcess):
    class IPCData(object):
        HPROCESS = hProcess
        def __init__(self, sz, datatype=None):

            if type(sz) is int:
                if datatype is None:
                    datatype = (c_char * sz)()
            else:
                datatype = sz
                sz = len(datatype)
            self._sz = sz
            self._ptr = VirtualAllocEx(self.HPROCESS, None, sz, MEM_COMMIT, PAGE_READWRITE)
            if not self._ptr:
                print >> sys.stderr, ('the following WindowsError occurred when calling'
                                      'VirtualAllocEx(%s, None, %s, MEM_COMMIT, PAGE_READWRITE)'
                                      % (self.HPROCESS, sz))
                raise WinError()


            self._value = type(datatype).from_address(self._ptr)

        def free(self):
            if self._ptr is not None:
                if not VirtualFreeEx(self.HPROCESS, self._ptr, 0, MEM_RELEASE):
                    raise WinError()
                self._ptr = None

        __del__ = free

    return IPCData


class extendedFileInfoStruct(Struct):
    _fields_ = [('filename', c_char_p),
                ('metadata', c_char_p),
                ('ret',      c_char_p),
                ('retlen',   c_int)]

# IPC communication constants from wa_ipc.h in the Winamp SDK
WM_WA_IPC          = 1024 # == WM_USER

PROCESS_ALL_ACCESS = 0
PROCESS_VM_OPERATION = 0x08
PROCESS_VM_READ    = 0x10
PROCESS_VM_WRITE   = 0x20
MEM_COMMIT         = 0x1000
MEM_DECOMMIT       = 0x4000
MEM_RELEASE        = 0x8000
PAGE_READWRITE     = 0x4

class IPC:
    GETVERSION = 0
    ISPLAYING  = 104
    GETOUTPUTTIME = 105
    GETLISTLENGTH = 124
    GETLISTPOS = 125
    GETINFO = 126
    GETPLAYLISTFILE = 211
    GETPLAYLISTTITLE = 212

    GET_EXTENDED_FILE_INFO = 290
    GET_EXTENDED_FILE_INFO_HOOKABLE = 296

isplaying = {0: 'stopped', 1: 'playing', 3: 'paused'}


if __name__ == '__main__':

    logging.basicConfig()
    from time import clock
    before = clock()
    checker = WinampSongChecker()
    checker.get_instance()
    print GetWindowText(checker.hwnd)
    #info = checker.currentSong()
    for i in range(1):
        print 'apptitle %r' % checker._currentSongFromAppTitle()
        print 'playlist %r' % checker._currentSongFromPlaylistTitle()
        print 'metadata %r' % checker._currentSongFromMetadata()
    #print info

    checker.release()
    duration = clock () - before

    print 'duration', duration
