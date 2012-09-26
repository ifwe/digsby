#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""Jabber Multi-User Chat implementation.

Normative reference:
  - `JEP 45 <http://www.jabber.org/jeps/jep-0045.html>`__
"""

__revision__="$Id: muc.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import logging

from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.iq import Iq
from pyxmpp.jid import JID

from pyxmpp.xmlextra import xml_element_ns_iter

from pyxmpp.jabber.muccore import MucPresence,MucUserX,MucItem,MucStatus
from pyxmpp.jabber.muccore import MUC_OWNER_NS

from pyxmpp.jabber.dataforms import DATAFORM_NS, Form

import weakref

class MucRoomHandler:
    """
    Base class for MUC room handlers.

    Methods of this class will be called for various events in the room.

    :Ivariables:
      - `room_state`: MucRoomState object describing room state and its
        participants.

    """
    def __init__(self):
        """Initialize a `MucRoomHandler` object."""
        self.room_state=None
        self.__logger=logging.getLogger("pyxmpp.jabber.MucRoomHandler")

    def assign_state(self,state_obj):
        """Assign a state object to this `MucRoomHandler` instance.

        :Parameters:
            - `state_obj`: the state object.
        :Types:
            - `state_obj`: `MucRoomState`"""
        self.room_state=state_obj

    def room_created(self, stanza):
        """
        Called when the room has been created.

        Default action is to request an "instant room" by accepting the default
        configuration. Instead the application may want to request a
        configuration form and submit it.

        :Parameters:
            - `stanza`: the stanza received.

        :Types:
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        _unused = stanza
        self.room_state.request_instant_room()

    def configuration_form_received(self,form):
        """
        Called when a requested configuration form is received.

        The form, after filling-in shoul be passed to `self.room_state.configure_room`.

        :Parameters:
            - `form`: the configuration form.

        :Types:
            - `form`: `pyxmpp.jabber.dataforms.Form`
        """
        pass

    def room_configured(self):
        """
        Called after a successfull room configuration.
        """
        pass

    def user_joined(self,user,stanza):
        """
        Called when a new participant joins the room.

        :Parameters:
            - `user`: the user joining.
            - `stanza`: the stanza received.

        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def user_left(self,user,stanza):
        """
        Called when a participant leaves the room.

        :Parameters:
            - `user`: the user leaving.
            - `stanza`: the stanza received.

        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def role_changed(self,user,old_role,new_role,stanza):
        """
        Called when a role of an user has been changed.

        :Parameters:
            - `user`: the user (after update).
            - `old_role`: user's role before update.
            - `new_role`: user's role after update.
            - `stanza`: the stanza received.

        :Types:
            - `user`: `MucRoomUser`
            - `old_role`: `unicode`
            - `new_role`: `unicode`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def affiliation_changed(self,user,old_aff,new_aff,stanza):
        """
        Called when a affiliation of an user has been changed.

        `user` MucRoomUser object describing the user (after update).
        `old_aff` is user's affiliation before update.
        `new_aff` is user's affiliation after update.
        `stanza` the stanza received.
        """
        pass

    def nick_change(self,user,new_nick,stanza):
        """
        Called when user nick change is started.

        :Parameters:
            - `user`: the user (before update).
            - `new_nick`: the new nick.
            - `stanza`: the stanza received.

        :Types:
            - `user`: `MucRoomUser`
            - `new_nick`: `unicode`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def nick_changed(self,user,old_nick,stanza):
        """
        Called after a user nick has been changed.

        :Parameters:
            - `user`: the user (after update).
            - `old_nick`: the old nick.
            - `stanza`: the stanza received.

        :Types:
            - `user`: `MucRoomUser`
            - `old_nick`: `unicode`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def presence_changed(self,user,stanza):
        """
        Called whenever user's presence changes (includes nick, role or
        affiliation changes).

        :Parameters:
            - `user`: MucRoomUser object describing the user.
            - `stanza`: the stanza received.

        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def subject_changed(self,user,stanza):
        """
        Called when the room subject has been changed.

        :Parameters:
            - `user`: the user changing the subject.
            - `stanza`: the stanza used to change the subject.

        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def message_received(self,user,stanza):
        """
        Called when groupchat message has been received.

        :Parameters:
            - `user`: the sender.
            - `stanza`: is the message stanza received.

        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def room_configuration_error(self,stanza):
        """
        Called when an error stanza is received in reply to a room
        configuration request.

        By default `self.error` is called.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        self.error(stanza)

    def error(self,stanza):
        """
        Called when an error stanza is received.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        err=stanza.get_error()
        self.__logger.debug("Error from: %r Condition: %r"
                % (stanza.get_from(),err.get_condition))

