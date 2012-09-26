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

__revision__="$Id: muccore.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.xmlextra import common_doc, common_root, common_ns, get_node_ns_uri
from pyxmpp.presence import Presence
from pyxmpp.iq import Iq
from pyxmpp.jid import JID
from pyxmpp import xmlextra
from pyxmpp.objects import StanzaPayloadWrapperObject
from pyxmpp.xmlextra import xml_element_iter

MUC_NS="http://jabber.org/protocol/muc"
MUC_USER_NS=MUC_NS+"#user"
MUC_ADMIN_NS=MUC_NS+"#admin"
MUC_OWNER_NS=MUC_NS+"#owner"

affiliations=("admin","member","none","outcast","owner")
roles=("moderator","none","participant","visitor")

class MucXBase(StanzaPayloadWrapperObject):
    """
    Base class for MUC-specific stanza payload - wrapper around
    an XML element.

    :Ivariables:
        - `xmlnode`: the wrapped XML node
    """
    element="x"
    ns=None
    def __init__(self, xmlnode=None, copy=True, parent=None):
        """
        Copy MucXBase object or create a new one, possibly
        based on or wrapping an XML node.

        :Parameters:
            - `xmlnode`: is the object to copy or an XML node to wrap.
            - `copy`: when `True` a copy of the XML node provided will be included
              in `self`, the node will be copied otherwise.
            - `parent`: parent node for the created/copied XML element.
        :Types:
            - `xmlnode`: `MucXBase` or `libxml2.xmlNode`
            - `copy`: `bool`
            - `parent`: `libxml2.xmlNode`
        """
        if self.ns==None:
            raise RuntimeError,"Pure virtual class called"
        self.xmlnode=None
        self.borrowed=False
        if isinstance(xmlnode,libxml2.xmlNode):
            if copy:
                self.xmlnode=xmlnode.docCopyNode(common_doc,1)
                common_root.addChild(self.xmlnode)
            else:
                self.xmlnode=xmlnode
                self.borrowed=True
            if copy:
                ns=xmlnode.ns()
                xmlextra.replace_ns(self.xmlnode, ns, common_ns)
        elif isinstance(xmlnode,MucXBase):
            if not copy:
                raise TypeError, "MucXBase may only be copied"
            self.xmlnode=xmlnode.xmlnode.docCopyNode(common_doc,1)
            common_root.addChild(self.xmlnode)
        elif xmlnode is not None:
            raise TypeError, "Bad MucX constructor argument"
        else:
            if parent:
                self.xmlnode=parent.newChild(None,self.element,None)
                self.borrowed=True
            else:
                self.xmlnode=common_root.newChild(None,self.element,None)
            ns=self.xmlnode.newNs(self.ns,None)
            self.xmlnode.setNs(ns)

    def __del__(self):
        if self.xmlnode:
            self.free()

    def free(self):
        """
        Unlink and free the XML node owned by `self`.
        """
        if not self.borrowed:
            self.xmlnode.unlinkNode()
            self.xmlnode.freeNode()
        self.xmlnode=None

    def free_borrowed(self):
        """
        Detach the XML node borrowed by `self`.
        """
        self.xmlnode=None

    def xpath_eval(self,expr):
        """
        Evaluate XPath expression in context of `self.xmlnode`.

        :Parameters:
            - `expr`: the XPath expression
        :Types:
            - `expr`: `unicode`

        :return: the result of the expression evaluation.
        :returntype: list of `libxml2.xmlNode`
        """
        ctxt = common_doc.xpathNewContext()
        ctxt.setContextNode(self.xmlnode)
        ctxt.xpathRegisterNs("muc",self.ns.getContent())
        ret=ctxt.xpathEval(to_utf8(expr))
        ctxt.xpathFreeContext()
        return ret

    def serialize(self):
        """
        Serialize `self` as XML.

        :return: serialized `self.xmlnode`.
        :returntype: `str`
        """
        return self.xmlnode.serialize()

