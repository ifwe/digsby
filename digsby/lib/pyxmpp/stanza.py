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

"""General XMPP Stanza handling.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: stanza.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import libxml2
import random

from pyxmpp import xmlextra
from pyxmpp.utils import from_utf8,to_utf8
from pyxmpp.jid import JID
from pyxmpp.xmlextra import common_doc, common_ns, COMMON_NS
from pyxmpp.exceptions import ProtocolError, JIDMalformedProtocolError

random.seed()
last_id=random.randrange(1000000)

def gen_id():
    """Generate stanza id unique for the session.

    :return: the new id."""
    global last_id
    last_id+=1
    return str(last_id)

class Stanza:
    """Base class for all XMPP stanzas.

    :Ivariables:
        - `xmlnode`: stanza XML node.
        - `_error`: `pyxmpp.error.StanzaErrorNode` describing the error associated with
          the stanza of type "error".
        - `stream`: stream on which the stanza was received or `None`. May be
          used to send replies or get some session-related parameters.
    :Types:
        - `xmlnode`: `libxml2.xmlNode`
        - `_error`: `pyxmpp.error.StanzaErrorNode`"""
    stanza_type="Unknown"

    def __init__(self, name_or_xmlnode, from_jid=None, to_jid=None,
            stanza_type=None, stanza_id=None, error=None, error_cond=None,
            stream = None):
        """Initialize a Stanza object.

        :Parameters:
            - `name_or_xmlnode`: XML node to be wrapped into the Stanza object
              or other Presence object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: "get", "set", "result" or "error".
            - `stanza_id`: stanza id -- value of stanza's "id" attribute. If
              not given, then unique for the session value is generated.
            - `error`: error object. Ignored if `stanza_type` is not "error".
            - `error_cond`: error condition name. Ignored if `stanza_type` is not
              "error" or `error` is not None.
        :Types:
            - `name_or_xmlnode`: `unicode` or `libxml2.xmlNode` or `Stanza`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `error`: `pyxmpp.error.StanzaErrorNode`
            - `error_cond`: `unicode`"""
        self._error=None
        self.xmlnode=None
        if isinstance(name_or_xmlnode,Stanza):
            self.xmlnode=name_or_xmlnode.xmlnode.copyNode(1)
            common_doc.addChild(self.xmlnode)
        elif isinstance(name_or_xmlnode,libxml2.xmlNode):
            self.xmlnode=name_or_xmlnode.docCopyNode(common_doc,1)
            common_doc.addChild(self.xmlnode)
            try:
                ns = self.xmlnode.ns()
            except libxml2.treeError:
                ns = None
            if not ns or not ns.name:
                xmlextra.replace_ns(self.xmlnode, ns, common_ns)
        else:
            self.xmlnode=common_doc.newChild(common_ns,name_or_xmlnode,None)

        if from_jid is not None:
            if not isinstance(from_jid,JID):
                from_jid=JID(from_jid)
            self.xmlnode.setProp("from",from_jid.as_utf8())

        if to_jid is not None:
            if not isinstance(to_jid,JID):
                to_jid=JID(to_jid)
            self.xmlnode.setProp("to",to_jid.as_utf8())

        if stanza_type:
            self.xmlnode.setProp("type",stanza_type)

        if stanza_id:
            self.xmlnode.setProp("id",stanza_id)

        if self.get_type()=="error":
            from pyxmpp.error import StanzaErrorNode
            if error:
                self._error=StanzaErrorNode(error,parent=self.xmlnode,copy=1)
            elif error_cond:
                self._error=StanzaErrorNode(error_cond,parent=self.xmlnode)
        self.stream = stream

    def __del__(self):
        if self.xmlnode:
            self.free()

    def free(self):
        """Free the node associated with this `Stanza` object."""
        if self._error:
            self._error.free_borrowed()
        self.xmlnode.unlinkNode()
        self.xmlnode.freeNode()
        self.xmlnode=None

    def copy(self):
        """Create a deep copy of the stanza.

        :returntype: `Stanza`"""
        return Stanza(self)

    def serialize(self):
        """Serialize the stanza into an UTF-8 encoded XML string.

        :return: serialized stanza.
        :returntype: `str`"""
        return self.xmlnode.serialize(encoding="utf-8")

    def get_node(self):
        """Return the XML node wrapped into `self`.

        :returntype: `libxml2.xmlNode`"""
        return self.xmlnode

    def get_from(self):
        """Get "from" attribute of the stanza.

        :return: value of the "from" attribute (sender JID) or None.
        :returntype: `JID`"""
        if self.xmlnode.hasProp("from"):
            try:
                return JID(from_utf8(self.xmlnode.prop("from")))
            except JIDError:
                raise JIDMalformedProtocolError, "Bad JID in the 'from' attribute"
        else:
            return None

    get_from_jid=get_from

    def get_to(self):
        """Get "to" attribute of the stanza.

        :return: value of the "to" attribute (recipient JID) or None.
        :returntype: `JID`"""
        if self.xmlnode.hasProp("to"):
            try:
                return JID(from_utf8(self.xmlnode.prop("to")))
            except JIDError:
                raise JIDMalformedProtocolError, "Bad JID in the 'to' attribute"
        else:
            return None

    get_to_jid=get_to

    def get_type(self):
        """Get "type" attribute of the stanza.

        :return: value of the "type" attribute (stanza type) or None.
        :returntype: `unicode`"""
        if self.xmlnode.hasProp("type"):
            return from_utf8(self.xmlnode.prop("type"))
        else:
            return None

    get_stanza_type=get_type

    def get_id(self):
        """Get "id" attribute of the stanza.

        :return: value of the "id" attribute (stanza identifier) or None.
        :returntype: `unicode`"""
        if self.xmlnode.hasProp("id"):
            return from_utf8(self.xmlnode.prop("id"))
        else:
            return None

    get_stanza_id=get_id

    def get_error(self):
        """Get stanza error information.

        :return: object describing the error.
        :returntype: `pyxmpp.error.StanzaErrorNode`"""
        if self._error:
            return self._error
        n=self.xpath_eval(u"ns:error")
        if not n:
            raise ProtocolError, (None, "This stanza contains no error: %r" % (self.serialize(),))
        from pyxmpp.error import StanzaErrorNode
        self._error=StanzaErrorNode(n[0],copy=0)
        return self._error

    def set_from(self,from_jid):
        """Set "from" attribute of the stanza.

        :Parameters:
            - `from_jid`: new value of the "from" attribute (sender JID).
        :Types:
            - `from_jid`: `JID`"""
        if from_jid:
            return self.xmlnode.setProp("from", JID(from_jid).as_utf8())
        else:
            return self.xmlnode.unsetProp("from")

    def set_to(self,to_jid):
        """Set "to" attribute of the stanza.

        :Parameters:
            - `to_jid`: new value of the "to" attribute (recipient JID).
        :Types:
            - `to_jid`: `JID`"""
        if to_jid:
            return self.xmlnode.setProp("to", JID(to_jid).as_utf8())
        else:
            return self.xmlnode.unsetProp("to")

    def set_type(self,stanza_type):
        """Set "type" attribute of the stanza.

        :Parameters:
            - `stanza_type`: new value of the "type" attribute (stanza type).
        :Types:
            - `stanza_type`: `unicode`"""
        if stanza_type:
            return self.xmlnode.setProp("type",to_utf8(stanza_type))
        else:
            return self.xmlnode.unsetProp("type")

    def set_id(self,stanza_id):
        """Set "id" attribute of the stanza.

        :Parameters:
            - `stanza_id`: new value of the "id" attribute (stanza identifier).
        :Types:
            - `stanza_id`: `unicode`"""
        if stanza_id:
            return self.xmlnode.setProp("id",to_utf8(stanza_id))
        else:
            return self.xmlnode.unsetProp("id")

    def set_content(self,content):
        """Set stanza content to an XML node.

        :Parameters:
            - `content`: XML node to be included in the stanza.
        :Types:
            - `content`: `libxml2.xmlNode` or unicode, or UTF-8 `str`
        """
        while self.xmlnode.children:
            self.xmlnode.children.unlinkNode()
        if hasattr(content,"as_xml"):
            content.as_xml(parent=self.xmlnode,doc=common_doc)
        elif isinstance(content,libxml2.xmlNode):
            self.xmlnode.addChild(content.docCopyNode(common_doc,1))
        elif isinstance(content,unicode):
            self.xmlnode.setContent(to_utf8(content))
        else:
            self.xmlnode.setContent(content)

    def add_content(self,content):
        """Add an XML node to the stanza's payload.

        :Parameters:
            - `content`: XML node to be added to the payload.
        :Types:
            - `content`: `libxml2.xmlNode`, UTF-8 `str` or unicode, or
               an object with "as_xml()" method.
        """
        if hasattr(content, "as_xml"):
            content.as_xml(parent = self.xmlnode, doc = common_doc)
        elif isinstance(content,libxml2.xmlNode):
            self.xmlnode.addChild(content.docCopyNode(common_doc,1))
        elif isinstance(content,unicode):
            self.xmlnode.addContent(to_utf8(content))
        else:
            self.xmlnode.addContent(content)

    def set_new_content(self,ns_uri,name):
        """Set stanza payload to a new XML element.

        :Parameters:
            - `ns_uri`: XML namespace URI of the element.
            - `name`: element name.
        :Types:
            - `ns_uri`: `str`
            - `name`: `str` or `unicode`
        """
        while self.xmlnode.children:
            self.xmlnode.children.unlinkNode()
        return self.add_new_content(ns_uri,name)

    def add_new_content(self,ns_uri,name):
        """Add a new XML element to the stanza payload.

        :Parameters:
            - `ns_uri`: XML namespace URI of the element.
            - `name`: element name.
        :Types:
            - `ns_uri`: `str`
            - `name`: `str` or `unicode`
        """
        c=self.xmlnode.newChild(None,to_utf8(name),None)
        if ns_uri:
            ns=c.newNs(ns_uri,None)
            c.setNs(ns)
        return c

    def xpath_eval(self,expr,namespaces=None):
        """Evaluate an XPath expression on the stanza XML node.

        The expression will be evaluated in context where the common namespace
        (the one used for stanza elements, mapped to 'jabber:client',
        'jabber:server', etc.) is bound to prefix "ns" and other namespaces are
        bound accordingly to the `namespaces` list.

        :Parameters:
            - `expr`: XPath expression.
            - `namespaces`: mapping from namespace prefixes to URIs.
        :Types:
            - `expr`: `unicode`
            - `namespaces`: `dict` or other mapping
        """
        ctxt = common_doc.xpathNewContext()
        ctxt.setContextNode(self.xmlnode)
        ctxt.xpathRegisterNs("ns",COMMON_NS)
        if namespaces:
            for prefix,uri in namespaces.items():
                ctxt.xpathRegisterNs(unicode(prefix),uri)
        ret=ctxt.xpathEval(unicode(expr))
        ctxt.xpathFreeContext()
        return ret

    def __eq__(self,other):
        if not isinstance(other,Stanza):
            return False
        return self.xmlnode.serialize()==other.xmlnode.serialize()

    def __ne__(self,other):
        if not isinstance(other,Stanza):
            return True
        return self.xmlnode.serialize()!=other.xmlnode.serialize()

# vi: sts=4 et sw=4
