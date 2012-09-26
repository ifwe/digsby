'''
Oscar File Transfer

the definitive reference:
U{http://gaim.sourceforge.net/summerofcode/jonathan/ft_doc.pdf}
'''
from __future__ import with_statement

__metaclass__ = type

from oscar.rendezvous.peer import OscarPeer
from oscar.rendezvous.rendezvous import oscarcookie, map_intarg, rendezvous_tlvs
import oscar.capabilities as capabilities
from util import Storage, strlist, NoneFileChunker, to_hex
from util.packable import Packable
import util, oscar.snac, oscar.OscarUtil
import common
import hooks
from path import path
import os.path
import traceback
import struct

from logging import getLogger
log = getLogger('oscar.rdv.ft'); info = log.info

def prettyoft(oft):
    return '\n'.join('%20s: %r' % line for line in list(iter(oft)))


rz, tlv, tlv_list = rendezvous_tlvs, oscar.OscarUtil.tlv, oscar.OscarUtil.tlv_list



#
# For sending a file or folder
#
def send(oscar, screenname, filestorage):
    'Request for sending a file to a buddy.'
    cookie = oscarcookie()
    oscar.rdv_sessions[cookie] = transfer = \
        OutgoingOscarFileTransfer(oscar, screenname, cookie, filestorage)
    transfer.request()
    return transfer

#
# Oscar file transfer packets - headers sent and received on an oscar direct
# connection.
#
class OFTHeader(Packable):
    fmt = strlist('''
        protocol_version 4s  # Always 'OFT2'
        length           H   # includes all data, including version and length
        type             H   # one of "types" below
    ''')

    invars = [lambda self: self.protocol_version == 'OFT2',
              lambda self: self.type in self.types.values()]

    types = Storage(prompt          = 0x0101,
                    ack             = 0x0202,
                    done            = 0x0204,
                    receiver_resume = 0x0205,
                    sender_resume   = 0x0106,
                    rcv_resume_ack  = 0x0207,
                    )


assert len(OFTHeader()) == 8

class OFTBody(Packable):
    fmt = strlist('''
    cookie              Q
    encryption          H
    compression         H
    num_files           H
    files_left          H
    num_parts           H
    parts_left          H
    total_size          I
    file_size           I

    modification_time   I   # since unix epoch
    checksum            I   # see OscarFileTransferChecksum
    recv_fork_checksum  I
    fork_size           I
    creation_time       I
    fork_checksum       I
    bytes_received      I
    recv_checksum       I
    id_string           32s # 32 byte right padded string: usually 'CoolFileXfer'

    flags               B   # Flags: 0x20 - Negotiation (not complete), 0x01 - Done
    list_name_offset    B   # always 0x1c
    list_size_offset    B   # always 0x11

    dummy_block         69s # Dummy Block - large null block for future expansion of OFT

    mac_file_info       16s # Mac File Info

    charset             H   # charset
    subset              H   # subset: 0 for ASCII, 2 for UTF-16BE, 3 for ISO-8859-1
    ''')

    default_checksum = 0xffff0000

    @staticmethod
    def padfilename(filename):
        '''Following an OFT body is a padded filename which at least 64
        characters and maybe more.'''

        if len(filename) < 64:
            filename += '\0' * (64 - len(filename))
            assert len(filename) == 64
        return filename

# Right pad an ID string for the header
OFTId = 'Cool FileXfer'
OFTId = OFTId + ( '\0' * (32 - len(OFTId)) )

# The two glued together should always equal 192 bytes.
assert len(OFTHeader()) + len(OFTBody()) == 192

#
# file transfer logic
#

