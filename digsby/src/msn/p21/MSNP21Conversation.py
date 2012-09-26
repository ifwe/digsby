import sys
import time
import datetime
import struct
import logging
import traceback
import email
import uuid

import lxml.etree as etree

import util.allow_once as once
import util.callbacks as callbacks
from util import callsback, RoundRobinProducer, strip_html, Timer
from util.primitives.funcs import get
import util.Events as Events

import common
from util.observe import ObservableDict
from common import Conversation, pref

import msn
import msn.AddressBook as MSNAB
import msn.SOAP.services as SOAPServices
from msn import NSSBAdapter, oim

import msn.P2P as P2P
import msn.P2P.P2PMessage as P2PMessage

import msn.MSNCommands as MSNC
from msn.MSNCommands import MSNTextMessage

log = logging.getLogger('msn.p21.conv')

class CircleNotReadyException(Exception):
    pass


class MSNP21Conversation(Conversation, Events.EventMixin):
    events = Events.EventMixin.events | set((
        'buddy_join',
        'buddy_leave',
        'AllContactsLeft',
        'MessageAckReceived',
        'ServerErrorReceived',
    ))
    def _repr(self):
        return ' chatbuddy=%r' % getattr(self, '_chatbuddy', None)

    def __init__(self, msn, to_invite = (), **k):
        Events.EventMixin.__init__(self)
        self.Bridge = None
        self.client = msn
        self._to_invite = set(to_invite)
        self._closed = False

        self._waschat = len(self._to_invite) > 1
        Conversation.__init__(self, msn)

        self.check_invite_list()

        self.protocol.register_conv(self)

        log.info("Added %r to msn's conversation list", self)

        self.buddies = {}
        self.typing_status = ObservableDict()

        self._pending_invite_callbacks = {}

        self.room_list.append(self.self_buddy)
        if self.ischat:
            cb = self.client.circle_buddies[self._chatbuddy]
            cb.sem.bind("resource_release", self._circle_unused)
            cb.sem.acquire()
            self.client.ns.JoinCircleConversation(self._chatbuddy)
            for bname in cb.buddy_names:
                if bname.lower().startswith(str(cb.guid).lower()):
                    continue
                self.buddy_join(bname)

    def check_invite_list(self):
        to_invite = tuple(self._to_invite)

        if len(to_invite) >= 1:
            self._chatbuddy = to_invite[0]
            if len(to_invite) == 1:
                self._chat_target_name = to_invite[0]
                cinfo = self.protocol.get_contact_info(self._chat_target_name)
                if cinfo is None:
                    self._chat_target_type = MSNAB.ClientType.ChatMember
                else:
                    self._chat_target_type = cinfo.type
            else:
                self._chat_target_name = None
                self._chat_target_type = MSNAB.ClientType.ChatMember
        else:
            self._chatbuddy = None

    @property
    def chat_room_name(self):
        if self.ischat:
            return self.name

        return None

    def connect(self):
        pass

    def connected(self):
        return self.protocol.ns is not None and self.protocol.ns.connected()

    def Disconnect(self):
        log.info('Disconnecting. unregistering %r from client (%r)', self, self.client)
        if self.Bridge is not None:
            self.event('AllContactsLeft') # Will cleanup bridge
            self.Bridge = None
            # cleanup bridge
        self.client.unregister_conv(self)

    def exit(self, force_close = False):
        log.info("%r exiting", self)
        self._closed = True

        if self.ischat and self._chat_target_type == MSNAB.IMAddressInfoType.TemporaryGroup:
            circle = self.protocol.circle_buddies[self._chatbuddy]
            circle.sem.release()
            self._chatbuddy = None
            self._chat_target_name = None
        Conversation.exit(self)
        self.Disconnect()

    def _circle_unused(self):
        log.info("Circle no longer in use. Leaving...")
        circle = self.protocol.circle_buddies[self._chatbuddy]
        circle.sem.unbind('resource_release', self._circle_unused)
        self.protocol.ns.leave_temp_circle(circle.name)

    @property
    def name(self):
        if self.ischat:
            return self.buddy.alias

        names = self._clean_list()
        count = len(names)
        aliases = [self.protocol.get_buddy(n).alias for n in names if n != self.self_buddy.name]
        if count == 2:
            who = aliases[0]
        elif count == 3:
            who = '%s and %s' % tuple(sorted(aliases))
        else:
            who = '%d people' % (count - 1)

        return who

    @property
    def chat_id(self):
        if self._chatbuddy is None:
            raise CircleNotReadyException()
        return '%s:%s' % (int(self._chat_target_type), self._chatbuddy)

    @property
    def ischat(self):
        return getattr(self, '_chat_target_type', 1) in (MSNAB.IMAddressInfoType.Circle, MSNAB.IMAddressInfoType.TemporaryGroup)

    @property
    def buddy(self):
        if self.ischat:
            return self.protocol.circle_buddies.get(self._chatbuddy)

        l = self._clean_list()

        try:
            l.remove(self.self_buddy.name)
        except ValueError:
            pass

        if len(l) == 1:
            answer = l[0]
            if isinstance(answer, basestring):
                answer = self.protocol.get_buddy(answer)
            return answer

        return self.protocol.get_buddy(self._chatbuddy)

    def _clean_list(self):
        l = set(x.name for x in self.room_list) | set(self._to_invite)

        circle = self.client.circle_buddies.get(self._chatbuddy, None)
        if circle is not None:
            l.update(circle.buddy_names)
            l.discard(circle.name)

        return list(l)

    @property
    def self_buddy(self):
        return self.protocol.self_buddy

    @callbacks.callsback
    def _send_message(self, text, callback = None, **k):
        pass

    @callbacks.callsback
    def invite(self, buddy, callback = None):
        name = getattr(buddy, 'name', buddy)
        self._pending_invite_callbacks[name] = callback

        is_new_circle = False

        def do_invites(circle_name):
            circle = self.protocol.circle_buddies[circle_name]

            if is_new_circle:
                circle.sem.bind("resource_release", self._circle_unused)
                circle.sem.acquire()

            old_name, self._chatbuddy = self._chatbuddy, circle_name
            self._chat_target_name = circle_name
            self._chat_target_type = (MSNAB.IMAddressInfoType.Circle
                                      if getattr(circle, 'circle', None) is not None
                                      else MSNAB.IMAddressInfoType.TemporaryGroup)

            if old_name != self._chatbuddy:
                self.protocol.ns.invite_to_circle(circle_name, old_name)
            self.protocol.ns.invite_to_circle(circle_name, name)

        if not self.ischat:
            is_new_circle = True
            self.protocol.ns.make_temp_circle(success = do_invites,
                                              error = callback.error)

        else:
            do_invites(self._chatbuddy)

    def on_message_recv(self, name, msg, sms = False):
        buddy = self.buddies[name] = self.protocol.get_buddy(name)
        self.typing_status[buddy] = None

        if hasattr(msg, 'html'):
            message = msg.html().replace('\n', '<br />')
            content_type = 'text/html'
        else:
            message = msg
            content_type = 'text/plain'

        did_receive = self.received_message(buddy, message, sms = sms, content_type = content_type)

        if name != self.self_buddy.name and did_receive:
            Conversation.incoming_message(self)

    def on_action_recv(self, name, action_type, action_text):
        self._stop_exit_timer()

        buddy = self.buddies[name] = self.protocol.get_buddy(name)

        if action_type == 'custom':
            if action_text is not None:
                #Translators: ex: Frank nudged you!
                message = _('{name} {action}').format(name = buddy.alias, action = action_text)
                self.system_message(message)
        else:
            text = dict(
                        wink  = _('{name} winked at you!'),
                        nudge = _('{name} nudged you!'),
                        ).get(action_type, None)
            if text is not None:
                message = text.format(name = buddy.alias)
                self.system_message(message)

    def on_typing_notification(self, name, typing):
        buddy = self.buddies[name] = self.protocol.get_buddy(name)
        self.typing_status[buddy] = 'typing' if typing else None

        log.info('%s is %styping', name, '' if typing else 'not ')

    @Events.event
    def buddy_join(self, name):
        buddy = self.buddies[name] = self.protocol.get_buddy(name)

        if buddy is not self.self_buddy and self.self_buddy not in self.room_list:
            self.on_buddy_join(self.self_buddy.name)

        if buddy not in self.room_list:
            self.room_list.append(buddy)
        if not self._chatbuddy:
            self._chatbuddy = name

        log.info('Got buddy join event (%s). self.ischat = %r', name, self.ischat)

        self.notify('ischat')
        super(MSNP21Conversation, self).buddy_join(buddy)

        self.invite_success(name)

        return name

    def invite_success(self, name):
        cb = self._pending_invite_callbacks.pop(name, None)
        if cb is not None:
            cb.success()

    def invite_failure(self, name):
        cb = self._pending_invite_callbacks.pop(name, None)
        if cb is not None:
            cb.error()

    def on_buddy_leave(self, name, notify = True):
        self._type_override = None
        buddy = self.buddies[name] = self.protocol.get_buddy(name)

        try:
            self.room_list.remove(buddy)
        except ValueError:
            log.info('Buddy %r wasn\'t in room but left anyway (?)', name)

        in_room = set(self._clean_list()) - self._to_invite
        in_room.discard(self.self_buddy.name)
        self.typing_status.pop(buddy, None)
        self.event('contacts_changed')

        super(MSNP21Conversation, self).buddy_leave(buddy)
        self.notify('ischat')

    def fed_message(self, msg):
        self.recv_msg(msg)

    def recv_msg(self, msg):
        if msg.name not in self.room_list:
            if not self.ischat:
                assert msg.name == self._chat_target_name, (msg.name, self._chat_target_name)
                self.buddy_join(msg.name)

        try:
            getattr(self, 'recv_msg_%s' % msg.type, self.recv_msg_unknown)(msg)
        except Exception, e:
            import traceback
            traceback.print_exc()

            log.error('Exception handling MSG: %r, msg = %r', e, msg)

    def recv_msg_control_typing(self, msg, typing = True):
        name = msg.name
        buddy = self.buddies[name] = self.protocol.get_buddy(name)
        self.typing_status[buddy] = 'typing' if typing else None

        log.info('%s is %styping', name, '' if typing else 'not ')

    def recv_msg_unknown(self, msg):
        log.info("Got an unknown message: %r (%r)", msg.type, str(msg))

    def recv_msg_signal_forceabchsync(self, msg):
        if msg.name == self.self_buddy.name:
            payload = msg.payload.get_payload()
            log.info("Got addressbook sync signal from a different endpoint: %r", payload)
            doc = etree.fromstring(payload)
            self.protocol.ns._sync_addressbook(abid = doc.find('.//Service').attrib.get('id', str(uuid.UUID(int = 0))),
                                               PartnerScenario = SOAPServices.PartnerScenario.ABChangeNotifyAlert)

    def recv_msg_wink(self, msg):
        self.on_action_recv(msg.name, 'wink', None)

    def recv_msg_nudge(self, msg):
        self.on_action_recv(msg.name, 'nudge', None)

    def recv_msg_text(self, msg):
        name = msg.name
        textmsg = MSNTextMessage.from_net(msg.payload)

        buddy = self.buddies[name] = self.protocol.get_buddy(name)
        self.typing_status[buddy] = None

        if hasattr(textmsg, 'html'):
            message = textmsg.html().replace('\n', '<br />')
            content_type = 'text/html'
        else:
            message = textmsg
            content_type = 'text/plain'

        service_channel = offline = msg.payload.get("Service-Channel", None)
        sms = service_channel == 'IM/Mobile'
        offline = service_channel == "IM/Offline"
        timestamp_str = msg.payload.get('Original-Arrival-Time', None)
        if timestamp_str is None:
            timestamp = None
        else:
            timestamp = datetime.datetime.fromtimestamp(SOAPServices.strptime_highres(timestamp_str))

        did_receive = self.received_message(buddy, message, sms = sms, content_type = content_type,
                                            offline = offline, timestamp = timestamp)

        if name != self.self_buddy.name and did_receive:
            Conversation.incoming_message(self)

    def send(self, *a, **k):
        return self.protocol.ns.socket.send(*a, **k)

    def message_header(self, first = None, second = None, path = 'IM', epid = None):
        if epid is not None:
            to_value = '%s;epid={%s}' % (self.chat_id, epid)
        else:
            to_value = '%s;path=%s' % (self.chat_id, path)

        message_headers = (
            (('Routing', '1.0'),
                 ('To', to_value),
                 ('From', '%d:%s;epid={%s}'  % (MSNAB.IMAddressInfoType.WindowsLive, self.self_buddy.name, str(self.client.get_machine_guid()).lower())),
              ) + (tuple(first or ())),

              (('Reliability', '1.0'),

              ) + (tuple(second or ())),
        )

        return message_headers

    def send_typing_status(self, status):
        if status != 'typing':
            return

        if not self.buddy.online:
            return

        payload = MSNC.MultiPartMime(self.message_header() +
                                ((('Messaging', '2.0'),
                                  ('Message-Type', 'Control/Typing'),),),
                                body = '')

        self.send(MSNC.SDG(payload = str(payload)), trid = True, callback = sentinel)

    @callbacks.callsback
    def send_text_message(self, body, callback = None):
        log.info("message body: %r, %r", type(body), body)
        if isinstance(body, unicode):
            body = body.encode('utf8')

        msnt = email.message_from_string(body)

        header_args = []
        if not self.buddy.online:
            header_args.append(("Service-Channel", "IM/Offline"))
        elif self.buddy.mobile and self.buddy.sms:
            header_args.append(("Service-Channel", "IM/Mobile"))

        payload = MSNC.MultiPartMime(self.message_header(header_args) +
                                ((('Messaging', '2.0'),
                                  ('Message-Type', 'Text'),
                                  ('IM-Display-Name', (self.protocol.self_buddy.remote_alias or self.protocol.self_buddy.name).encode('utf8')),
                                  ('X-MMS-IM-Format', msnt.get('X-MMS-IM-Format', 'EF=;')),
                                  ('Content-Type', msnt.get('Content-Type', 'text/plain; charset=UTF-8')),
                                 ),),
                                body = msnt.get_payload())


        self.send(MSNC.SDG(payload = str(payload)), trid = True, callback = callback)

    @callbacks.callsback
    def _send_message(self, msg, callback = None, **k):

        if not self.ischat:
            cl = set(self._clean_list())
            cl -= set([self.self_buddy.name])
            if not cl:
                callback.error()
                self.system_message('You can\'t message yourself using MSN.')
                return

        body = msg.format_as('msn')

        def check_nak(sck, emsg):
            log.error('Error sending message: %r', emsg)
            cmd = getattr(emsg, 'cmd', None)
            if cmd == 'NAK':
                self._send_message_im(msg, callback = callback)
            elif cmd == '217':
                # user was offline. use self.protocol.ns.getService('OIMService').Store(...)
                self.system_message("Offline messaging not yet supported")
            else:
                callback.error(emsg)

        self.send_text_message(body, error = check_nak)
        callback.success()

    @callbacks.callsback
    def p2p_send(self, mime_headers, data, epid = None, callback = None):
        payload = MSNC.MultiPartMime(self.message_header((('Options','0'), ('Service-Channel', 'PE')), path = 'PE', epid = epid) +
                                     (mime_headers,),
                                     body = data)
        cmd = msn.MSNCommands.SDG(payload = str(payload))

        def handle_error(sck = None, e = None):
            # if recoverable(e):
            #     callback.error()
            # else:
            #     callback.error("fatal")
            callback.error(e)

        self.send(cmd, trid = True, success = callback.success, error = handle_error)

