#__LICENSE_GOES_HERE__

from util.packable import Packable
from util.primitives.error_handling import traceguard
from util.primitives import Storage
from gui.toast import popup
from threading import Thread, currentThread
from peak.util.addons import AddOn
from logging import getLogger; log = getLogger('growl')

GROWL_UDP_PORT = 9887
GROWL_TYPE_REGISTRATION = 0 # The packet type of registration packets with MD5 authentication.
GROWL_PREF = 'growl.popups'

def on_packet(packet):
    import wx
    @wx.CallAfter
    def guithread():
        url = None

        extra = getattr(packet, 'extra', None)
        if extra:
            url = extra.get('url', None)

        popup(header=packet.title,
              minor=packet.description,
              onclick=url)

class GrowlAddon(AddOn):
    _server_thread = None

    def __init__(self, subject):
        self.profile = subject

    did_setup = False
    def setup(self):
        if self.did_setup:
            return
        self.did_setup = True

        self.profile.prefs.add_observer(self.on_pref_change, GROWL_PREF)
        self.on_pref_change()

    def on_pref_change(self, *a):
        enabled = self.profile.prefs.get(GROWL_PREF, False)
        if enabled:
            self.start_server_thread()
        else:
            self.stop_server_thread()

    def _server_thread_running(self):
        return self._server_thread is not None and self._server_thread.is_alive()

    def start_server_thread(self):
        if not self._server_thread_running():
            self._server_thread = thread = Thread(target=_udp_server_loop)
            thread.daemon = True
            thread.start()

    def stop_server_thread(self):
        if self._server_thread_running():
            self._server_thread.die_please = True
            self._server_thread = None

class GrowlPacketHeader(Packable):
    fmt = ('protocol_version', 'B',
           'type_notification', 'B',
           'flags', 'H',
           'len_notification', 'H',
           'len_title', 'H',
           'len_description', 'H',
           'len_appname', 'H')

def unpack_packet(data):
    packet_header, data = GrowlPacketHeader.unpack(data)
    packet = Storage(extra=Storage())

    for attr in ('notification', 'title', 'description', 'appname'):
        value, data = readstring(data, getattr(packet_header, 'len_' + attr))
        packet[attr] = value

    #md5, data = data[:16], data[16:]

    if packet.description.find('\0') != -1:
        packet.description, extra = packet.description.split('\0')

        import simplejson
        packet.extra = simplejson.loads(extra)

    return packet, data


def readstring(d, slen):
    return d[:slen], d[slen:]

def _udp_server_loop():
    import socket
    s = socket.socket(2, 2)
    
    try:
        s.bind(('', GROWL_UDP_PORT))
    except socket.error:
        log.error('cannot initialize growl server loop: could not bind to port %r', GROWL_UDP_PORT)
        return
    
    while not getattr(currentThread(), 'die_please', False):
        with traceguard:
            try:
                data, addr = s.recvfrom(1024 * 10)
            except socket.timeout:
                continue

            if data[0] != chr(1):
                # print 'first byte was not 1: %r %s', (data[0], ord(data[0]))
                continue
            if data[1] == chr(GROWL_TYPE_REGISTRATION):
                # print 'ignoring registration packet'
                continue

            packet, data = unpack_packet(data)
            # assert not data

            on_packet(packet)

_server_thread = None

