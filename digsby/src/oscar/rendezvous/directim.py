'''
Messaging and photo sharing over Oscar direct connections.
'''

from __future__ import with_statement
from util import strlist, lookup_table, bitflags_enabled, myip, callsback
from util.packable import Packable
from oscar.rendezvous.peer import OscarPeer
from oscar.rendezvous.rendezvous import rendezvous_tlvs
from oscar.OscarUtil import tlv_list
import oscar, common, time, struct
from logging import getLogger; log = getLogger('oscar.rdv.directim'); info=log.info
import os.path, wx
from util.BeautifulSoup import BeautifulSoup
from functools import partial
from oscar import OscarException

from common.Protocol import StateMixin

import hooks

def directconnect(protocol, screenname):
    '''
    Requests a direct connect connection.

    Returns the DirectIM object.
    '''

    if not isinstance(screenname, str): raise TypeError('screenname must be a str')

    # Make sure the buddy isn't yourself
    ostrip = lambda s: s.lower().replace(' ','')
    if ostrip(screenname) == ostrip(protocol.self_buddy.name):
        raise OscarException("You cannot direct connect with yourself.")

    cookie = int(time.time()**2) #TODO: there's a very small chance this will suck
    protocol.rdv_sessions[cookie] = dim = OscarDirectIM(protocol, screenname, cookie)
    dim.request()

    return dim

class ODCHeader(Packable):
    '''
    Sent over direct IM connections for text messages, typing notifications,
    and photos.
    '''

    # All DirectIM communication is preceded by these headers:

    fmt = strlist('''
        version    4s      # always ODC2
        hdrlen     H       # length of header
        one        H       # 1
        six        H       # 6
        zero       H       # 0
        cookie     Q       # sixteen byte rendezvous cookie
        null       Q
        length     I
        encoding   H
        subset     H
        flags      I
        zero       I
        screenname 16s
        null2      16s ''')

    @classmethod
    def make(cls, *a, **k):
        'Makes a packable with default values filled in.'

        k.update(dict(version = 'ODC2', static = 76, one = 1, six = 6, zero = 0,
                      null = 0, null2 = '\0'*16))
        return cls(*a, **k)

    # for the "flags" field above.
    bitflags = lookup_table({
        0x01: 'autoresponse',
        0x02: 'typingpacket',            # has typing info
        0x04: 'typed',
        0x08: 'typing',
        0x20: 'confirmation',
        0x40: 'mac_confirmation',
    })

    invars = [lambda o: o.version == 'ODC2',]