class MucRoomUser:
    """
    Describes a user of a MUC room.

    The attributes of this object should not be changed directly.

    :Ivariables:
        - `presence`: last presence stanza received for the user.
        - `role`: user's role.
        - `affiliation`: user's affiliation.
        - `room_jid`: user's room jid.
        - `real_jid`: user's real jid or None if not available.
        - `nick`: user's nick (resource part of `room_jid`)
    :Types:
        - `presence`: `MucPresence`
        - `role`: `str`
        - `affiliation`: `str`
        - `room_jid`: `JID`
        - `real_jid`: `JID`
        - `nick`: `unicode`
    """
    def __init__(self,presence_or_user_or_jid):
        """
        Initialize a `MucRoomUser` object.

        :Parameters:
            - `presence_or_user_or_jid`: a MUC presence stanza with user
              information, a user object to copy or a room JID of a user.
        :Types:
            - `presence_or_user_or_jid`: `MucPresence` or `MucRoomUser` or
              `JID`

        When `presence_or_user_or_jid` is a JID user's
        role and affiliation are set to "none".
        """
        if isinstance(presence_or_user_or_jid,MucRoomUser):
            self.presence=presence_or_user_or_jid.presence
            self.role=presence_or_user_or_jid.role
            self.affiliation=presence_or_user_or_jid.affiliation
            self.room_jid=presence_or_user_or_jid.room_jid
            self.real_jid=presence_or_user_or_jid.real_jid
            self.nick=presence_or_user_or_jid.nick
            self.new_nick=None
        else:
            self.affiliation="none"
            self.presence=None
            self.real_jid=None
            self.new_nick=None
            if isinstance(presence_or_user_or_jid,JID):
                self.nick=presence_or_user_or_jid.resource
                self.room_jid=presence_or_user_or_jid
                self.role="none"
            elif isinstance(presence_or_user_or_jid,Presence):
                self.nick=None
                self.room_jid=None
                self.role="participant"
                self.update_presence(presence_or_user_or_jid)
            else:
                raise TypeError,"Bad argument type for MucRoomUser constructor"

    def update_presence(self,presence):
        """
        Update user information.

        :Parameters:
            - `presence`: a presence stanza with user information update.
        :Types:
            - `presence`: `MucPresence`
        """
        self.presence=MucPresence(presence)
        t=presence.get_type()
        if t=="unavailable":
            self.role="none"
            self.affiliation="none"
        self.room_jid=self.presence.get_from()
        self.nick=self.room_jid.resource
        mc=self.presence.get_muc_child()
        if isinstance(mc,MucUserX):
            items=mc.get_items()
            for item in items:
                if not isinstance(item,MucItem):
                    continue
                if item.role:
                    self.role=item.role
                if item.affiliation:
                    self.affiliation=item.affiliation
                if item.jid:
                    self.real_jid=item.jid
                if item.nick:
                    self.new_nick=item.nick
                break

    def same_as(self,other):
        """Check if two `MucRoomUser` objects describe the same user in the
        same room.

        :Parameters:
            - `other`: the user object to compare `self` with.
        :Types:
            - `other`: `MucRoomUser`

        :return: `True` if the two object describe the same user.
        :returntype: `bool`"""
        return self.room_jid==other.room_jid

