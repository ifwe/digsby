#__LICENSE_GOES_HERE__

import traceback
import logging
import codecs
import common.AsyncSocket as AS
import peak.util.addons as addons
import lxml.etree as etree

import gntp

import wx
import email
import util
import common
import gui.toast as toast

log = logging.getLogger("gntp.recv")

# Cross domain policy in case flash shows up and wants to give us notifications
# Accepts incoming on port 23053 (growl port)
cross_domain_policy = '''\
<?xml version="1.0"?>
<!DOCTYPE cross-domain-policy SYSTEM "xml/dtds/cross-domain-policy.dtd">
<cross-domain-policy>
   <site-control permitted-cross-domain-policies="master-only"/>
   <allow-access-from domain="*" to-ports="%d" />
</cross-domain-policy>'''

def get_cross_domain_policy():
    return cross_domain_policy % common.pref("gntp.port", type = int, default = 23053)

class GrowlServerSocket(AS.AsyncSocket):
    terminator = '\r\n\r\n'
    expected_chunks = 1
    received_chunks = 0

    def collect_incoming_data(self, data):
        retval = super(GrowlServerSocket, self).collect_incoming_data(data)

        if self.data.endswith('\0'):
            #some kind of data from flash. most likely a request for cross domain policy
            self.found_terminator(flash = True)

        return retval

    def handle_flash_data(self):
        '''
        The GNTP project has a flash-based JS connector for allowing
        javascript apps to send growl notifies to localhost. The only
        known "flash-only" thing they do is request a cross-domain policy.
        Handle that here.
        '''
        data, self.data = self.data, ''
        data = data.strip('\0')
        log.debug("got flash data: %r", data)
        try:
            doc = etree.fromstring(data)
        except Exception, e:
            raise e

        if doc.tag == 'policy-file-request':
            self.push(codecs.BOM_UTF8 + get_cross_domain_policy() + '\0')

    def found_terminator(self, flash = False):
        self.set_terminator('\r\n\r\n')

        if flash:
            return self.handle_flash_data()
        else:
            if len(self.data) == 0:
                return

            self.data += self.terminator

        if self.received_chunks == 0:
            try:
                headers = email.message_from_string(self.data.split('\r\n', 1)[1])
            except Exception as e:
                self.push(str(gntp.GNTPError(errorcode=500, errordesc='Unknown server error: %r' % repr(e))))
                return
            else:
                self.expected_chunks = int(headers.get('Notifications-Count', '0')) + 1

        self.received_chunks += 1
        if self.expected_chunks > self.received_chunks:
            return

        self.received_chunks = 0

        data, self.data = self.data, ''
        log.debug("received growl message: %r / %r", self, data)

        result = None
        try:
            result = on_growl_data(data)
        except gntp.BaseError as e:
            traceback.print_exc()
            self.push(e.gntp_error())
        except Exception as e:
            traceback.print_exc()
            self.push(str(gntp.GNTPError(errorcode=500, errordesc='Unknown server error: %r' % repr(e))))
        else:
            if result is not None:
                self.push(result)

        self.close_when_done()

    def push(self, data):
        log.debug("Sending: %r", data)
        return super(GrowlServerSocket, self).push(data)

    def handle_close(self):
        super(GrowlServerSocket, self).handle_close()
        self.close()

class GrowlListenServer(AS.AsyncServer):
    SocketClass = GrowlServerSocket

class GrowlReceiver(addons.AddOn):
    _did_setup = False
    def setup(self):
        if self._did_setup:
            return
        self._did_setup = True

        try:
            self.server = GrowlListenServer()
            self.server.bind(common.pref("gntp.host", type = str, default = ''),
                             common.pref("gntp.port", type = int, default = 23053))

            self.server.listen(5)
        except Exception as e:
            log.error("Error setting up growl listen server: %r", e)
            self.server = None
            self._did_setup = False
        else:
            log.info("Growl server listening on %s:%d", *self.server.getsockname())

def on_growl_data(data):
    gmsg = e = None
    for password in common.pref("gntp.password_list", type=list, default = []) + [None]:
        try:
            gmsg = gntp.parse_gntp(data, password)
        except gntp.BaseError as e:
            continue
        else:
            e = None
            break
    else:
        if e is not None:
            raise e

    headers = {}
    for key, value in gmsg.headers.items():
#        value_chunks = email.Header.decode_header(value)
#        value = ''.join(chunk.decode(charset) for (chunk, charset) in value_chunks)
        headers[key.lower()] = value.decode('utf8')

    on_growl_message(util.Storage(info = gmsg.info, headers = headers, resources = gmsg.resources))

    return str(gntp.GNTPOK(action = gmsg.info['messagetype']))

def on_growl_message(msg):
    if msg.info['messagetype'] != 'NOTIFY':
        return
    @wx.CallAfter
    def guithread():
        url = None

        toast.popup(header=msg.headers.get('notification-title', ''),
                    minor=msg.headers.get('notification-text', ''),
                    sticky = (msg.headers.get('notification-sticky', 'False') == 'True' or
                              common.pref('gntp.force_sticky', type=bool, default = False)),
                    _growlinfo=(msg.info, msg.headers, msg.resources),
                    popupid = (msg.headers.get('application-name', ''), msg.headers.get('notification-name')),
                    update = 'paged',
                    onclick=url)