class OscarDirectIM( OscarPeer, StateMixin ):

    class Statuses:
        DISCONNECTED = 'Disconnected'
        CONNECTING = 'Connecting'
        ERROR = 'Error'
        CONNECTED = 'Connected'
        OFFLINE = DISCONNECTED

    class Reasons:
        NONE = 'None'

    def __init__(self, protocol, screenname, cookie):
        StateMixin.__init__(self, self.Statuses.CONNECTING)
        direct_im_cap = oscar.capabilities.by_name['direct_im']
        OscarPeer.__init__(self, protocol, screenname, cookie, direct_im_cap)
        self.buddy = protocol.buddies[screenname]


    def accept(self):
        info('%r accepted', self)
        self.establish_dc()

    def handle_request(self, rendtlvs):
        'Logic for incoming direct connect requests.'

        #
        # until DirectIM is fully implemented...
        #
        # self.protocol.hub.on_direct_connect(self)
        #
        self.send_rdv('cancel')

    def setup_convo(self):
        # Set the buddy's conversation to a Direct Connect convo
        self.convo = self.protocol.convo_for(self.screenname)
        self.convo.setnotifyif('type', 'dc')
        self.convo.dc = self
        self.change_state(self.Statuses.CONNECTED)

    def on_odc_connection(self):
        self.socket.receive_next( ODCHeader, self.odc_header_received )
        self.setup_convo()

        # Rendezvous ACCEPT, and a confirmation ODC message.
        self.send_odc(flags = 0x60)

    def odc_header_received(self, data):
        packet, data = ODCHeader.unpack(data)
        flags = bitflags_enabled(ODCHeader.bitflags, packet.flags)
        info('incoming ODC header - enabled flags: %s', ', '.join(flags))

        # Set typing status flags in the conversation if typing notification
        # bitflags are set.
        typeset = partial(self.convo.set_typing_status, self.screenname)
        if 'typingpacket' in flags:
            if 'typing' in flags:  typeset('typing')
            elif 'typed' in flags: typeset('typed')
            else: typeset(None)

        next = self.socket.receive_next
        leftover = packet.hdrlen - ODCHeader._struct.size
        if leftover:
            # There are extra padding bytes after the header, read those first.
            next( leftover, self.read_leftover(packet.length) )
        elif packet.length > 0:
            # There is a message body to receive.
            next( packet.length, self.odc_body_received )
        else:
            # Otherwise, prepare for the next header.
            next( ODCHeader, self.odc_header_received )

    def read_leftover(self, paklen):
        info('read %d leftover bytes', paklen)
        next = self.socket.receive_next
        def callback(data):
            if paklen > 0: next( paklen, self.odc_body_received )
            else:          next( ODCHeader, self.odc_header_received )
        return callback

    def odc_body_received(self, data):
        info('odc_body_received')

        # Get a place to store the images.
        import stdpaths
        assetdir = stdpaths.userdata

        # Did the message include an inline image?
        if '<BINARY>' in data:
            j = data.find('<BINARY>')

            # Parse the HTML _before_ <BINARY>
            soup = BeautifulSoup(data[:j])
            for img in soup.html.body('img'):    # may have more than one <img>

                # For each <IMG> tag
                imgdata = data[j:]
                findme = ' ID="%s" SIZE="%s">' % (str(img['id']), str(img['datasize']))
                i = imgdata.find(findme)
                imgbytes = imgdata[i + len(findme):int(img['datasize'])+33]

                # os.path.split the img src, because some clients send their
                # full paths. (file:///c:/blah.jpg)
                imgpath = os.path.join(assetdir, os.path.split(img['src'])[1])

                img['src'] = imgpath
                del img['width']; del img['height']

                with open(imgpath, 'wb') as f: f.write(imgbytes)

            msg = unicode(soup.html)
        else:
            msg = data

        self.convo.incoming_message(self.screenname, msg)
        self.socket.receive_next( ODCHeader, self.odc_header_received )

    def send_odc(self, data = '', flags = 0):
        bname = self.protocol.self_buddy.name

        # Create an ODC header with our cookie and (buddy's) screenname
        packet = ODCHeader.make(cookie = self.cookie, screenname = bname)
        packet.flags = flags
        if isinstance(data, list):
            packet.length = sum(len(d) for d in data)
            info('send_odc got a list, summed length is %d', packet.length)
        else:
            packet.length = len(data)
            info('send_odc got a string, length is %d', packet.length)
        packet.hdrlen = len(packet)

        info('sending ODC header to screenname %s (%d bytes of %r)',
              bname, len(packet), str(type(packet)))

        if isinstance(data, list):
            self.socket.push( packet.pack() + ''.join(data) )
        else:
            self.socket.push( packet.pack() + data )

    def send_typing(self, status):
        '''
        status must be 'typing', 'typed', or None
        '''

        flag = {'typing':0x8,
                'typed' :0x4,
                None    :0x0}[status]

        self.send_odc(flags=0x2 | flag)

    def request(self):
        self.establish_out_dc()

    def ch2accept(self, data):
        info('incoming dIM got channel 2 accept')

    def send_message(self, message):
        self.send_odc(message)

    def decline(self):
        self.send_rdv('cancel')

    def ch2cancel(self, data):
        info('%r cancelled', self)
        if hasattr(self, 'convo'):
            self.convo.setnotifyif('type', 'im')
        self.change_state(self.Statuses.DISCONNECTED)

    def disconnect(self):
        'DirectIMSocket will invoke this method when the socket is closed.'

        self.socket.close()
        del self.convo.dc
        self.convo.setnotifyif('type', 'im')
        self.change_state(self.Statuses.DISCONNECTED)

    def __repr__(self):
        return '<OscarDirectIM with %s>' % self.screenname

def initialize():
    log.info('\tloading rendezvous handler: direct IM')
    import oscar.rendezvous.peer as peer
    peer.register_rdv_factory('direct_im', OscarDirectIM)

hooks.Hook('oscar.rdv.load').register(initialize)
