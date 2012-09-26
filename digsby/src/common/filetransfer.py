'''
Logic for file transfers.
'''
from __future__ import with_statement, division

import os.path
from urllib2 import urlopen, URLError
import tempfile

from common import pref, profile
from path import path
import util
from util import autoassign, FileChunker, default_timer, threaded, Storage
from util.observe import Observable, notifyprop
from traceback import print_exc

from logging import getLogger
log = getLogger('filetransfer'); info = log.info; error = log.error

__metaclass__ = type

def fire(*a, **k):
    from common.notifications import fire
    return fire(*a, **k)

class FileTransferStates:
    CONNECTING           = 'Connecting'
    WAITING_FOR_YOU      = 'Waiting For You to Accept'
    WAITING_FOR_BUDDY    = 'Waiting For Buddy to Accept'
    CANCELLED_BY_YOU     = 'Cancelled By You'
    CANCELLED_BY_BUDDY   = 'Cancelled By Buddy'
    CONN_FAIL            = 'Could Not Connect'
    TRANSFERRING         = 'Transferring'
    CONN_FAIL_XFER         = 'Connection Failed During Transfer'
    PAUSED               = 'Paused'
    FINISHED             = 'Transfer Finished'
    PROXY_XFER_FILESIZE_ERROR = 'File size too big for proxy transfer'
    BUDDY_GONE           = 'Buddy has signed off'

    ErrorStates          = set((
                            CONN_FAIL,
                            CONN_FAIL_XFER,
                            BUDDY_GONE,
                            PROXY_XFER_FILESIZE_ERROR,
                            CANCELLED_BY_BUDDY,
                           ))
    FailStates           = ErrorStates | set((
                            CANCELLED_BY_YOU,
                           ))
    CompleteStates       = set((
                            FINISHED,
                           ))
    TransferringStates   = set((
                            TRANSFERRING,
                            PAUSED,
                           ))
    StartingStates       = set((
                            WAITING_FOR_YOU,
                            WAITING_FOR_BUDDY,
                            CONNECTING,
                           ))

