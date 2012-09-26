'''
Jabber multi-user chat (MUC)
'''

import pyxmpp.jabber.muc
from pyxmpp.message import Message
from pyxmpp.all import JID
from common import Conversation, caps
from util.observe import Observable
from util import callsback
from pprint import pformat

from logging import getLogger; log = getLogger('JabberChat')
import traceback
import jabber
from pyxmpp import presence
from .objects.nick import NICK_NS
from .objects.nick import Nick

class user_prop(object):
    def __init__(self, name):
        self.attr = name

    def __get__(self, obj, objtype=None):
        return getattr(obj.user, self.attr)

class JabberChatBuddy(Observable):
    def __init__(self, mucRoomUser, room):
        Observable.__init__(self)

        self.user = mucRoomUser
        self.room = room

    @property
    def info_key(self):
        return self.room.name + '/' + self.name + '_' + self.service

    @property
    def jid(self):
        return self.user.room_jid

    def __getattr__(self, val, default = sentinel):
        if val == 'user':
            return object.__getattribute__(self, 'user')
        try:
            return getattr(object.__getattribute__(self, 'user'), val)
        except AttributeError:
            if default is sentinel:
                return object.__getattribute__(self, val)
            else:
                try:
                    return object.__getattribute__(self, val)
                except AttributeError:
                    return default

    name = property(lambda self: self.user.nick)

    @property
    def service(self): return self.room.protocol.name

    @property
    def protocol(self): return self.room.protocol

    def idstr(self):
        return u'/'.join([self.service, self.room.name, self.name])

    def private_message_buddy(self):
        return self.protocol.get_buddy(self.user.real_jid or self.user.room_jid)

    def private_message_buddy_attr(self, attr):
        b = self.private_message_buddy()
        if b is not None:
            return getattr(b, attr)

    @property
    def alias(self):
        if self.user is self.room.room_state.me:
            try:
                return self.room.protocol.self_buddy.alias
            except Exception:
                return 'Me'
        for attr in ('nickname',):
            nick = getattr(self, attr, None)
            if nick: return unicode(nick)
        try:
            return self.room.protocol.buddies[self.user.real_jid].alias
        except Exception:
            pass
        return self.user.nick

    def __repr__(self):
        user = self.user
        return '<JabberChatBuddy %s [%s %s] (Real JID: %s)>' % \
                (user.room_jid, user.role, user.affiliation, user.real_jid or '?')

    #
    # TODO: find a way to keep this boilerplate out of individual buddy classes.
    #
    def increase_log_size(self, num_bytes):
        pass

    @property
    def icon(self):
        return self.private_message_buddy_attr('icon')

    @property
    def icon_path(self):
        return self.private_message_buddy_attr('icon_path')

    @property
    def buddy_icon(self):
        '''
        Returns a 32 pixel version of this buddy's icon (or the generic
        replacement icon for buddies without icons).
        '''

        from gui.buddylist.renderers import get_buddy_icon
        return get_buddy_icon(self, 32, False)

    history = property(lambda self: iter([]))
    status_orb = 'available'#user_prop('status_orb')
    online = True
    @property
    def serviceicon(self):
        from gui import skin
        return skin.get('serviceicons.' + self.service)

    caps = [caps.IM]
    blocked = False
    sms = False


class JabberChat(pyxmpp.jabber.muc.MucRoomHandler, Conversation):

    ischat = True
    contact_identities_known = False

    def __init__(self, protocol, jid, callback):
        pyxmpp.jabber.muc.MucRoomHandler.__init__(self)
        Conversation.__init__(self, protocol)

        self.callback = callback
        self.jid      = jid
        self.protocol.conversations[jid.as_unicode()] = self

        self.buddies    = {}

    @property
    def chat_room_name(self):
        return self.jid.as_unicode()

    @property
    def name(self):
        name = self.room_state.room_jid.bare()
        subject = self.room_state.subject

        if subject:
            return u'%s - %s' % (name, subject)
        else:
            return unicode(name)

    #
    # callbacks invoked by pyxmpp informing us of room changes
    #

    def user_joined(self, user, stanza):
        'Called when a new participant joins the room.'

        bud = self._buddy(user)
        self.room_list.append(bud)

        if user is self.room_state.me and self.callback is not None:
            self.callback, cb = None, self.callback
            cb.success(self)

        self._log_presence(bud, 'joined')
        Conversation.buddy_join(self, bud)

    def user_left(self,user,stanza):
        'Called when a participant leaves the room.'

        bud = self.buddies[user.nick]
        try:
            self.room_list.remove(bud)
        except ValueError:
            pass

        self._log_presence(bud, 'left')
        Conversation.buddy_leave(self, bud)

    def _log_presence(self, buddy, action):
        try:
            roomlist = pformat(list(self.room_list))
        except UnicodeError:
            try:
                roomlist = repr(self.room_list)
            except Exception:
                roomlist = '?'

        log.info('user %r %s:\n%s', buddy, action, roomlist)

    def nick_changed(self, user, old_nick, stanza):
        'Called after a user nick has been changed.'

        b = self._buddy(user)
        b.notify('name', old_nick, b.name) # b.name is a property -> user.nick

    def presence_changed(self,user,stanza):
        b = self._buddy(user)
        nicks = jabber.jabber_util.xpath_eval(stanza.xmlnode,
                           'n:nick',{'n':NICK_NS})