class OscarFileTransfer( OscarPeer ):
    'Base class for file transfers, providing channel 2 messaging.'

    def __init__(self, protocol, screenname, cookie):
        OscarPeer.__init__(self, protocol, screenname, cookie,
                           capabilities.by_name['file_xfer'])
        common.FileTransfer.__init__(self)
        self.cancelled = False
        self.resuming = False
        self.on_get_buddy(self.buddy)

    def ch2cancel(self, data):
        log.info('%r cancelled by buddy', self)
        self.cancelled = True
        self.cancel_by_buddy()
        if data:
            log.info('data in a ch2 cancel: %s', to_hex(data))

    def cancel_by_buddy(self):
        log.info('cancel_by_buddy')
        if self.state != self.states.CANCELLED_BY_YOU:
            self.state = self.states.CANCELLED_BY_BUDDY

        try:
            self.fileobj.close()
        except Exception:
            traceback.print_exc()


    def on_close(self):
        log.info('%r on_close', self)

        try:
            self.fileobj.close()
        except AttributeError:
            pass

        if self.state == self.states.TRANSFERRING:
            self.state = self.states.CONN_FAIL_XFER

            self.on_error()


    def close(self):
        log.info('close')
        try:
            self.socket.close()
            del self.socket
        except Exception:
            pass
        self.done = True
        try:
            self.fileobj.close()
        except AttributeError:
            pass


    def cancel(self, msg = '', state=None):
        if hasattr(self, 'socket') and self.socket:
            try:
                self.socket.cancel_timeout()
            except Exception:
                #temporary until I figure out how to cancel
                traceback.print_exc()

        try:
            self.filechunker.cancelled = True
        except Exception:
            traceback.print_exc()
            info('$$$ sending cancel')
            self.send_rdv('cancel')
        self.close()

        self.setnotifyif('cancelled', True)

        info('%r cancelled. %s', self, msg)
        if state is None:
            state = self.states.CANCELLED_BY_YOU
        self.state = state

    def ch2accept(self, data):
        if data:
            log.error('got data in a channel 2 accept: data = %r', data)
            self.cancel()
        else:
            log.info('ch2accept data = %r', data)

    def decline_transfer(self, reason = None):
        'Cancels this file transfer.'
        log.info('decline_transfer: reason = %r', reason)
        self.cancel()

    def send_oft(self, type, setvalues=True):
        # Use most of the values received from the sender, but set some:


        oft = self.oft

        if not oft:
            return

        if setvalues:
            oft.id_string = OFTId
            oft.cookie = self.cookie
            oft.list_name_offset = 0x1c
            oft.list_size_offset = 0x11
            oft.flags = 0x01 if 'type' == 'done' else 0x20
            oft.checksum = OFTBody.default_checksum #TODO: incomplete transfers

        info('sending oft %s for %s', type, self.filename )
        info(prettyoft(oft) + '\n  filename: %s', self.filename)
        self.socket.push(oftpacket(type, oft, self.filename))

#
# sending
#