class FileTransfer(Observable):
    DATA_POINTS = 500
    TIME_THRESHOLD = 30
    ATROPHY_TIME = 3

    states = FileTransferStates
    state  = notifyprop('state')

    _xfer_display_strings = {
        # transfer state       # xfer, "direction" string
        states.TRANSFERRING:       lambda x: _('{completed} of {size} ({speed}/sec) -- {time} remain').format(completed=util.nicebytecount(x.completed), size=util.nicebytecount(x.size), speed=util.nicebytecount(x.bytes_per_sec), time=util.nicetimecount(x.ETA)),
        states.FINISHED:           lambda x: (_('Received from {name}') if x.direction == 'incoming' else _('Sent to {name}')).format(name=x.buddy.name),
        states.CONNECTING:         lambda x: _('Connecting to {name}...').format(name=x.buddy.name),
        states.WAITING_FOR_BUDDY:  lambda x: _('Waiting for {name} to accept file').format(name=x.buddy.name),
        states.WAITING_FOR_YOU:    lambda _x: '',
        states.CANCELLED_BY_BUDDY: lambda x: _('Canceled by {name}').format(name=x.buddy.name),
        states.WAITING_FOR_BUDDY:  lambda x: _('Waiting for {name} to accept file').format(name=x.buddy.name),
        states.CONN_FAIL_XFER:     lambda x: (_('Failed during transfer from {name}') if x.direction == 'incoming' else _('Failed during transfer to {name}')).format(name=x.buddy.name),
        states.CONN_FAIL:          lambda x: _('Failed to connect to {name}').format(name=x.buddy.name),
        states.PROXY_XFER_FILESIZE_ERROR: lambda _x:  _('File size too big for proxy transfer'),
    }


    def __init__(self):
        Observable.__init__(self)

        self.state          = self.states.CONNECTING
        self.bytecounts     = []
        self._bytes_per_sec = 0
        self.filepath       = None
        self.completed      = 0
        self._starttime     = None
        self._done          = False
        self.xfer_display_strings = self._xfer_display_strings.copy()

    def get_right_links(self):
        return [('open',   _('Open'),   lambda *a: None, self.allow_open),
                ('cancel', _('Cancel'), self.cancel, self.allow_cancel),
                ('remove', _('Remove'), lambda *a: None, self.allow_remove)]

    def get_bottom_links(self):
        return [('save',   _('Save'),       self.save, self.allow_save),
                ('saveas', _('Save as...'), self.saveas, self.allow_save_as),
                ('reject', _('Reject'),     self.decline, self.allow_reject)]

    @property
    def should_show_buddy_name(self):
        return self.state in (self.states.TRANSFERRING, self.states.WAITING_FOR_YOU)
    @property
    def details_string(self):
        return self.xfer_display_strings.get(self.state, lambda _x: self.state)(self)

    @property
    def elapsed(self):
        return default_timer() - self._starttime

    @property
    def average_speed(self):
        try:
            return self.completed / self.elapsed
        except ZeroDivisionError:
            return None

    @property
    def ETA(self):
        'The estimated number of seconds until the trasnfer is complete.'

        try:
            return (self.size - self.completed) / self.bytes_per_sec
        except ZeroDivisionError:
            return 0

    def _onrequest(self):
        # ask the user about the transfer
        self.protocol.hub.on_file_request(self.protocol, self)

    def _setcompleted(self, bytes):
        old = self.completed

        diff = bytes - old
        if diff <= 0:
            #log.debug('_setcompleted delta is <= 0 (%r - %r = %r)', bytes, old, diff)
            pass
        else:
            self._add_byte_data(default_timer(), bytes)

            self.setnotifyif('completed', bytes)

    @property
    def bytes_per_sec(self):
        now = default_timer()
        if self.state == self.states.TRANSFERRING:
            self._add_byte_data(now, self.completed)

        oldest = now
        newest = 0
        lowest = self.completed

        for t,b in self.bytecounts:
            if (self.completed - b):
                oldest = t if oldest > t else oldest
                newest = t if newest < t else newest
                lowest = b if lowest > b else lowest

        time_diff = now - oldest
        byte_diff = self.completed - lowest
        time_since_recv = now - newest

        if (time_since_recv) > self.ATROPHY_TIME:
            # been a long time since we got bytes
            self._bytes_per_sec = 0
        elif byte_diff and time_diff:
            self._bytes_per_sec = byte_diff/time_diff
        elif not byte_diff:
            self._bytes_per_sec = 0
        elif not time_diff:
            # uhh...infinite? wha?
            pass

        return self._bytes_per_sec

    def _add_byte_data(self, time, bytecount):
        time       = int(time)
        bytecounts = self.bytecounts

        actual = filter(lambda x: x[1], bytecounts)

        if not actual and bytecount:
            self._starttime = default_timer()

        if not bytecounts:
            bytecounts.append((time, bytecount))

        oldtime = bytecounts[-1][0]
        if time > oldtime:
            bytecounts.append((time, bytecount))
        elif time == oldtime:
            bytecounts[-1] = (time, bytecount)

        self.bytecounts = bytecounts[-self.TIME_THRESHOLD:]

    def get_default_dir(self):
        if pref('filetransfer.create_subfolders', False):
            service = self.protocol.service
            bname = self.buddy.name
        else:
            service = bname = ''

        return path(profile.localprefs['save_to_dir']) / service / bname

    def save(self, filepath=None):
        if filepath is None:
            try:
                orig = filepath = self.get_default_dir() / self.name
            except Exception:
                print_exc()

                # There was an exception getting the default file transfer save-to location.
                # Open a dialog and let the user choose, and then save this location as a
                # new location to save in.
                try:
                    new_path = self.saveas(lookup_default=False)
                    profile.localprefs['save_to_dir'] = os.path.dirname(new_path)
                except Exception:
                    print_exc()

                return

            orig, ext = os.path.splitext(orig)
            i = 0
            while os.path.exists(filepath):
                i += 1
                filepath = orig + (' (%d)' %i) + ext

        import wx
        parent = os.path.split(filepath)[0]
        if not os.path.exists(parent):
            try:
                os.makedirs(parent)
            except EnvironmentError, e:
                strerror = e.strerror or _('Directory does not exist')
                wx.MessageBox("Error saving file to %s.\n%s" % (parent, strerror), style=wx.ICON_ERROR | wx.OK)
                return self.saveas()

        try:

            if pref('filetransfer.preallocate', False) and getattr(self, 'size', 0):
                self.allocate(filepath, self.size)

            f = open(filepath, 'wb')
        except EnvironmentError, e:
            wx.MessageBox("Error saving file to %s.\n%s" % (parent, e.strerror), style=wx.ICON_ERROR | wx.OK)
            return self.saveas()

        if not self.name:
            self.name = path(f.name).name
        self.accept(f)

        if hasattr(self, 'notifications'):
            self.notifications.cancel()

    def saveas(self, lookup_default = True):
        default_path = ''
        if lookup_default:
            try:
                default_path = self.get_default_dir()
            except Exception:
                print_exc()

        import wx
        path = wx.FileSelector(_('Choose a location to save'),
                               default_path = default_path,
                               default_filename = self.name,
                               flags = wx.SAVE | wx.OVERWRITE_PROMPT)
        if path:
            self.save(filepath=path)
            return path

    def accept(self, _openfileobj):
        '''user has accepted the file transfer
        @param _openfileobj: A file to store the data in.
        '''
        raise NotImplementedError

    def decline(self):
        '''user has rejected the file transfer'''
        if hasattr(self, 'notifications'):
            self.notifications.cancel()

    def cancel(self, state=None):
        '''user has decided to stop the file transfer.
        This should only be possible if the transfer has already started.
        The implementing class should do cleanup here, i.e. trigger close of
        socket/file.'''
        raise NotImplementedError

    def allocate(self, path, size):
        remaining = size
        block_size = 4096
        null = '\0' * block_size
        with open(path, 'wb') as f:
            while remaining:
                if remaining > block_size:
                    f.write(null)
                    remaining -= block_size

                else:
                    f.write(null[:remaining])
                    remaining = 0

    @property
    def type(self):
        'Returns "folder" or "file".'

        if self.numfiles > 1 or getattr(self, 'multiple', False):
            type = 'folder'
        else:
            type = 'file'

        return type

    def _ondone(self):
        oldstate = self.state
        if self.state in self.states.TransferringStates:
            self.state = self.states.FINISHED

        if self.state in self.states.CompleteStates:
            fire('filetransfer.ends',
                 filetransfer = self,
                 buddy = self.buddy,
                 target = self,
                 onclick = lambda *a: self.filepath.openfolder()) # clicking the popup opens the folder
        elif self.state in self.states.FailStates:
            #see comment in on_error
            self.on_error()

        self._done = True

        if oldstate != self.state:
            self.notify('state', oldstate, self.state)

    def on_error(self):
        # This is now really a cleanup routine, but without checking for every callsite,
        # it doesn't seem like a good idea to rename it
        do_fire = True
        if self.state not in self.states.ErrorStates:
            log.info('%r: %r is not an error. Not firing popup.', self, self.state)
            do_fire = False
        else:
            log.info('%r: %r is a file transfer error. Firing popup...', self, self.state)

        if self._done:
            return

        if do_fire:
            sending = self.direction == "outgoing"

            errmsg = _('Failed to send {filename} to {name}') if sending else _('Failed to receive {filename} from {name}')

            fire('filetransfer.error', sticky=False,
                 errmsg = errmsg.format(filename = self.name, name = self.buddy.name))


        if getattr(self, 'openfile', None) is not None:
            of, self.openfile = self.openfile, None
            of.close()

        self._done = True

    def on_get_buddy(self, buddy):
        if buddy.status != 'offline':
            buddy.add_observer(self.buddy_state_change,'status')

    def buddy_state_change(self, src, attr, old, new):
        if new == 'offline':
            self.cancel(state=self.states.BUDDY_GONE)

            src.remove_observer(self.buddy_state_change, 'status')

    def allow_open_folder(self):
        return self.state != self.states.WAITING_FOR_YOU

    def allow_open(self):
        return self.state == self.states.FINISHED

    def is_active(self):
        return self.state in (self.states.CONNECTING,
                              self.states.TRANSFERRING,
                              self.states.WAITING_FOR_BUDDY,)
    def allow_cancel(self):
        return self.is_active()

    def is_inactive(self):
        return not self.is_active() and self.state != self.states.WAITING_FOR_YOU

    def allow_remove(self):
        return self.is_inactive()

    def is_done(self):
        return self.state in (self.states.FailStates | self.states.CompleteStates)

    def allow_save(self):
        return self.state == self.states.WAITING_FOR_YOU

    def allow_save_as(self):
        return self.state == self.states.WAITING_FOR_YOU

    def allow_reject(self):
        return self.state == self.states.WAITING_FOR_YOU