#           nicks.extend(jabber.jabber_util.xpath_eval(presence.xmlnode,
#                                       'ns:nick'))
        if nicks:
            b.nickname = Nick(nicks[0]).nick

    def affiliation_changed(self, user, old_aff, new_aff, stanza):
        'Called when a affiliation of an user has been changed.'

        self._buddy(user).notify('affiliation', old_aff, new_aff)

    def role_changed(self, user, old_role, new_role, stanza):
        'Called when a role of an user has been changed.'

        self._buddy(user).notify('role', old_role, new_role)

    def subject_changed(self, user, stanza):
        self.notify('name', None, self.room_state.subject)


    #
    # messaging
    #

    def message_received(self, user, stanza):
        if not user:
            return
        body = stanza.get_body()
        if body is not None:
            self.incoming_message(self._buddy(user), body)

    def incoming_message(self, buddy, message):
        if buddy.user == self.room_state.me: # own messages already echoed
            return

        self.typing_status[buddy] = None
        self.received_message(buddy, message)

    def room_configuration_error(self,stanza):
        self.error(stanza)

    def error(self,stanza):
        from common import fire
        #gtalk gets this from conference.jabber.org
        if not self.room_state.configured and stanza.get_from() == self.jid and\
            stanza.stanza_type == 'presence':
            err = stanza.get_error()
            cond = err.get_condition()
            if cond is not None and cond.name == 'item-not-found':
                return
        try:
            fire('error', title = self.jid, msg = stanza.get_error().get_message(), details='',
                 sticky = True, popupid = self.jid, buttons = ((_('Close'), lambda: None),), update = 'replace')
        except Exception:
            traceback.print_exc()
        if not self.room_state.joined:
            self.exit()

    @callsback
    def _send_message(self, message, callback=None):
        self.room_state.send_message(message.format_as('plaintext'))
        callback.success()

    @callsback
    def invite(self, buddy, message = None, callback = None):
        '''
        Sends an invite for this room to "buddy" (its actually a <message /> to
        the room--the room sends an invite "on your behalf").

        <message
            from='crone1@shakespeare.lit/desktop'
            to='darkcave@macbeth.shakespeare.lit'>
          <x xmlns='http://jabber.org/protocol/muc#user'>
            <invite to='hecate@shakespeare.lit'>
              <reason>
                Hey Hecate, this is the place for all good witches!
              </reason>
            </invite>
          </x>
        </message>
        '''
        room  = self

        try:    buddy = buddy.jid.as_unicode()
        except: buddy = JID(buddy).as_unicode()

        if message is None:
            message = _('You have been invited to {roomname}').format(roomname=self.jid.as_unicode())

        # Send an invitation "by way" of room
        m = Message(from_jid = room.protocol.self_buddy.jid,
                    to_jid   = room.jid)

        # <x tag>
        x = m.xmlnode.newTextChild(None, 'x', None)
        x.setNs(x.newNs('http://jabber.org/protocol/muc#user', None))

        # <invite to="buddy to invite"><reason>Plz come chat</reason></invite>
        invite = x.newTextChild(None, 'invite', None)
        invite.setProp('to', buddy)
        reason = invite.newTextChild(None, 'reason', message)

        self.protocol.send_cb(m, callback = callback)


    def send_typing_status(self, status):
        return None

    def set_subject(self, subject):
        self.room_state.set_subject(subject)

    def exit(self):
        self.room_state.leave()

        try:
            del self.protocol.conversations[self.jid.as_unicode()]
        except KeyError:
            traceback.print_exc()

        Conversation.exit(self)

    @property
    def self_buddy(self):
        return self.protocol.self_buddy


    def _buddy(self, mucuser):
        'Wraps a pyxmpp.jabber.muc.MucRoomUser in an observable JabberChatBuddy.'

        try:
            return self.buddies[mucuser.nick]
        except KeyError:
            return self.buddies.setdefault(mucuser.nick, JabberChatBuddy(mucuser, self))