class MucRoomState:
    """
    Describes the state of a MUC room, handles room events
    and provides an interface for room actions.

    :Ivariables:
        - `own_jid`: real jid of the owner (client using this class).
        - `room_jid`: room jid of the owner.
        - `handler`: MucRoomHandler object containing callbacks to be called.
        - `manager`: MucRoomManager object managing this room.
        - `joined`: True if the channel is joined.
        - `subject`: current subject of the room.
        - `users`: dictionary of users in the room. Nicknames are the keys.
        - `me`: MucRoomUser instance of the owner.
        - `configured`: `False` if the room requires configuration.
    """
    def __init__(self,manager,own_jid,room_jid,handler):
        """
        Initialize a `MucRoomState` object.

        :Parameters:
            - `manager`: an object to manage this room.
            - `own_jid`: real JID of the owner (client using this class).
            - `room_jid`: room JID of the owner (provides the room name and
              the nickname).
            - `handler`: an object to handle room events.
        :Types:
            - `manager`: `MucRoomManager`
            - `own_jid`: JID
            - `room_jid`: JID
            - `handler`: `MucRoomHandler`
        """
        self.own_jid=own_jid
        self.room_jid=room_jid
        self.handler=handler
        self.manager=weakref.proxy(manager)
        self.joined=False
        self.subject=None
        self.users={}
        self.me=MucRoomUser(room_jid)
        self.configured = None
        self.configuration_form = None
        handler.assign_state(self)
        self.__logger=logging.getLogger("pyxmpp.jabber.MucRoomState")

    def get_user(self,nick_or_jid,create=False):
        """
        Get a room user with given nick or JID.

        :Parameters:
            - `nick_or_jid`: the nickname or room JID of the user requested.
            - `create`: if `True` and `nick_or_jid` is a JID, then a new
              user object will be created if there is no such user in the room.
        :Types:
            - `nick_or_jid`: `unicode` or `JID`
            - `create`: `bool`

        :return: the named user or `None`
        :returntype: `MucRoomUser`
        """
        if isinstance(nick_or_jid,JID):
            if not nick_or_jid.resource:
                return None
            for u in self.users.values():
                if nick_or_jid in (u.room_jid,u.real_jid):
                    return u
            if create:
                return MucRoomUser(nick_or_jid)
            else:
                return None
        return self.users.get(nick_or_jid)

    def set_stream(self,stream):
        """
        Called when current stream changes.

        Mark the room not joined and inform `self.handler` that it was left.

        :Parameters:
            - `stream`: the new stream.
        :Types:
            - `stream`: `pyxmpp.stream.Stream`
        """
        _unused = stream
        if self.joined and self.handler:
            self.handler.user_left(self.me,None)
        self.joined=False

    def join(self, password=None, history_maxchars = None,
            history_maxstanzas = None, history_seconds = None, history_since = None):
        """
        Send a join request for the room.

        :Parameters:
            - `password`: password to the room.
            - `history_maxchars`: limit of the total number of characters in
              history.
            - `history_maxstanzas`: limit of the total number of messages in
              history.
            - `history_seconds`: send only messages received in the last
              `history_seconds` seconds.
            - `history_since`: Send only the messages received since the
              dateTime specified (UTC).
        :Types:
            - `password`: `unicode`
            - `history_maxchars`: `int`
            - `history_maxstanzas`: `int`
            - `history_seconds`: `int`
            - `history_since`: `datetime.datetime`
        """
        if self.joined:
            raise RuntimeError,"Room is already joined"
        p=MucPresence(to_jid=self.room_jid)
        p.make_join_request(password, history_maxchars, history_maxstanzas,
                history_seconds, history_since)
        self.manager.stream.send(p)

    def leave(self):
        """
        Send a leave request for the room.
        """
        if self.joined:
            p=MucPresence(to_jid=self.room_jid,stanza_type="unavailable")
            self.manager.stream.send(p)

    def send_message(self,body):
        """
        Send a message to the room.

        :Parameters:
            - `body`: the message body.
        :Types:
            - `body`: `unicode`
        """
        m=Message(to_jid=self.room_jid.bare(),stanza_type="groupchat",body=body)
        self.manager.stream.send(m)

    def set_subject(self,subject):
        """
        Send a subject change request to the room.

        :Parameters:
            - `subject`: the new subject.
        :Types:
            - `subject`: `unicode`
        """
        m=Message(to_jid=self.room_jid.bare(),stanza_type="groupchat",subject=subject)
        self.manager.stream.send(m)

    def change_nick(self,new_nick):
        """
        Send a nick change request to the room.

        :Parameters:
            - `new_nick`: the new nickname requested.
        :Types:
            - `new_nick`: `unicode`
        """
        new_room_jid=JID(self.room_jid.node,self.room_jid.domain,new_nick)
        p=Presence(to_jid=new_room_jid)
        self.manager.stream.send(p)

    def get_room_jid(self,nick=None):
        """
        Get own room JID or a room JID for given `nick`.

        :Parameters:
            - `nick`: a nick for which the room JID is requested.
        :Types:
            - `nick`: `unicode`

        :return: the room JID.
        :returntype: `JID`
        """
        if nick is None:
            return self.room_jid
        return JID(self.room_jid.node,self.room_jid.domain,nick)

    def get_nick(self):
        """
        Get own nick.

        :return: own nick.
        :returntype: `unicode`
        """
        return self.room_jid.resource

    def process_available_presence(self,stanza):
        """
        Process <presence/> received from the room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `MucPresence`
        """
        fr=stanza.get_from()
        if not fr.resource:
            return
        nick=fr.resource
        user=self.users.get(nick)
        if user:
            old_user=MucRoomUser(user)
            user.update_presence(stanza)
            user.nick=nick
        else:
            old_user=None
            user=MucRoomUser(stanza)
            self.users[user.nick]=user
        self.handler.presence_changed(user,stanza)
        if fr==self.room_jid and not self.joined:
            self.joined=True
            self.me=user
            mc=stanza.get_muc_child()
            if isinstance(mc,MucUserX):
                status = [i for i in mc.get_items() if isinstance(i,MucStatus) and i.code==201]
                if status:
                    self.configured = False
                    self.handler.room_created(stanza)
            if self.configured is None:
                self.configured = True
        if not old_user or old_user.role=="none":
            self.handler.user_joined(user,stanza)
        else:
            if old_user.nick!=user.nick:
                self.handler.nick_changed(user,old_user.nick,stanza)
                if old_user.room_jid==self.room_jid:
                    self.room_jid=fr
            if old_user.role!=user.role:
                self.handler.role_changed(user,old_user.role,user.role,stanza)
            if old_user.affiliation!=user.affiliation:
                self.handler.affiliation_changed(user,old_user.affiliation,user.affiliation,stanza)

    def process_unavailable_presence(self,stanza):
        """
        Process <presence type="unavailable"/> received from the room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `MucPresence`
        """
        fr=stanza.get_from()
        if not fr.resource:
            return
        nick=fr.resource
        user=self.users.get(nick)
        if user:
            old_user=MucRoomUser(user)
            user.update_presence(stanza)
            self.handler.presence_changed(user,stanza)
            if user.new_nick:
                mc=stanza.get_muc_child()
                if isinstance(mc,MucUserX):
                    renames=[i for i in mc.get_items() if isinstance(i,MucStatus) and i.code==303]
                    if renames:
                        self.users[user.new_nick]=user
                        del self.users[nick]
                        return
        else:
            old_user=None
            user=MucRoomUser(stanza)
            self.users[user.nick]=user
            self.handler.presence_changed(user,stanza)
        if fr==self.room_jid and self.joined:
            self.joined=False
            self.handler.user_left(user,stanza)
            self.manager.forget(self)
            self.me=user
        elif old_user:
            self.handler.user_left(user,stanza)
        # TODO: kicks

    def process_groupchat_message(self,stanza):
        """
        Process <message type="groupchat"/> received from the room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Message`
        """
        fr=stanza.get_from()
        user=self.get_user(fr,True)
        s=stanza.get_subject()
        if s:
            self.subject=s
            self.handler.subject_changed(user,stanza)
        else:
            self.handler.message_received(user,stanza)

    def process_error_message(self,stanza):
        """
        Process <message type="error"/> received from the room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Message`
        """
        self.handler.error(stanza)

    def process_error_presence(self,stanza):
        """
        Process <presence type="error"/> received from the room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Presence`
        """
        self.handler.error(stanza)

    def process_configuration_form_success(self, stanza):
        """
        Process successful result of a room configuration form request.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Presence`
        """
        if stanza.get_query_ns() != MUC_OWNER_NS:
            raise ValueError, "Bad result namespace" # TODO: ProtocolError
        query = stanza.get_query()
        form = None
        for el in xml_element_ns_iter(query.children, DATAFORM_NS):
            form = Form(el)
            break
        if not form:
            raise ValueError, "No form received" # TODO: ProtocolError
        self.configuration_form = form
        self.handler.configuration_form_received(form)

    def process_configuration_form_error(self, stanza):
        """
        Process error response for a room configuration form request.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Presence`
        """
        self.handler.error(stanza)

    def request_configuration_form(self):
        """
        Request a configuration form for the room.

        When the form is received `self.handler.configuration_form_received` will be called.
        When an error response is received then `self.handler.error` will be called.

        :return: id of the request stanza.
        :returntype: `unicode`
        """
        iq = Iq(to_jid = self.room_jid.bare(), stanza_type = "get")
        iq.new_query(MUC_OWNER_NS, "query")
        self.manager.stream.set_response_handlers(
                iq, self.process_configuration_form_success, self.process_configuration_form_error)
        self.manager.stream.send(iq)
        return iq.get_id()

    def process_configuration_success(self, stanza):
        """
        Process success response for a room configuration request.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Presence`
        """
        _unused = stanza
        self.configured = True
        self.handler.room_configured()

    def process_configuration_error(self, stanza):
        """
        Process error response for a room configuration request.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Presence`
        """
        self.handler.room_configuration_error(stanza)

    def configure_room(self, form):
        """
        Configure the room using the provided data.
        Do nothing if the provided form is of type 'cancel'.

        :Parameters:
            - `form`: the configuration parameters. Should be a 'submit' form made by filling-in
              the configuration form retireved using `self.request_configuration_form` or
              a 'cancel' form.
        :Types:
            - `form`: `Form`

        :return: id of the request stanza or `None` if a 'cancel' form was provieded.
        :returntype: `unicode`
        """

        if form.type == "cancel":
            return None
        elif form.type != "submit":
            raise ValueError, "A 'submit' form required to configure a room"
        iq = Iq(to_jid = self.room_jid.bare(), stanza_type = "set")
        query = iq.new_query(MUC_OWNER_NS, "query")
        form.as_xml(query)
        self.manager.stream.set_response_handlers(
                iq, self.process_configuration_success, self.process_configuration_error)
        self.manager.stream.send(iq)
        return iq.get_id()

    def request_instant_room(self):
        """
        Request an "instant room" -- the default configuration for a MUC room.

        :return: id of the request stanza.
        :returntype: `unicode`
        """
        if self.configured:
            raise RuntimeError, "Instant room may be requested for unconfigured room only"
        form = Form("submit")
        return self.configure_room(form)