class MucX(MucXBase):
    """
    Wrapper for http://www.jabber.org/protocol/muc namespaced
    stanza payload "x" elements.
    """
    ns=MUC_NS
    def __init__(self, xmlnode=None, copy=True, parent=None):
        MucXBase.__init__(self,xmlnode=xmlnode, copy=copy, parent=parent)

    def set_history(self, parameters):
        """
        Set history parameters.

        Types:
            - `parameters`: `HistoryParameters`
        """
        for child in xml_element_iter(self.xmlnode.children):
            if get_node_ns_uri(child) == MUC_NS and child.name == "history":
                child.unlinkNode()
                child.freeNode()
                break

        if parameters.maxchars and parameters.maxchars < 0:
            raise ValueError, "History parameter maxchars must be positive"
        if parameters.maxstanzas and parameters.maxstanzas < 0:
            raise ValueError, "History parameter maxstanzas must be positive"
        if parameters.maxseconds and parameters.maxseconds < 0:
            raise ValueError, "History parameter maxseconds must be positive"

        hnode=self.xmlnode.newChild(self.xmlnode.ns(), "history", None)

        if parameters.maxchars is not None:
            hnode.setProp("maxchars", str(parameters.maxchars))
        if parameters.maxstanzas is not None:
            hnode.setProp("maxstanzas", str(parameters.maxstanzas))
        if parameters.maxseconds is not None:
            hnode.setProp("maxseconds", str(parameters.maxseconds))
        if parameters.since is not None:
            hnode.setProp("since", parameters.since.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def get_history(self):
        """Return history parameters carried by the stanza.

        :returntype: `HistoryParameters`"""
        for child in xml_element_iter(self.xmlnode.children):
            if get_node_ns_uri(child) == MUC_NS and child.name == "history":
                maxchars = from_utf8(child.prop("maxchars"))
                if maxchars is not None:
                    maxchars = int(maxchars)
                maxstanzas = from_utf8(child.prop("maxstanzas"))
                if maxstanzas is not None:
                    maxstanzas = int(maxstanzas)
                maxseconds = from_utf8(child.prop("maxseconds"))
                if maxseconds is not None:
                    maxseconds = int(maxseconds)
                # TODO: since -- requires parsing of Jabber dateTime profile
                since = None
                return HistoryParameters(maxchars, maxstanzas, maxseconds, since)

    def set_password(self, password):
        """Set password for the MUC request.

        :Parameters:
            - `password`: password
        :Types:
            - `password`: `unicode`"""
        for child in xml_element_iter(self.xmlnode.children):
            if get_node_ns_uri(child) == MUC_NS and child.name == "password":
                child.unlinkNode()
                child.freeNode()
                break

        if password is not None:
            self.xmlnode.newTextChild(self.xmlnode.ns(), "password", to_utf8(password))

    def get_password(self):
        """Get password from the MUC request.

        :returntype: `unicode`
        """
        for child in xml_element_iter(self.xmlnode.children):
            if get_node_ns_uri(child) == MUC_NS and child.name == "password":
                return from_utf8(child.getContent())
        return None

class HistoryParameters(object):
    """Provides parameters for MUC history management

    :Ivariables:
        - `maxchars`: limit of the total number of characters in history.
        - `maxstanzas`: limit of the total number of messages in history.
        - `seconds`: send only messages received in the last `seconds` seconds.
        - `since`: Send only the messages received since the dateTime (UTC)
          specified.
    :Types:
        - `maxchars`: `int`
        - `maxstanzas`: `int`
        - `seconds`: `int`
        - `since`: `datetime.datetime`
    """
    def __init__(self, maxchars = None, maxstanzas = None, maxseconds = None, since = None):
        """Initializes a `HistoryParameters` object.

        :Parameters:
            - `maxchars`: limit of the total number of characters in history.
            - `maxstanzas`: limit of the total number of messages in history.
            - `maxseconds`: send only messages received in the last `seconds` seconds.
            - `since`: Send only the messages received since the dateTime specified.
        :Types:
            - `maxchars`: `int`
            - `maxstanzas`: `int`
            - `maxseconds`: `int`
            - `since`: `datetime.datetime`
        """
        self.maxchars = maxchars
        self.maxstanzas = maxstanzas
        self.maxseconds = maxseconds
        self.since = since


class MucItemBase(object):
    """
    Base class for <status/> and <item/> element wrappers.
    """
    def __init__(self):
        if self.__class__ is MucItemBase:
            raise RuntimeError,"Abstract class called"

class MucItem(MucItemBase):
    """
    MUC <item/> element -- describes a room occupant.

    :Ivariables:
        - `affiliation`: affiliation of the user.
        - `role`: role of the user.
        - `jid`: JID of the user.
        - `nick`: nickname of the user.
        - `actor`: actor modyfying the user data.
        - `reason`: reason of change of the user data.
    :Types:
        - `affiliation`: `str`
        - `role`: `str`
        - `jid`: `JID`
        - `nick`: `unicode`
        - `actor`: `JID`
        - `reason`: `unicode`
    """
    def __init__(self,xmlnode_or_affiliation,role=None,jid=None,nick=None,actor=None,reason=None):
        """
        Initialize a `MucItem` object.

        :Parameters:
            - `xmlnode_or_affiliation`: XML node to be pased or the affiliation of
              the user being described.
            - `role`: role of the user.
            - `jid`: JID of the user.
            - `nick`: nickname of the user.
            - `actor`: actor modyfying the user data.
            - `reason`: reason of change of the user data.
        :Types:
            - `xmlnode_or_affiliation`: `libxml2.xmlNode` or `str`
            - `role`: `str`
            - `jid`: `JID`
            - `nick`: `unicode`
            - `actor`: `JID`
            - `reason`: `unicode`
        """
        self.jid,self.nick,self.actor,self.affiliation,self.reason,self.role=(None,)*6
        MucItemBase.__init__(self)
        if isinstance(xmlnode_or_affiliation,libxml2.xmlNode):
            self.__from_xmlnode(xmlnode_or_affiliation)
        else:
            self.__init(xmlnode_or_affiliation,role,jid,nick,actor,reason)

    def __init(self,affiliation,role,jid=None,nick=None,actor=None,reason=None):
        """Initialize a `MucItem` object from a set of attributes.

        :Parameters:
            - `affiliation`: affiliation of the user.
            - `role`: role of the user.
            - `jid`: JID of the user.
            - `nick`: nickname of the user.
            - `actor`: actor modyfying the user data.
            - `reason`: reason of change of the user data.
        :Types:
            - `affiliation`: `str`
            - `role`: `str`
            - `jid`: `JID`
            - `nick`: `unicode`
            - `actor`: `JID`
            - `reason`: `unicode`
        """
        if not affiliation:
            affiliation=None
        elif affiliation not in affiliations:
            raise ValueError,"Bad affiliation"
        self.affiliation=affiliation
        if not role:
            role=None
        elif role not in roles:
            raise ValueError,"Bad role"
        self.role=role
        if jid:
            self.jid=JID(jid)
        else:
            self.jid=None
        if actor:
            self.actor=JID(actor)
        else:
            self.actor=None
        self.nick=nick
        self.reason=reason

    def __from_xmlnode(self, xmlnode):
        """Initialize a `MucItem` object from an XML node.

        :Parameters:
            - `xmlnode`: the XML node.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
        """
        actor=None
        reason=None
        n=xmlnode.children
        while n:
            ns=n.ns()
            if ns and ns.getContent()!=MUC_USER_NS:
                continue
            if n.name=="actor":
                actor=n.getContent()
            if n.name=="reason":
                reason=n.getContent()
            n=n.next
        self.__init(
            from_utf8(xmlnode.prop("affiliation")),
            from_utf8(xmlnode.prop("role")),
            from_utf8(xmlnode.prop("jid")),
            from_utf8(xmlnode.prop("nick")),
            from_utf8(actor),
            from_utf8(reason),
            );

    def as_xml(self,parent):
        """
        Create XML representation of `self`.

        :Parameters:
            - `parent`: the element to which the created node should be linked to.
        :Types:
            - `parent`: `libxml2.xmlNode`

        :return: an XML node.
        :returntype: `libxml2.xmlNode`
        """
        n=parent.newChild(None,"item",None)
        if self.actor:
            n.newTextChild(None,"actor",to_utf8(self.actor))
        if self.reason:
            n.newTextChild(None,"reason",to_utf8(self.reason))
        n.setProp("affiliation",to_utf8(self.affiliation))
        if self.role:
            n.setProp("role",to_utf8(self.role))
        if self.jid:
            n.setProp("jid",to_utf8(self.jid.as_unicode()))
        if self.nick:
            n.setProp("nick",to_utf8(self.nick))
        return n

class MucStatus(MucItemBase):
    """
    MUC <item/> element - describes special meaning of a stanza

    :Ivariables:
        - `code`: staus code, as defined in JEP 45
    :Types:
        - `code`: `int`
    """
    def __init__(self,xmlnode_or_code):
        """Initialize a `MucStatus` element.

        :Parameters:
            - `xmlnode_or_code`: XML node to parse or a status code.
        :Types:
            - `xmlnode_or_code`: `libxml2.xmlNode` or `int`
        """
        self.code=None
        MucItemBase.__init__(self)
        if isinstance(xmlnode_or_code,libxml2.xmlNode):
            self.__from_xmlnode(xmlnode_or_code)
        else:
            self.__init(xmlnode_or_code)

    def __init(self,code):
        """Initialize a `MucStatus` element from a status code.

        :Parameters:
            - `code`: the status code.
        :Types:
            - `code`: `int`
        """
        code=int(code)
        if code<0 or code>999:
            raise ValueError,"Bad status code"
        self.code=code

    def __from_xmlnode(self, xmlnode):
        """Initialize a `MucStatus` element from an XML node.

        :Parameters:
            - `xmlnode`: XML node to parse.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
        """
        self.code=int(xmlnode.prop("code"))

    def as_xml(self,parent):
        """
        Create XML representation of `self`.

        :Parameters:
            - `parent`: the element to which the created node should be linked to.
        :Types:
            - `parent`: `libxml2.xmlNode`

        :return: an XML node.
        :returntype: `libxml2.xmlNode`
        """
        n=parent.newChild(None,"status",None)
        n.setProp("code","%03i" % (self.code,))
        return n

class MucUserX(MucXBase):
    """
    Wrapper for http://www.jabber.org/protocol/muc#user namespaced
    stanza payload "x" elements and usually containing information
    about a room user.

    :Ivariables:
        - `xmlnode`: wrapped XML node
    :Types:
        - `xmlnode`: `libxml2.xmlNode`
    """
    ns=MUC_USER_NS
    def get_items(self):
        """Get a list of objects describing the content of `self`.

        :return: the list of objects.
        :returntype: `list` of `MucItemBase` (`MucItem` and/or `MucStatus`)
        """
        if not self.xmlnode.children:
            return []
        ret=[]
        n=self.xmlnode.children
        while n:
            ns=n.ns()
            if ns and ns.getContent()!=self.ns:
                pass
            elif n.name=="item":
                ret.append(MucItem(n))
            elif n.name=="status":
                ret.append(MucStatus(n))
            # FIXME: alt,decline,invite,password
            n=n.next
        return ret
    def clear(self):
        """
        Clear the content of `self.xmlnode` removing all <item/>, <status/>, etc.
        """
        if not self.xmlnode.children:
            return
        n=self.xmlnode.children
        while n:
            ns=n.ns()
            if ns and ns.getContent()!=MUC_USER_NS:
                pass
            else:
                n.unlinkNode()
                n.freeNode()
            n=n.next
    def add_item(self,item):
        """Add an item to `self`.

        :Parameters:
            - `item`: the item to add.
        :Types:
            - `item`: `MucItemBase`
        """
        if not isinstance(item,MucItemBase):
            raise TypeError,"Bad item type for muc#user"
        item.as_xml(self.xmlnode)

class MucOwnerX(MucXBase):
    """
    Wrapper for http://www.jabber.org/protocol/muc#owner namespaced
    stanza payload "x" elements and usually containing information
    about a room user.

    :Ivariables:
        - `xmlnode`: wrapped XML node.
    :Types:
        - `xmlnode`: `libxml2.xmlNode`
    """
    # FIXME: implement
    pass

class MucAdminQuery(MucUserX):
    """
    Wrapper for http://www.jabber.org/protocol/muc#admin namespaced
    IQ stanza payload "query" elements and usually describing
    administrative actions or their results.

    Not implemented yet.
    """
    ns=MUC_ADMIN_NS
    element="query"

class MucStanzaExt:
    """
    Base class for MUC specific stanza extensions. Used together
    with one of stanza classes (Iq, Message or Presence).
    """
    def __init__(self):
        """Initialize a `MucStanzaExt` derived object."""
        if self.__class__ is MucStanzaExt:
            raise RuntimeError,"Abstract class called"
        self.xmlnode=None
        self.muc_child=None

    def get_muc_child(self):
        """
        Get the MUC specific payload element.

        :return: the object describing the stanza payload in MUC namespace.
        :returntype: `MucX` or `MucUserX` or `MucAdminQuery` or `MucOwnerX`
        """
        if self.muc_child:
            return self.muc_child
        if not self.xmlnode.children:
            return None
        n=self.xmlnode.children
        while n:
            if n.name not in ("x","query"):
                n=n.next
                continue
            ns=n.ns()
            if not ns:
                n=n.next
                continue
            ns_uri=ns.getContent()
            if (n.name,ns_uri)==("x",MUC_NS):
                self.muc_child=MucX(n)
                return self.muc_child
            if (n.name,ns_uri)==("x",MUC_USER_NS):
                self.muc_child=MucUserX(n)
                return self.muc_child
            if (n.name,ns_uri)==("query",MUC_ADMIN_NS):
                self.muc_child=MucAdminQuery(n)
                return self.muc_child
            if (n.name,ns_uri)==("query",MUC_OWNER_NS):
                self.muc_child=MucOwnerX(n)
                return self.muc_child
            n=n.next

    def clear_muc_child(self):
        """
        Remove the MUC specific stanza payload element.
        """
        if self.muc_child:
            self.muc_child.free_borrowed()
            self.muc_child=None
        if not self.xmlnode.children:
            return
        n=self.xmlnode.children
        while n:
            if n.name not in ("x","query"):
                n=n.next
                continue
            ns=n.ns()
            if not ns:
                n=n.next
                continue
            ns_uri=ns.getContent()
            if ns_uri in (MUC_NS,MUC_USER_NS,MUC_ADMIN_NS,MUC_OWNER_NS):
                n.unlinkNode()
                n.freeNode()
            n=n.next

    def make_muc_userinfo(self):
        """
        Create <x xmlns="...muc#user"/> element in the stanza.

        :return: the element created.
        :returntype: `MucUserX`
        """
        self.clear_muc_child()
        self.muc_child=MucUserX(parent=self.xmlnode)
        return self.muc_child

    def make_muc_admin_quey(self):
        """
        Create <query xmlns="...muc#admin"/> element in the stanza.

        :return: the element created.
        :returntype: `MucAdminQuery`
        """
        self.clear_muc_child()
        self.muc_child=MucAdminQuery(parent=self.xmlnode)
        return self.muc_child

    def muc_free(self):
        """
        Free MUC specific data.
        """
        if self.muc_child:
            self.muc_child.free_borrowed()

class MucPresence(Presence,MucStanzaExt):
    """
    Extend `Presence` with MUC related interface.
    """
    def __init__(self, xmlnode=None,from_jid=None,to_jid=None,stanza_type=None,stanza_id=None,
            show=None,status=None,priority=0,error=None,error_cond=None):
        """Initialize a `MucPresence` object.

        :Parameters:
            - `xmlnode`: XML node to_jid be wrapped into the `MucPresence` object
              or other Presence object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: None, "available", "unavailable",
              "subscribe", "subscribed", "unsubscribe", "unsubscribed" or
              "error". "available" is automaticaly changed to_jid None.
            - `stanza_id`: stanza id -- value of stanza's "id" attribute
            - `show`: "show" field of presence stanza. One of: None, "away",
              "xa", "dnd", "chat".
            - `status`: descriptive text for the presence stanza.
            - `priority`: presence priority.
            - `error_cond`: error condition name. Ignored if `stanza_type` is not "error"
        :Types:
            - `xmlnode`: `unicode` or `libxml2.xmlNode` or `pyxmpp.stanza.Stanza`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `show`: `unicode`
            - `status`: `unicode`
            - `priority`: `unicode`
            - `error_cond`: `unicode`"""
        MucStanzaExt.__init__(self)
        Presence.__init__(self,xmlnode,from_jid=from_jid,to_jid=to_jid,
                stanza_type=stanza_type,stanza_id=stanza_id,
                show=show,status=status,priority=priority,
                error=error,error_cond=error_cond)

    def copy(self):
        """
        Return a copy of `self`.
        """
        return MucPresence(self)

    def make_join_request(self, password = None, history_maxchars = None,
            history_maxstanzas = None, history_seconds = None,
            history_since = None):
        """
        Make the presence stanza a MUC room join request.

        :Parameters:
            - `password`: password to the room.
            - `history_maxchars`: limit of the total number of characters in
              history.
            - `history_maxstanzas`: limit of the total number of messages in
              history.
            - `history_seconds`: send only messages received in the last
              `seconds` seconds.
            - `history_since`: Send only the messages received since the
              dateTime specified (UTC).
        :Types:
            - `password`: `unicode`
            - `history_maxchars`: `int`
            - `history_maxstanzas`: `int`
            - `history_seconds`: `int`
            - `history_since`: `datetime.datetime`
        """
        self.clear_muc_child()
        self.muc_child=MucX(parent=self.xmlnode)
        if (history_maxchars is not None or history_maxstanzas is not None
                or history_seconds is not None or history_since is not None):
            history = HistoryParameters(history_maxchars, history_maxstanzas,
                    history_seconds, history_since)
            self.muc_child.set_history(history)
        if password is not None:
            self.muc_child.set_password(password)

    def get_join_info(self):
        """If `self` is a MUC room join request return the information contained.

        :return: the join request details or `None`.
        :returntype: `MucX`
        """
        x=self.get_muc_child()
        if not x:
            return None
        if not isinstance(x,MucX):
            return None
        return x

    def free(self):
        """Free the data associated with this `MucPresence` object."""
        self.muc_free()
        Presence.free(self)

class MucIq(Iq,MucStanzaExt):
    """
    Extend `Iq` with MUC related interface.
    """
    def __init__(self,xmlnode=None,from_jid=None,to_jid=None,stanza_type=None,stanza_id=None,
            error=None,error_cond=None):
        """Initialize an `Iq` object.

        :Parameters:
            - `xmlnode`: XML node to_jid be wrapped into the `Iq` object
              or other Iq object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: "get", "set", "result" or "error".
            - `stanza_id`: stanza id -- value of stanza's "id" attribute. If not
              given, then unique for the session value is generated.
            - `error_cond`: error condition name. Ignored if `stanza_type` is not "error".
        :Types:
            - `xmlnode`: `unicode` or `libxml2.xmlNode` or `Iq`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `error_cond`: `unicode`"""
        MucStanzaExt.__init__(self)
        Iq.__init__(self,xmlnode,from_jid=from_jid,to_jid=to_jid,
                stanza_type=stanza_type,stanza_id=stanza_id,
                error=error,error_cond=error_cond)

    def copy(self):
        """ Return a copy of `self`.  """
        return MucIq(self)

    def make_kick_request(self,nick,reason):
        """
        Make the iq stanza a MUC room participant kick request.

        :Parameters:
            - `nick`: nickname of user to kick.
            - `reason`: reason of the kick.
        :Types:
            - `nick`: `unicode`
            - `reason`: `unicode`

        :return: object describing the kick request details.
        :returntype: `MucItem`
        """
        self.clear_muc_child()
        self.muc_child=MucAdminQuery(parent=self.xmlnode)
        item=MucItem("none","none",nick=nick,reason=reason)
        self.muc_child.add_item(item)
        return self.muc_child

    def free(self):
        """Free the data associated with this `MucIq` object."""
        self.muc_free()
        Iq.free(self)

# vi: sts=4 et sw=4