class IncomingFileTransfer(FileTransfer):
    direction = 'incoming'

    @property
    def message(self):
        'For a file transfer object, return a displayable prompt message.'

        if self.type == 'folder':
            # A message for receiving a folder.
            msg = ('%s is sending you folder "%s" (%d files, %d bytes)\n\n'
                   'Would you like to accept it?' % \
                   (self.buddy.name, self.name, self.numfiles, self.size))
        else:
            # A message for receiving a single file.

            size_str = '' if not hasattr(self, 'size') else '(%d bytes)' % self.size

            msg = '%s is sending you file "%s" %s\n\nWould you like to accept it?' \
                  % (self.buddy.name, self.name, size_str)

        return msg


class OutgoingFileTransfer(FileTransfer):
    direction = 'outgoing'


class IncomingHTTPFileTransfer(IncomingFileTransfer):
    'Simple file transfer object for HTTP GETting a file.'

    def __init__(self, protocol, buddy, name, url):
        IncomingFileTransfer.__init__(self)

        autoassign(self, locals())
        self.buddy = buddy
        self.numfiles = 1
        self.name = name
        self.bytes_written = 0
        self.size = 0 # TODO http head to find size
        self.chunker = None

    @threaded
    def accept(self, fileobj):
        try:
            conn = urlopen(self.url)
        except URLError, e:
            import traceback
            traceback.print_exc()
            self.cancel(state = self.states.CONN_FAIL)
            raise e
        # read the size of the file from the HTTP Content-Length header

        info = conn.info()
        self.size     = int(info.get('Content-Length', 0))
        log.info('reading a file (%s) of length %d bytes', self.url, self.size)

        if self.state != self.states.CANCELLED_BY_YOU:
            self.state    = self.states.TRANSFERRING
            self.filepath = path(fileobj.name)
            self.chunker  = FileChunker.tofile(conn, fileobj, self.progress)

        if self.state != self.states.CANCELLED_BY_YOU:
            self._ondone()

    def cancel(self, state=None):
        if state is None:
            state = self.states.CANCELLED_BY_YOU
        self.state = state

        if self.chunker is not None:
            self.chunker.cancelled = True
        self.on_error()


    def decline(self):
        info('%r declined', self)
        self.state = self.states.CANCELLED_BY_YOU
        FileTransfer.decline(self)

    def progress(self, bytes_written):
        self._setcompleted(bytes_written)
        self.bytes_written = bytes_written

    def __repr__(self):
        return '<IncomingHTTPFileTransfer %s>' % self.name

