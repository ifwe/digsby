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

"""XMPP-IM roster handling.

Normative reference:
  - `RFC 3921 <http://www.ietf.org/rfc/rfc3921.txt>`__
"""

__revision__="$Id: roster.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.xmlextra import common_doc, get_node_ns_uri
from pyxmpp.iq import Iq
from pyxmpp.jid import JID

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.objects import StanzaPayloadObject

ROSTER_NS="jabber:iq:roster"

class RosterItem(StanzaPayloadObject):
    """
    Roster item.

    Represents part of a roster, or roster update request.
    """

    xml_element_name = "item"
    xml_element_namespace = ROSTER_NS

    def __init__(self,node_or_jid,subscription="none",name=None,groups=(),ask=None):
        """
        Initialize a roster item from XML node or jid and optional attributes.

        :Parameters:
            - `node_or_jid`: XML node or JID
            - `subscription`: subscription type ("none", "to", "from" or "both"
            - `name`: item visible name
            - `groups`: sequence of groups the item is member of
            - `ask`: True if there was unreplied subsription or unsubscription
              request sent."""
        if isinstance(node_or_jid,libxml2.xmlNode):
            self.from_xml(node_or_jid)
        else:
            node_or_jid=JID(node_or_jid)
            if subscription not in ("none","from","to","both","remove"):
                raise ValueError,"Bad subscription type: %r" % (subscription,)
            if ask not in ("subscribe",None):
                raise ValueError,"Bad ask type: %r" % (ask,)
            self.jid=node_or_jid
            self.ask=ask
            self.subscription=subscription
            self.name=name
            self.groups=list(groups)

    def from_xml(self,node):
        """Initialize RosterItem from XML node."""
        if node.type!="element":
            raise ValueError,"XML node is not a roster item (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=ROSTER_NS or node.name!="item":
            raise ValueError,"XML node is not a roster item"
        jid=JID(node.prop("jid").decode("utf-8"))
        subscription=node.prop("subscription")
        if subscription not in ("none","from","to","both","remove"):
            subscription="none"
        ask=node.prop("ask")
        if ask not in ("subscribe",None):
            ask=None
        name=from_utf8(node.prop("name"))
        groups=[]
        n=node.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=ROSTER_NS or n.name!="group":
                n=n.next
                continue
            group=n.getContent()
            if group:
                groups.append(from_utf8(group))
            n=n.next
        self.jid=jid
        self.name=name
        self.groups=groups
        self.subscription=subscription
        self.ask=ask

    def complete_xml_element(self, xmlnode, _unused):
        """Complete the XML node with `self` content.

        Should be overriden in classes derived from `StanzaPayloadObject`.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `_unused`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `_unused`: `libxml2.xmlDoc`"""
        xmlnode.setProp("jid",self.jid.as_utf8())
        if self.name:
            xmlnode.setProp("name",to_utf8(self.name))
        xmlnode.setProp("subscription",self.subscription)
        if self.ask:
            xmlnode.setProp("ask",to_utf8(self.ask))
        for g in self.groups:
            xmlnode.newTextChild(None, "group", to_utf8(g))

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

    def make_roster_push(self):
        """
        Make "roster push" IQ stanza from the item representing roster update
        request.
        """
        iq=Iq(stanza_type="set")
        q=iq.new_query(ROSTER_NS)
        self.as_xml(parent=q, doc=common_doc)
        return iq