class MucRoomManager:
    """
    Manage collection of MucRoomState objects and dispatch events.

    :Ivariables:
      - `rooms`: a dictionary containing known MUC rooms. Unicode room JIDs are the
        keys.
      - `stream`: the stream associated with the room manager.

    """
    def __init__(self,stream):
        """
        Initialize a `MucRoomManager` object.

        :Parameters:
            - `stream`: a stream to be initially assigned to `self`.
        :Types:
            - `stream`: `pyxmpp.stream.Stream`
        """
        self.rooms={}
        self.stream,self.jid=(None,)*2
        self.set_stream(stream)
        self.__logger=logging.getLogger("pyxmpp.jabber.MucRoomManager")

    def set_stream(self,stream):
        """
        Change the stream assigned to `self`.

        :Parameters:
            - `stream`: the new stream to be assigned to `self`.
        :Types:
            - `stream`: `pyxmpp.stream.Stream`
        """
        self.jid=stream.me
        self.stream=stream
        for r in self.rooms.values():
            r.set_stream(stream)

    def set_handlers(self,priority=10):
        """
        Assign MUC stanza handlers to the `self.stream`.

        :Parameters:
            - `priority`: priority for the handlers.
        :Types:
            - `priority`: `int`
        """
        self.stream.set_message_handler("groupchat",self.__groupchat_message,None,priority)
        self.stream.set_message_handler("error",self.__error_message,None,priority)
        self.stream.set_presence_handler("available",self.__presence_available,None,priority)
        self.stream.set_presence_handler("unavailable",self.__presence_unavailable,None,priority)
        self.stream.set_presence_handler("error",self.__presence_error,None,priority)

    def join(self, room, nick, handler, password = None, history_maxchars = None,
            history_maxstanzas = None, history_seconds = None, history_since = None):
        """
        Create and return a new room state object and request joining
        to a MUC room.

        :Parameters:
            - `room`: the name of a room to be joined
            - `nick`: the nickname to be used in the room
            - `handler`: is an object to handle room events.
            - `password`: password for the room, if any
            - `history_maxchars`: limit of the total number of characters in
              history.
            - `history_maxstanzas`: limit of the total number of messages in
              history.
            - `history_seconds`: send only messages received in the last
              `history_seconds` seconds.
            - `history_since`: Send only the messages received since the
              dateTime specified (UTC).

        :Types:
            - `room`: `JID`
            - `nick`: `unicode`
            - `handler`: `MucRoomHandler`
            - `password`: `unicode`
            - `history_maxchars`: `int`
            - `history_maxstanzas`: `int`
            - `history_seconds`: `int`
            - `history_since`: `datetime.datetime`

        :return: the room state object created.
        :returntype: `MucRoomState`
        """

        if not room.node or room.resource:
            raise ValueError,"Invalid room JID"

        room_jid = JID(room.node, room.domain, nick)

        cur_rs = self.rooms.get(room_jid.bare().as_unicode())
        if cur_rs and cur_rs.joined:
            raise RuntimeError,"Room already joined"

        rs=MucRoomState(self, self.stream.me, room_jid, handler)
        self.rooms[room_jid.bare().as_unicode()]=rs
        rs.join(password, history_maxchars, history_maxstanzas,
            history_seconds, history_since)
        return rs

    def get_room_state(self,room):
        """Get the room state object of a room.

        :Parameters:
            - `room`: JID or the room which state is requested.
        :Types:
            - `room`: `JID`

        :return: the state object.
        :returntype: `MucRoomState`"""
        return self.rooms.get(room.bare().as_unicode())

    def forget(self,rs):
        """
        Remove a room from the list of managed rooms.

        :Parameters:
            - `rs`: the state object of the room.
        :Types:
            - `rs`: `MucRoomState`
        """
        try:
            del self.rooms[rs.room_jid.bare().as_unicode()]
        except KeyError:
            pass

    def __groupchat_message(self,stanza):
        """Process a groupchat message from a MUC room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Message`

        :return: `True` if the message was properly recognized as directed to
            one of the managed rooms, `False` otherwise.
        :returntype: `bool`"""
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            self.__logger.debug("groupchat message from unknown source")
            return False
        rs.process_groupchat_message(stanza)
        return True

    def __error_message(self,stanza):
        """Process an error message from a MUC room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Message`

        :return: `True` if the message was properly recognized as directed to
            one of the managed rooms, `False` otherwise.
        :returntype: `bool`"""
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            return False
        rs.process_error_message(stanza)
        return True

    def __presence_error(self,stanza):
        """Process an presence error from a MUC room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Presence`

        :return: `True` if the stanza was properly recognized as generated by
            one of the managed rooms, `False` otherwise.
        :returntype: `bool`"""
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            return False
        rs.process_error_presence(stanza)
        return True

    def __presence_available(self,stanza):
        """Process an available presence from a MUC room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Presence`

        :return: `True` if the stanza was properly recognized as generated by
            one of the managed rooms, `False` otherwise.
        :returntype: `bool`"""
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            return False
        rs.process_available_presence(MucPresence(stanza))
        return True

    def __presence_unavailable(self,stanza):
        """Process an unavailable presence from a MUC room.

        :Parameters:
            - `stanza`: the stanza received.
        :Types:
            - `stanza`: `Presence`

        :return: `True` if the stanza was properly recognized as generated by
            one of the managed rooms, `False` otherwise.
        :returntype: `bool`"""
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            return False
        rs.process_unavailable_presence(MucPresence(stanza))
        return True

# vi: sts=4 et sw=4
