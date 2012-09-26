from __future__ import with_statement
from httplib import IncompleteRead
from .YahooSocket import DEFAULT_YMSG_VERSION

FILE_XFER_URL        = 'http://filetransfer.msg.yahoo.com:80/notifyft'

PROXY_FILESIZE_LIMIT = 2 ** 20 # 10 MB

import common
from traceback import print_exc
from util import threaded, chained_files
from .yahooutil import filename_from_url
import struct
from StringIO import StringIO
from util.net import HTTPConnProgress


from logging import getLogger
log = getLogger('yahoo.ft'); info = log.info; error = log.error

in_cls  = common.IncomingHTTPFileTransfer
out_cls = common.filetransfer.OutgoingFileTransfer

# first eight bytes of PNGs (the only thing Yahoo's icon sever will accept)
PNG_HEADER = struct.pack('8B', 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)

class YahooHTTPIncoming(in_cls):
    'Incoming HTTP file transfer.'

    def __init__(self, protocol, buddy, url):

        # Use filename_from_url to grab filename
        in_cls.__init__(self, protocol, buddy, filename_from_url(url), url)

def set_buddy_icon(yahoo, image_data):
    log.info('set_buddy_icon %r', yahoo)
    YahooIconSender.send_buddy_icon(yahoo, image_data)


class OutgoingYHTTPXfer(out_cls):

    direction = 'outgoing'
    http_path = '/notifyft'
    host      = 'filetransfer.msg.yahoo.com:80'
    conn_host = 'filetransfer.msg.yahoo.com'

    def __init__(self, protocol, buddy = None, fileinfo = None, initiate = True):
        out_cls.__init__(self)

        if fileinfo is not None:
            self.filepath = fpath  = fileinfo.files[0]
            self.name     = fpath.name
            self.size     = fpath.size

        self.buddy    = buddy
        self.protocol = protocol
        self.cancelled = False



        if hasattr(fileinfo, 'obj'): fileinfo.obj.close()
        if initiate:
            self.initiate_transfer()

    def initiate_transfer(self, message = ''):
        filesize = self.filepath.size

        # Yahoo's proxy server has a filesize limit.
        if filesize > PROXY_FILESIZE_LIMIT:
            self.state = self.states.PROXY_XFER_FILESIZE_ERROR
            return

        # squeeze the following YDict into an HTTP post to Yahoo's file
        # transfer server
        protocol = self.protocol
        ydata = protocol.yahoo_packet_v_bin(DEFAULT_YMSG_VERSION,
            'filetransfer', 'available',
            'away_buddy', protocol.self_buddy.name,
            'to',         self.buddy.name,
            'message',    message,
            'filename',   self.name,
            'filesize',   str(filesize),
            'filedata',   '')

        sublen = struct.unpack('!H', ydata[8:10])[0] - (8 + len(str(filesize))) + 14
        ydata  = ydata[:8] + struct.pack('!H', sublen-1) + ydata[10:-2]

        self.state = self.states.TRANSFERRING

        try:
            fileobj = file(self.filepath, 'rb')
        except:
            print_exc()
            self.state = self.states.CONN_FAIL
            self.on_error()
        else:
            self._post_file(ydata, protocol.cookie_str, fileobj = fileobj, filesize = filesize)

    def cancel(self):
        try:
            self.conn.close()
            del self.conn
        except:
            pass

        self.cancelled = True
        self.state = self.states.CANCELLED_BY_YOU


    @threaded
    def _post_file(self, ydata, cookies, fileobj = None, filesize = None):
        try:
            self.conn = conn = HTTPConnProgress(self.conn_host)
        except Exception, e:
            print_exc()
            if not self.cancelled:
                self.state = self.states.CONN_FAIL
                self.on_error()
            return False

        # Hack httplib to send HTTP/1.0 as the version
#        conn._http_vsn_str = 'HTTP/1.0'
#        conn._http_vsn = 10

        #conn.set_debuglevel(3)
        conn.putrequest('POST', self.http_path, skip_host = True, skip_accept_encoding=True)
#        conn.putheader ('Referer', 'foo')
        conn.putheader ('Cookie', cookies)
#        conn.putheader ('User-Agent', 'Mozilla/4.0 (compatible; MSIE 5.5)')
        conn.putheader ('Host', self.host)
        conn.putheader ('Content-Length', str(len(ydata) + filesize))
        conn.putheader ('Cache-Control', 'no-cache')

        conn.endheaders()

        diff = len(ydata) - filesize

        try:
            # use "chained_files" function to send file without reading it into a str
            if ydata != '':
                conn.send_file_cb(chained_files([ydata, fileobj]),
                                  self._setcompleted,
                                  progressDelta = len(ydata)) # report bytes MINUS the length of the YMSG header
            else:
                conn.send_file_cb(fileobj, self._setcompleted)
        except:
            if not self.cancelled:
                print_exc()
                self.state = self.states.CONN_FAIL
            try: conn.close()
            except: pass
        finally:
            try: fileobj.close()
            except: pass

        if self.state != self.states.TRANSFERRING:
            return


        # we're done--make sure the progress bar is at 100%
        self._setcompleted(filesize)

        # Check for OK
        try:
            response = conn.getresponse()
            respdata, status = response.read(), response.status

            log.info('response data %d bytes, status code %s', len(respdata), status)
            log.info('response data %s', respdata)

            if status != 200:
                self.state = self.states.CONN_FAIL_XFER
                log.error('ERROR: POST returned a status of %d', status)
                return False

            info('HTTP POST response status %d', status)
        except IncompleteRead:
            if ydata != '':
                raise
        finally:
            conn.close()

        self.state = self.states.FINISHED
        self._ondone()
        return True


class YahooIconSender(OutgoingYHTTPXfer):
    def __repr__(self):
        return '<YahooIconSender>'

    @classmethod
    def send_buddy_icon(cls, protocol, image_data):

        # yahoo's server accepts only PNGs--make the icon one if it isn't already.
        from PIL import Image
        i = Image.open(StringIO(image_data))
        if (image_data[:8] != PNG_HEADER) or (i.size != (96, 96)):
            converted = StringIO()
            i2 = i.Resized(96)
            i2.save(converted, 'PNG')
            image_data = converted.getvalue()

        xfer = YahooIconSender(protocol, initiate = False)

        selfname = protocol.self_buddy.name
        filesize = len(image_data)

        ydata = protocol.yahoo_packet_v_bin(DEFAULT_YMSG_VERSION,
            'picture_upload',  'available',
            'frombuddy',  selfname,
            'expires',    struct.pack('6s', '604800'),
            'away_buddy', selfname,
            'filesize',   str(filesize),
            'filename',   'myicon.png',
            'message',    ' ',
            'filedata',   '')

        sublen = struct.unpack('!H', ydata[8:10])[0] - (8 + len(str(filesize))) + 14
        ydata  = ydata[:8] + struct.pack('!H', sublen-1) + ydata[10:-2]

        xfer.state = xfer.states.TRANSFERRING

        log.info('sending %d bytes of image data', filesize)
        xfer._post_file(ydata, protocol.cookie_str, fileobj = StringIO(image_data), filesize = filesize)


    def _ondone(self):
        self.setnotifyif('state', self.states.FINISHED)
        self._done = True

    def on_error(self):
        log.critical('error sending icon')