class Roster(StanzaPayloadObject):
    """Class representing XMPP-IM roster.

    Iteration over `Roster` object iterates over roster items.

    ``for item in roster: ...`` may be used to iterate over roster items,
    ``roster[jid]`` to get roster item by jid, ``jid in roster`` to test roster
    for jid presence.

    :Ivariables:
        - `items_dict`: items indexed by JID.
    :Properties:
        - `items`: roster items.
    :Types:
        - `items_dict`: `dict` of `JID` -> `RosterItem`
        - `items`: `list` of `RosterItem`"""

    xml_element_name = "query"
    xml_element_namespace = ROSTER_NS

    def __init__(self,node=None,server=False,strict=True):
        """
        Initialize Roster object.

        `node` should be an XML representation of the roster (e.g. as sent
        from server in response to roster request).  When `node` is None empty
        roster will be created.

        If `server` is true the object is considered server-side roster.

        If `strict` is False, than invalid items in the XML will be ignored.
        """
        self.items_dict={}
        self.server=server
        self.node=None
        if node:
            self.from_xml(node,strict)

    def from_xml(self,node,strict=True):
        """
        Initialize Roster object from XML node.

        If `strict` is False, than invalid items in the XML will be ignored.
        """
        self.items_dict={}
        if node.type!="element":
            raise ValueError,"XML node is not a roster (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=ROSTER_NS or node.name!="query":
            raise ValueError,"XML node is not a roster"
        n=node.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=ROSTER_NS or n.name!="item":
                n=n.next
                continue
            try:
                item=RosterItem(n)
                self.items_dict[item.jid]=item
            except ValueError:
                if strict:
                    raise
            n=n.next

    def complete_xml_element(self, xmlnode, doc):
        """Complete the XML node with `self` content.

        Should be overriden in classes derived from `StanzaPayloadObject`.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `doc`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `doc`: `libxml2.xmlDoc`"""
        for it in self.items_dict.values():
            it.as_xml(parent=xmlnode, doc=doc)

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r
    
    def __iter__(self):
        return self.items_dict.itervalues()

    def __contains__(self, jid):
        return jid in self.items_dict

    def __getitem__(self, jid):
        return self.items_dict[jid]

    def get_items(self):
        """Return a list of items in the roster."""
        return self.items_dict.values()

    items = property(get_items)

    def get_groups(self):
        """Return a list of groups in the roster."""
        r={}
        for it in self.items_dict.values():
            it.groups=[g for g in it.groups if g]
            if it.groups:
                for g in it.groups:
                    r[g]=True
            else:
                r[None]=True
        return r.keys()

    def get_items_by_name(self, name, case_sensitive = True):
        """
        Return a list of items with given `name`.

        If `case_sensitive` is False the matching will be case insensitive.
        """
        if not case_sensitive and name:
            name = name.lower()
        r = []
        for it in self.items_dict.values():
            if it.name == name:
                r.append(it)
            elif it.name is None:
                continue
            elif not case_sensitive and it.name.lower() == name:
                r.append(it)
        return r

    def get_items_by_group(self,group,case_sensitive=True):
        """
        Return a list of groups with given name.

        If `case_sensitive` is False the matching will be case insensitive.
        """
        r=[]
        if not group:
            for it in self.items_dict.values():
                it.groups=[g for g in it.groups if g]
                if not it.groups:
                    r.append(it)
            return r
        if not case_sensitive:
            group=group.lower()
        for it in self.items_dict.values():
            if group in it.groups:
                r.append(it)
            elif not case_sensitive and group in [g.lower() for g in it.groups]:
                r.append(it)
        return r

    def get_item_by_jid(self,jid):
        """
        Return roster item with given `jid`.

        :raise KeyError: if the item is not found.
        """
        if not jid:
            raise ValueError,"jid is None"
        return self.items_dict[jid]

    def add_item(self,item_or_jid,subscription="none",name=None,groups=(),ask=None):
        """
        Add an item to the roster.

        The `item_or_jid` argument may be a `RosterItem` object or a `JID`. If
        it is a JID then `subscription`, `name`, `groups` and `ask` may also be
        specified.
        """
        if isinstance(item_or_jid,RosterItem):
            item=item_or_jid
            if self.items_dict.has_key(item.jid):
                raise ValueError,"Item already exists"
        else:
            if self.items_dict.has_key(item_or_jid):
                raise ValueError,"Item already exists"
            if not self.server or subscription not in ("none","from","to","both"):
                subscription="none"
            if not self.server:
                ask=None
            item=RosterItem(item_or_jid,subscription,name,groups,ask)
        self.items_dict[item.jid]=item
        return item

    def remove_item(self,jid):
        """Remove item from the roster."""
        del self.items_dict[jid]
        return RosterItem(jid,"remove")

    def update(self,query):
        """
        Apply an update request to the roster.

        `query` should be a query included in a "roster push" IQ received.
        """
        ctxt=common_doc.xpathNewContext()
        ctxt.setContextNode(query)
        ctxt.xpathRegisterNs("r",ROSTER_NS)
        items=ctxt.xpathEval("r:item")
        ctxt.xpathFreeContext()
        if not items:
            raise ValueError,"No item to update"
        local_items = []
        for item in items:
            item=RosterItem(item)
            jid=item.jid
            subscription=item.subscription
            try:
                local_item=self.get_item_by_jid(jid)
                local_item.subscription=subscription
            except KeyError:
                if subscription=="remove":
                    return [RosterItem(jid,"remove")]
                if self.server or subscription not in ("none","from","to","both"):
                    subscription="none"
                local_item=RosterItem(jid,subscription)
            if subscription=="remove":
                del self.items_dict[local_item.jid]
                return [RosterItem(jid,"remove")]
            local_item.name=item.name
            local_item.groups=list(item.groups)
            if not self.server:
                local_item.ask=item.ask
            self.items_dict[local_item.jid]=local_item
            local_items.append(local_item)
        return local_items

# vi: sts=4 et sw=4