class OutgoingOscarFileTransfer(OscarFileTransfer, common.OutgoingFileTransfer):

    def __init__(self, o, screenname, cookie, fileinfo):
        OscarFileTransfer.__init__(self, o, screenname, cookie)

        [setattr(self, a, fileinfo[a]) for a in \
         'name files size numfiles'.split()]

        if fileinfo.numfiles == 1 and 'obj' in fileinfo:
            fileinfo.obj.close()

        else:
            self.rootpath = fileinfo.path

        self.filepath = path(fileinfo.path)


        # If obj is an open file object, it's raw contents are dumped to the
        # socket after the next
        self.fileobj = None
        self.oft = self.next_file()

        self.accepted = False
        self.connected = False
        self.completed = 0
        self.state = self.states.WAITING_FOR_BUDDY

    def next_file(self):
        if self.files:
            self.file = self.files.pop(0)

            # When sending folders in AIM, path elements are separated by
            # ASCII character 1.
            if hasattr(self, 'rootpath'):
                p = self.rootpath.relpathto(self.file)
                self.filename = p.normpath().replace('\\','/').replace('/', chr(1))
            else:
                self.filename = self.file.name

            return self.oft_for_file(self.file)
        else:
            self.file = None
            return False

    def __repr__(self):
        return '<OutgoingOscarFileTransfer to %s (%r)>' % \
            (self.screenname, getattr(self.file, 'name', None) or '')

    def request(self, message = '<html>'):
        # Assemble information about the file or directory we are sending.
        xdata    = xdata_block(self.name, self.size, self.numfiles)

        self.establish_out_dc(message=message, extratlvs=[
            (rz.extended_data, xdata),
            (rz.filename_encoding, 'utf-8'),
        ])

    def on_odc_connection(self):
        info('%r connected!', self)
        self.connected = True
        self.maybe_start()

    def received_oft_header(self, data):
        'Received the first part of an OFT packet.'
        header, data = OFTHeader.unpack(data)
        assert data == ''
        log.debug('received OFT header: oft=%(protocol_version)s length=0x%(length)x type=0x%(type)x', dict(header))

        bytes_left = header.length - OFTHeader._struct.size

        # ACK - the receiver is ready to receive binary file data.
        # Resume ack - receiver is ready to receive file data, starting from offset
        if header.type in (OFTHeader.types.ack, OFTHeader.types.rcv_resume_ack,):#OFTHeader.types.receiver_resume):
            #self.state = self.states.CONNECTING
            self.open_file()
        # DONE - the receiver received all the bytes of a file successfully.
        elif header.type == OFTHeader.types.done:
            try:
                self.fileobj.close()
            except AttributeError:
                pass
            self.fileobj = None
            self.oft = self.next_file()

            if not self.oft:
                if self.completed:
                    self.state = self.states.FINISHED
                    self._ondone()
                else:
                    self.cancel_by_buddy()
                self.close()
            return

        # Receiver wants to resume
        elif header.type == OFTHeader.types.receiver_resume:
            log.info('Going to resume file %s' % self.file)
            self.resuming = True
        else:
            log.warning('Error! OFT type %r', header.type)


        self.socket.receive_next(bytes_left, self.received_oft_body)

    def open_file(self):
        try:
            self.fileobj = self.file.open('rb')
            return True
        except IOError:
            self.cancel('Could not open file %s' % self.file)
            return False


    def received_oft_body(self, data):
        'The remainder of an OFT packet has come in.'
        oft, data = OFTBody.unpack(data)
        filename, data = read_cstring(data)
        info(prettyoft(oft) + '\n  filename: %s', filename)
        self.oft = oft
        self.socket.receive_next(OFTHeader, self.received_oft_header)

        # After an OFT body, we need to either...
        if self.fileobj:
            if self.resuming:
                self.fileobj.seek(oft.bytes_received)
                self._setcompleted(self.fileobj.tell())
            # Send file data,
            self.filechunker = NoneFileChunker(self.fileobj, close_when_done=True,
                                      progress_cb = self._setcompleted)
            log.info('Pushing FileChunker onto socket')
            self.socket.push_with_producer(self.filechunker)
        elif self.oft:
            # Sned a new prompt,
            if self.resuming:
                self.send_oft('sender_resume', False)
            else:
                self.send_oft('prompt')
        else:
            # Or close the socket.
            info('DONE!')
            self.state = self.states.FINISHED
            self.close()

    def ch2accept(self, data):
        info('received CH2 accept')
        self.accepted = True
        self.maybe_start()

    def maybe_start(self):
        if not self.accepted or not self.connected:
            if not self.accepted:  info('no RDV accept yet')
            if not self.connected: info('no connection yet')
            return

        if self.state == self.states.FINISHED:
            info('got "maybe_start" but already finished')
            return

        self.state = self.states.TRANSFERRING
        if not getattr(self, 'sent_first', False):
            info('sending first oft prompt')
            self.sent_first = True
            self.send_oft('prompt')
        self.socket.receive_next(OFTHeader, self.received_oft_header)

    def oft_for_file(self, file):
        return OFTBody(
            cookie = self.cookie,
            num_files = self.numfiles,
            files_left = 1 + len(self.files),
            num_parts = 1,
            parts_left = 1,
            total_size = self.size,
            file_size = file.size,
            modification_time = int(file.mtime),
            creation_time = int(file.ctime),
            checksum = OFTBody.default_checksum,
            recv_fork_checksum = OFTBody.default_checksum,
            fork_checksum = OFTBody.default_checksum,
            recv_checksum = OFTBody.default_checksum,
            id_string = OFTId,
            dummy_block = '\0' * 69,
            mac_file_info = '\0' * 16,
            charset = 0,
            subset = 0,
        )
#
# receiving
#