class ManualFileTransfer(IncomingHTTPFileTransfer):
    """
        A manual HTTP file transfer download, with success, cancel, and error callbacks.
    """

    def __init__(self, name, url, whenDoneCB, onCancelCB, onErrorCB):

        self.whenDoneCB = whenDoneCB
        self.onCancelCB = onCancelCB
        self.onErrorCB  = onErrorCB

        from gui import skin
        protocol = None
        buddy = Storage(name = "Digsby Servers", alias = "Digsby Servers", serviceicon=skin.get('serviceicons.digsby'))

        IncomingHTTPFileTransfer.__init__(self, protocol, buddy, name, url)

    def manual_download(self, temp_path=None):
        if temp_path is None:
            #make a temp file
            fd, temp_path = tempfile.mkstemp()
            os.fdopen(fd).close()

        self.save(temp_path)
        self.downloaded_path = temp_path # TODO: not necessarily! see "save" above
        profile.xfers.insert(0, self)

    def get_default_dir(self):
        return self.dest

    def _onrequest(self):
        pass

    def _ondone(self):
        self.setnotifyif('state', self.states.FINISHED)

        self._done = True

        self.whenDoneCB(self.downloaded_path)


    def cancel(self, state=None):
        IncomingHTTPFileTransfer.cancel(self, state)

        if self.state == self.states.CANCELLED_BY_YOU:
            self.onCancelCB()

    def on_error(self):
        self.onErrorCB()

    def allow_open_folder(self):
        return False

    def allow_open(self):
        return False

    def allow_save(self):
        return False

    def allow_save_as(self):
        return False

    def allow_reject(self):
        return False

