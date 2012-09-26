from __future__ import with_statement
import struct, logging, os.path
import oscar, common, util
S = util.Storage

from util import callsback, gen_sequence
from util.primitives.funcs import get
log = logging.getLogger('oscar.conversation'); info = log.info


class OscarConversation(common.Conversation):

    def __init__(self, o, type='im', cookie=None, roomname=None):
        common.Conversation.__init__(self, o)
        self.type = type
        self.buddies = oscar.buddies(self.protocol)
        self.self_buddy = o.self_buddy
        if self.type != 'chat':
            return

        self.sock     = None
        self.encoding = o.encoding
        self.lang     = o.lang
        self.country  = o.country

        self.cookie = cookie
        self.roomname = roomname
        self.name = 'OscarChat' + self.cookie

    @property
    def chat_room_name(self):
        return self.roomname

    def _update_chat_info(self, chat_info):
        self.roomname = chat_info.name

    def __repr__(self):
        return '<OscarConversation%s %s with %s>' % \
            ((' (chatroom %s)' % self.name) if self.ischat else '', id(self), getattr(self.buddy, 'name', '??'))

    def __contains__(self, buddy):
        bname = get(buddy, 'name', buddy)

        if bname in self.buddies:
            buddy = self.buddies[bname]

        else:
            buddy = self.buddies[bname] = self.protocol.buddies[bname]

        return buddy in self.room_list

    @property
    def ischat(self):
        return self.type == 'chat'

    @callsback
    def invite(self, buddyname, message = None, callback=None):
        if not self.ischat:
            return log.warning('this conversation is not a chat room')

        if not isinstance(buddyname, basestring):
            buddyname = buddyname.name

        log.info('%r INVITE %r', self, buddyname)

        import oscar.rendezvous.chat
        oscar.rendezvous.chat.invite(self.protocol, buddyname, self.cookie, callback=callback)

    @gen_sequence
    @callsback
    def connect_chat_socket(self, callback = None):
        'Initializes the socket for the chatroom.'

        log.info('connect_chat_socket')

        me = (yield None); assert me
        if self.cookie not in self.protocol.sockets:

            log.info('creating chat room...')
            self._create_chat_room(me())
            log.info('returned from create chat room')
            exchange, cookie, instance, detail, tlvs = (yield None)

            #if not cookie == self.cookie:
                #log.warning('cookies did not match:\nself.cookie: %r\n     cookie: %r', self.cookie, cookie)
            self.exchange = exchange
            self.cookie = cookie
            if not self.cookie.startswith('!'):
                self.cookie = '!' + self.cookie

            log.info('room created')

            self.room_info = tlvs

            log.info('requesting service...')
            self.protocol.service_request(self.cookie, me())
            self.sock = (yield None)
            log.info('...service acquired: %r', self.sock)
        else:
            self.sock = self.protocol.sockets[self.cookie]

        callback.success(self)

    @gen_sequence
    def _create_chat_room(self, parent):
        me = (yield None); assert me
        self.protocol.send_snac(*oscar.snac.x0d_x08(self.protocol, self.roomname, self.cookie),
                                req=True, cb=me.send)
        parent.send(self.protocol.gen_incoming((yield None))[-1])

    def send_snac(self, *args, **kwargs):
        self.protocol.send_snac(self.cookie, *args, **kwargs)

    @callsback
    def _send_message(self, message, callback=None, **kwargs):
        getattr(self, 'send_message_%s' %self.type, self.send_message_unknown)(message, callback=callback, **kwargs)

    def send_message_unknown(self, message, callback, **kwargs):
        log.warning('Unknown type in OscarConversation: %r. args were: %r', self.type, (message, callback, kwargs))

    def send_message_im(self, fmsg, auto=False, callback=None, **options):
        buddy = self.get_im_buddy()
        sn = buddy.name
        buddy = self.protocol.buddies[sn]

        if isinstance(sn, unicode):
            _sn, sn = sn, sn.encode('utf-8')

        if buddy.accepts_html_messages:
            log.info('buddy accepts html messages')
            html = True
            network_msg = fmsg.format_as('html')
            network_msg = network_msg.replace('\n', '<br>')
        else:
            log.info('buddy does not accept html messages. not encoding html')
            html = False
            network_msg = fmsg.format_as('plaintext')

        if self.protocol.icq and not buddy.online:
            save = True
        else:
            save = False
        # Send messages out on a higher priority than usual.
        fam, sub, data = oscar.snac.snd_channel1_message(self.protocol, sn, network_msg,
                                                         req_ack = not auto, save = save,
                                                         auto = auto, html = html)

        if auto:
            sock_callback = lambda  *a, **k: None
        else:

            def sock_callback(sock, snac):
                self._sent_msg(sock, snac, fmsg, auto, save, callback)

        self.protocol.send_snac(fam, sub, data, priority=4, req=True, cb=sock_callback)

        # echo auto messages back to the GUI - we don't ask for an ack so it will never come.
        if auto:
            callback.success()


    def _sent_msg(self, sock, snac, fmsg, auto, save, callback):
        fam = snac.hdr.fam
        sub = snac.hdr.sub

        def error():
            log.error('Bad snac in message callback: %r', (sock, snac, fmsg, auto, save))
            callback.error(snac)

        if fam != 4:
            return error()

        if sub == 1:

            errcode, = struct.unpack('!H', snac.data[:2])

            if errcode == 0x4:
                # Recipient not logged in

                if auto:
                    log.info('Could not send auto-response')
                    return
                if save:
                    log.info('Could not save message')
                    return

                log.info('Message could not be sent, trying to send again with "save" flag set.')

                sn = self.get_im_buddy().name
                # Send messages out on a higher priority than usual.
                fam, sub, data = oscar.snac.snd_channel1_message(self.protocol, sn, fmsg.format_as('html'), save=True, auto=auto)
                if self.protocol.icq:
                    self.protocol.send_snac(fam, sub, data, priority=4, req=True, cb=lambda sock,snac:None)
                    log.info("Message sent (not waiting for confirmation because account is ICQ)")

                else:
                    self.protocol.send_snac(fam, sub, data, priority=4, req=True,
                                            cb=lambda sock, snac: self._sent_msg(sock, snac, fmsg.format_as('html'), auto, True, callback))

            elif errcode == 0xA:
                # Message refused by client -- disabled offline messaging.
                log.info('Buddy does not accept offline messages. Could not send message.')
                log.info_s('\t\tBy the way, the message was: %r', fmsg)
                error()
            else:
                return error()

        elif sub == 0xC:
            log.info("Message successfully sent")
            callback.success()

        elif sub == 0xE:
            log.info('Message was incorrectly formatted! Check oscar.send_message')
            return error()

        else:
            return error()



    def send_message_dc(self, msg, callback):
        self.dc.send_message(msg.encode('utf-8'))
        self.sent_message(msg)

    def send_message_chat(self, msg, public=True, reflect=True, callback=None):
        self.send_snac(*oscar.snac.x0e_x05(self, msg.format_as('html'), public, reflect))

    def send_image(self, imgs):
        '''
        Oscar DirectIM images look like

        <HTML><BODY>
        <IMG SRC="filename.jpg" ID="1" WIDTH="40" HEIGHT="40" DATASIZE="2155">
        </BODY><HTML>
        <BINARY><DATA ID="1" SIZE="2155">GIF89..[binary data]..</DATA></BINARY>
        '''
        #TODO: move to directim.py

        if not self.type == 'dc':
            return log.warning('only direct connections can send images')

        if not isinstance(imgs, list): imgs = [imgs]

        msg, bin = '<HTML><BODY>', '<BINARY>'

        for i, img in enumerate(imgs):
            with open(img.filename, 'rb') as f: imgdata = f.read() # grab bytes
            imgname = os.path.split(img.filename)[1] # get filename part of path

            id = i + 1 # ID's start at 1.
            w, h = img.size
            size = os.path.getsize(img.filename) # size in bytes of image file

            msg += str('<IMG SRC="%s" ID="%d" WIDTH="%d" HEIGHT="%d" DATASIZE="%d">' \
                   % (imgname, id, w, h, size))
            bin += '<DATA ID="%d" SIZE="%d">' % (id, size) + imgdata + '</DATA>'

        msg += '</BODY></HTML>'
        bin += '</BINARY>'

        self.dc.send_message( [msg, bin] )

        # This message will be displayed on our own IM window.
        selfmessage = '<IMG SRC="%s">' % img.filename
        self.sent_message(selfmessage)

    def set_typing_status(self, bname, status):
        if bname not in self:
            self.buddy_join(bname)

        if bname is self.self_buddy.name:
            self.send_typing_status(status)

        self.typing_status[self.buddies[bname]] = status

    def send_typing_status(self, status=None, channel=1):
        if self.type == 'chat':
            return

        if self.type == 'im':
            bname = self.get_im_buddy().name

            if isinstance(bname, unicode):
                _bname, bname = bname, bname.encode('utf-8')

            if not self.protocol.buddies[bname].online or self.protocol.buddies[bname].isbot:
                return

            self.protocol.send_snac(*oscar.snac.x04_x14(status=status,
                                                        bname=bname,
                                                        channel=channel))
        if self.type == 'dc':
            self.dc.send_typing(status)

    def get_im_buddy(self):
        others = [b for b in self.room_list if b.name
                  != self.self_buddy.name]

        if others: return others[0]
        else:      return self.self_buddy

    def incoming(self, sock, snac):
        assert self.type == 'chat' and sock is self.sock
        f = getattr(oscar.snac, 'x%02x_x%02x' % (snac.hdr.fam, snac.hdr.sub), None)
        if f is None:
            log.warning('%r got an unknown snac: %r', self, snac)
        else:
            f(self, sock, snac.data)

    def buddy_join(self, buddy):
        if isinstance(buddy, basestring):
            buddy = self.protocol.buddies[buddy]
        assert isinstance(buddy, oscar.buddy)

        if not self.ischat and buddy not in self and len(self.room_list) >= 2:
            self.system_message(buddy.name + ' joined the room')

        self.buddies[buddy.name] = self.protocol.buddies[buddy.name]

        if buddy is self.protocol.self_buddy:
            self.self_buddy = buddy

        self.typing_status[buddy] = None
        self.update_list()

        super(OscarConversation, self).buddy_join(buddy)

    def buddy_leave(self, buddy):
        self.buddies.pop(buddy.name.lower().replace(' ',''))
        self.typing_status.pop(buddy)
        self.update_list()

        if not self.ischat and buddy is not self.self_buddy:
            self.system_message(buddy.name + ' left the room')

        super(OscarConversation, self).buddy_leave(buddy)

    def incoming_message(self, bname, msg, auto = False, offline = False, timestamp = None, **opts):
        assert bname in self

        if not isinstance(msg, unicode):
            log.warning('incoming_message: msg is not unicode, trying a last resort .decode(replace)')
            msg = msg.decode('utf-8', 'replace')

        if self.protocol.icq:
            msg = msg.replace('\n', '<br />')

        # AIM's iPhone client sends "<div>message</div>"
        if msg[:5] == '<div>' and msg[-6:] == '</div>':
            msg = msg[5:-6]

        b = self.buddies[bname]

        did_receive = self.received_message(b, msg, sms = bname.startswith('+'),
                              auto = auto, offline = offline, timestamp = timestamp, **opts)

        if b in self.typing_status:
            self.typing_status[b] = None

        if b is self.protocol.buddies['aolsystemmsg']:
            # Regardless of all other conditions, this one makes sure we won't respond to aolsytsemmsg
            autoresp = False
        else:
            # this flag does not mean auto response will happen, just that it is allowed
            autoresp = True
        if did_receive:
            common.Conversation.incoming_message(self, autoresp)

    def update_list(self):
        self.room_list[:] = sorted(self.buddies.values())

    def get_name(self):
        if self.ischat:
            return self._room_name
        else:
            if self.room_list and len(self.room_list) < 3:
                buddy = self.get_im_buddy()
                name = buddy.alias
                status = self.typing_status.get(buddy, None)
                if status: name += ' (%s)' % status
                return name
            else:
                return self._room_name

    def set_name(self, new_name):
        self._room_name = new_name

    name = property (get_name, set_name)

    _did_exit = False
    def exit(self):
        if self._did_exit:
            return
        self._did_exit = True

        self.buddy_leave(self.self_buddy)
        self.maybe_send_typing_status(None)

        if self.type == 'dc':
            # If this conversation window had a direct IM connection, then
            # close it.
            self.dc.disconnect()

        self.protocol.exit_conversation(self)
        common.Conversation.exit(self)