class IncomingOscarFileTransfer( OscarFileTransfer, common.IncomingFileTransfer ):
    'Negotiates a peer connection, and begins receiving a file.'

    direction = 'incoming'

    def __init__(self, o, screenname, cookie):
        OscarFileTransfer.__init__(self, o, screenname, cookie)
        self.completed = 0

    def handle_request(self, rendtlvs):
        '''A rendezvous packet with request number 1 has come in with the
        specified TLVs.'''

        # unpack TLV 0x2711 (the last entry in the rendezvous block)
        info, data = unpack_extended_data( rendtlvs.extended_data )

        # ...and store file count, name, size
        self.__dict__.update(info)

        self._onrequest()

    def accept(self, file_obj):
        'The UI accepts this file transfer.'

        # If we've already been cancelled, display an error alert.
        if self.cancelled:
            e = OscarFileTransferError('The sender has already cancelled this '
                                       'file request.')
            self.protocol.hub.on_error(e)
        else:
            if isinstance(file_obj, file) or self.numfiles == 1:
                # For single files, the hub gives this method an open file
                # object. For consistency, just grab it's path and use that,
                # so that it operates like receiving a folder.
                self.filepath = path(file_obj.name)
                self.rootpath = self.filepath.parent

                file_obj.close()
            else:
                # Otherwise, make a new directory with the folder name where
                # the user specified.
                self.rootpath = os.path.join(file_obj, self.name)
                if not os.path.exists(self.rootpath):
                    os.makedirs(self.rootpath)

                self.filepath = path(self.rootpath)

            assert isinstance(self.rootpath, basestring)
            info('self.rootpath = %r', self.rootpath)
            info('accepting incoming file transfer, saving %s to %s',
                 'file' if self.numfiles == 1 else 'files', self.rootpath)

            self.state = self.states.CONNECTING
            self.establish_dc()

    def decline(self):
        self.state = self.states.CANCELLED_BY_YOU
        self.send_rdv('cancel')
        common.IncomingFileTransfer.decline(self)

    def on_odc_connection(self):
        '''At this point self.socket should be a connected socket to either
        another AIM user, or a proxy server with initialization already taken
        care of.'''
        self.state = self.states.TRANSFERRING
        self.socket.receive_next(OFTHeader, self.received_oft_header)

    def received_oft_header(self, data):
        'Received the first part of an OFT packet.'
        header, data = OFTHeader.unpack(data)
        assert data == ''

        log.debug('received OFT header: %r', dict(header))
        if header.type == OFTHeader.types.prompt:
            bytes_left = header.length - OFTHeader._struct.size
            log.debug('receiving %d more OFT body bytes', bytes_left)
            self.socket.receive_next(bytes_left, self.received_oft_body)
        else:
            self.fail('Error! OFT type ' + str(header.type))

    def received_oft_body(self, data):
        'The remainder of an OFT packet has come in.'
        oft, data = OFTBody.unpack(data)
        self.oft = oft
        info('incoming oft body...\n' + prettyoft(oft))

        nullindex = data.find('\0')
        if nullindex == -1 and len(data) >= 64:
            self.filename = filename = data
        elif nullindex == -1:
            raise AssertionError("couldn't find a null byte in the padded filename")
        else:
            self.filename = filename = data[:nullindex]

        self.fileobj = openpath(self.rootpath, self.filepath.name)

        info('incoming file: %s (%d bytes), %d left',
             filename, oft.file_size, oft.files_left)
        self.send_oft('ack')

        self.socket.push_collector(self.collect_file_bytes)
        if oft.file_size > 0:
            self.socket.receive_next(oft.file_size, self.received_file)
        else:
            self.received_file()

    def collect_file_bytes(self, data):
        'When receiving file bytes, this is the asynchat collector.'

        try:
            self.fileobj.write(data)
        except IOError:
            # probably closed file
            traceback.print_exc()
            return
        else:
            completed = self.fileobj.tell()
            self.oft.bytes_received = completed
            self._setcompleted(completed)
        finally:
            self.data = ''

    def received_file(self, *data):
        self.socket.pop_collector()

        info('received file %s', self.fileobj.name)
        self.fileobj.close()
        self.send_oft('done')

        if self.oft.files_left == 1:
            info('done!')
            self._ondone()
            self.socket.close()
        else:
            # repeat the process if there are files left.
            self.socket.receive_next(OFTHeader, self.received_oft_header)

    def fail(self, msg):
        log.error(msg)
        self.close()

    def __repr__(self):
        return '<IncomingOFT from %s>' % self.screenname


def oftpacket(type, body, filename):
    'Constructs a complete OFT packet.'

    #TODO: unicode
    if isinstance(filename, unicode):
        filename = filename.encode('utf8')
    else:
        filename = str(filename)

    padded = OFTBody.padfilename(filename)
    return ''.join([ OFTHeader('OFT2',
                     length = 192 + len(padded),
                     type = map_intarg(type, OFTHeader.types)).pack(),
                     body.pack(),
                     padded ])

def oft_filename(fn):
    '''
    OFT filenames are null terminated, must be at least 64 bytes long, but may
    be longer.
    '''
    fn += chr(0)
    if len(fn) < 64:
        fn += (64 - len(fn)) * chr(0)
        assert len(fn) == 64
    return fn

def read_cstring(data): #TODO: should go in OscarUtil
    '''
    Reads a null terminated string from data, returning the string, and the
    remainder of the data, not including the null byte.

    >>> s = 'some string' + chr(0) + 'extra data'
    >>> foo, data = read_cstring(s)
    >>> print foo
    'some string'
    '''
    i = data.find(chr(0))
    if i == -1:
        raise ValueError('not a null terminated string')

    return data[:i], data[i+1:]

def unpack_extended_data(data):
    'Unpacks the capabilities/extra data (TLV 0x2711) in a rendezvous packet.'

    multiple, filecount, totalbytes = struct.unpack('!HHI', data[:8])
    data = data[8:]
    filename, data = read_cstring(data)

    return util.Storage( numfiles = filecount,
                         multiple = multiple == 0x002,
                         size = totalbytes,
                         name = filename ), data

def xdata_block(filename, filesize, filecount = 1):
    'builds TLV 0x2711 in Ch2 RDV requests, which shows filename, count'

    assert filecount > 0 and isinstance(filename, basestring)
    return struct.pack('!HHI',
                       0x001 if filecount == 1 else 0x002,
                       filecount,
                       filesize) + filename.encode('utf-8') + '\0'

def openpath(rootpath, filename):
    '''
    Given an "OSCAR" path, returns an open file object for the
    specified file.

    In folder transfers, ASCII character 0x01 splits directories and filenames,
    i.e. dir(0x01)subdir(0x01)filename.txt. This function will create any
    directory hierarchy needed to open the file.
    '''

    PATHSEP  = chr(1)
    needdirs = filename.find(PATHSEP) != -1
    path     = filename.split(PATHSEP)

    filename = path.pop(-1)
    path = [rootpath] + path

    if needdirs:
        pathstr = os.path.join(*path)
        if not os.path.exists(pathstr):
            info('calling makedirs(%s)', pathstr)
            os.makedirs(pathstr)

    filepath = path + [filename]
    return open(os.path.join(*filepath), 'wb')



class OscarFileTransferError(Exception): pass

class OFTChecksum(object):
    starting_value = 0xffff0000L

    def __init__(self, data = None):

        self.checksum = self.starting_value

        if data is not None:
            self.update(data)

    def update(self, data, offset = 0):
        check = (self.checksum >> 16) & 0xffffL

        for i in xrange(len(data)):
            oldcheck = check
            byteval  = ord(data[offset + i]) & 0xff
            check   -= byteval if (i & 1) != 0 else byteval << 8

            if check > oldcheck: check -= 1

        check = ((check & 0x0000ffff) + (check >> 16))
        check = ((check & 0x0000ffff) + (check >> 16))

        checksum = check << 16 & 0xffffffff

def initialize():
    log.info('\tloading rendezvous handler: file transfer')
    import oscar.rendezvous.peer as peer
    peer.register_rdv_factory('file_xfer', IncomingOscarFileTransfer)

hooks.Hook('oscar.rdv.load').register(initialize)
