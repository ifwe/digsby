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

"""XMPP error handling.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
  - `JEP 86 <http://www.jabber.org/jeps/jep-0086.html>`__
"""

__revision__="$Id: error.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.utils import from_utf8, to_utf8
from pyxmpp.xmlextra import common_doc, common_root, common_ns
from pyxmpp import xmlextra
from pyxmpp.exceptions import ProtocolError

stream_errors={
            u"bad-format":
                ("Received XML cannot be processed",),
            u"bad-namespace-prefix":
                ("Bad namespace prefix",),
            u"conflict":
                ("Closing stream because of conflicting stream being opened",),
            u"connection-timeout":
                ("Connection was idle too long",),
            u"host-gone":
                ("Hostname is no longer hosted on the server",),
            u"host-unknown":
                ("Hostname requested is not known to the server",),
            u"improper-addressing":
                ("Improper addressing",),
            u"internal-server-error":
                ("Internal server error",),
            u"invalid-from":
                ("Invalid sender address",),
            u"invalid-id":
                ("Invalid stream ID",),
            u"invalid-namespace":
                ("Invalid namespace",),
            u"invalid-xml":
                ("Invalid XML",),
            u"not-authorized":
                ("Not authorized",),
            u"policy-violation":
                ("Local policy violation",),
            u"remote-connection-failed":
                ("Remote connection failed",),
            u"resource-constraint":
                ("Remote connection failed",),
            u"restricted-xml":
                ("Restricted XML received",),
            u"see-other-host":
                ("Redirection required",),
            u"system-shutdown":
                ("The server is being shut down",),
            u"undefined-condition":
                ("Unknown error",),
            u"unsupported-encoding":
                ("Unsupported encoding",),
            u"unsupported-stanza-type":
                ("Unsupported stanza type",),
            u"unsupported-version":
                ("Unsupported protocol version",),
            u"xml-not-well-formed":
                ("XML sent by client is not well formed",),
    }

stanza_errors={
            u"bad-request":
                ("Bad request",
                "modify",400),
            u"conflict":
                ("Named session or resource already exists",
                "cancel",409),
            u"feature-not-implemented":
                ("Feature requested is not implemented",
                "cancel",501),
            u"forbidden":
                ("You are forbidden to perform requested action",
                "auth",403),
            u"gone":
                ("Recipient or server can no longer be contacted at this address",
                "modify",302),
            u"internal-server-error":
                ("Internal server error",
                "wait",500),
            u"item-not-found":
                ("Item not found"
                ,"cancel",404),
            u"jid-malformed":
                ("JID malformed",
                "modify",400),
            u"not-acceptable":
                ("Requested action is not acceptable",
                "modify",406),
            u"not-allowed":
                ("Requested action is not allowed",
                "cancel",405),
            u"not-authorized":
                ("Not authorized",
                "auth",401),
            u"payment-required":
                ("Payment required",
                "auth",402),
            u"recipient-unavailable":
                ("Recipient is not available",
                "wait",404),
            u"redirect":
                ("Redirection",
                "modify",302),
            u"registration-required":
                ("Registration required",
                "auth",407),
            u"remote-server-not-found":
                ("Remote server not found",
                "cancel",404),
            u"remote-server-timeout":
                ("Remote server timeout",
                "wait",504),
            u"resource-constraint":
                ("Resource constraint",
                "wait",500),
            u"service-unavailable":
                ("Service is not available",
                "cancel",503),
            u"subscription-required":
                ("Subscription is required",
                "auth",407),
            u"undefined-condition":
                ("Unknown error",
                "cancel",500),
            u"unexpected-request":
                ("Unexpected request",
                "wait",400),
    }

legacy_codes={
        302: "redirect",
        400: "bad-request",
        401: "not-authorized",
        402: "payment-required",
        403: "forbidden",
        404: "item-not-found",
        405: "not-allowed",
        406: "not-acceptable",
        407: "registration-required",
        408: "remote-server-timeout",
        409: "conflict",
        500: "internal-server-error",
        501: "feature-not-implemented",
        502: "service-unavailable",
        503: "service-unavailable",
        504: "remote-server-timeout",
        510: "service-unavailable",
    }

STANZA_ERROR_NS='urn:ietf:params:xml:ns:xmpp-stanzas'
STREAM_ERROR_NS='urn:ietf:params:xml:ns:xmpp-streams'
PYXMPP_ERROR_NS='http://pyxmpp.jajcus.net/xmlns/errors'
STREAM_NS="http://etherx.jabber.org/streams"

class ErrorNode:
    """Base class for both XMPP stream and stanza errors"""
    def __init__(self,xmlnode_or_cond,ns=None,copy=True,parent=None):
        """Initialize an ErrorNode object.

        :Parameters:
            - `xmlnode_or_cond`: XML node to be wrapped into this object
              or error condition name.
            - `ns`: XML namespace URI of the error condition element (to be
              used when the provided node has no namespace).
            - `copy`: When `True` then the XML node will be copied,
              otherwise it is only borrowed.
            - `parent`: Parent node for the XML node to be copied or created.
        :Types:
            - `xmlnode_or_cond`: `libxml2.xmlNode` or `unicode`
            - `ns`: `unicode`
            - `copy`: `bool`
            - `parent`: `libxml2.xmlNode`"""
        if type(xmlnode_or_cond) is str:
            xmlnode_or_cond=unicode(xmlnode_or_cond,"utf-8")
        self.xmlnode=None
        self.borrowed=0
        if isinstance(xmlnode_or_cond,libxml2.xmlNode):
            self.__from_xml(xmlnode_or_cond,ns,copy,parent)
        elif isinstance(xmlnode_or_cond,ErrorNode):
            if not copy:
                raise TypeError, "ErrorNodes may only be copied"
            self.ns=from_utf8(xmlnode_or_cond.ns.getContent())
            self.xmlnode=xmlnode_or_cond.xmlnode.docCopyNode(common_doc,1)
            if not parent:
                parent=common_root
            parent.addChild(self.xmlnode)
        elif ns is None:
            raise ValueError, "Condition namespace not given"
        else:
            if parent:
                self.xmlnode=parent.newChild(common_ns,"error",None)
                self.borrowed=1
            else:
                self.xmlnode=common_root.newChild(common_ns,"error",None)
            cond=self.xmlnode.newChild(None,to_utf8(xmlnode_or_cond),None)
            ns=cond.newNs(ns,None)
            cond.setNs(ns)
            self.ns=from_utf8(ns.getContent())

    def __from_xml(self,xmlnode,ns,copy,parent):
        """Initialize an ErrorNode object from an XML node.

        :Parameters:
            - `xmlnode`: XML node to be wrapped into this object.
            - `ns`: XML namespace URI of the error condition element (to be
              used when the provided node has no namespace).
            - `copy`: When `True` then the XML node will be copied,
              otherwise it is only borrowed.
            - `parent`: Parent node for the XML node to be copied or created.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `ns`: `unicode`
            - `copy`: `bool`
            - `parent`: `libxml2.xmlNode`"""
        if not ns:
            ns=None
            c=xmlnode.children
            while c:
                ns=c.ns().getContent()
                if ns in (STREAM_ERROR_NS,STANZA_ERROR_NS):
                    break
                ns=None
                c=c.next
            if ns==None:
                raise ProtocolError, "Bad error namespace"
        self.ns=from_utf8(ns)
        if copy:
            self.xmlnode=xmlnode.docCopyNode(common_doc,1)
            if not parent:
                parent=common_root
            parent.addChild(self.xmlnode)
        else:
            self.xmlnode=xmlnode
            self.borrowed=1
        if copy:
            ns1=xmlnode.ns()
            xmlextra.replace_ns(self.xmlnode, ns1, common_ns)

    def __del__(self):
        if self.xmlnode:
            self.free()

    def free(self):
        """Free the associated XML node."""
        if not self.borrowed:
            self.xmlnode.unlinkNode()
            self.xmlnode.freeNode()
        self.xmlnode=None

    def free_borrowed(self):
        """Free the associated "borrowed" XML node."""
        self.xmlnode=None

    def is_legacy(self):
        """Check if the error node is a legacy error element.

        :return: `True` if it is a legacy error.
        :returntype: `bool`"""
        return not self.xmlnode.hasProp("type")

    def xpath_eval(self,expr,namespaces=None):
        """Evaluate XPath expression on the error element.

        The expression will be evaluated in context where the common namespace
        (the one used for stanza elements, mapped to 'jabber:client',
        'jabber:server', etc.) is bound to prefix "ns" and other namespaces are
        bound accordingly to the `namespaces` list.

        :Parameters:
            - `expr`: the XPath expression.
            - `namespaces`: prefix to namespace mapping.
        :Types:
            - `expr`: `unicode`
            - `namespaces`: `dict`

        :return: the result of the expression evaluation.
        """
        ctxt = common_doc.xpathNewContext()
        ctxt.setContextNode(self.xmlnode)
        ctxt.xpathRegisterNs("ns",to_utf8(self.ns))
        if namespaces:
            for prefix,uri in namespaces.items():
                ctxt.xpathRegisterNs(prefix,uri)
        ret=ctxt.xpathEval(expr)
        ctxt.xpathFreeContext()
        return ret

    def get_condition(self,ns=None):
        """Get the condition element of the error.

        :Parameters:
            - `ns`: namespace URI of the condition element if it is not
              the XMPP namespace of the error element.
        :Types:
            - `ns`: `unicode`

        :return: the condition element or `None`.
        :returntype: `libxml2.xmlNode`"""
        if ns is None:
            ns=self.ns
        c=self.xpath_eval("ns:*")
        if not c:
            self.upgrade()
            c=self.xpath_eval("ns:*")
        if not c:
            return None
        if ns==self.ns and c[0].name=="text":
            if len(c)==1:
                return None
            c=c[1:]
        return c[0]

    def get_text(self):
        """Get the description text from the error element.

        :return: the text provided with the error or `None`.
        :returntype: `unicode`"""
        c=self.xpath_eval("ns:*")
        if not c:
            self.upgrade()
        t=self.xpath_eval("ns:text")
        if not t:
            return None
        return from_utf8(t[0].getContent())

    def add_custom_condition(self,ns,cond,content=None):
        """Add custom condition element to the error.

        :Parameters:
            - `ns`: namespace URI.
            - `cond`: condition name.
            - `content`: content of the element.

        :Types:
            - `ns`: `unicode`
            - `cond`: `unicode`
            - `content`: `unicode`

        :return: the new condition element.
        :returntype: `libxml2.xmlNode`"""
        c=self.xmlnode.newTextChild(None,to_utf8(cond),content)
        ns=c.newNs(to_utf8(ns),None)
        c.setNs(ns)
        return c

    def upgrade(self):
        """Upgrade a legacy error element to the XMPP compliant one.

        Use the error code provided to select the condition and the
        <error/> CDATA for the error text."""

        if not self.xmlnode.hasProp("code"):
            code=None
        else:
            try:
                code=int(self.xmlnode.prop("code"))
            except (ValueError,KeyError):
                code=None

        if code and legacy_codes.has_key(code):
            cond=legacy_codes[code]
        else:
            cond=None

        condition=self.xpath_eval("ns:*")
        if condition:
            return
        elif cond is None:
            condition=self.xmlnode.newChild(None,"undefined-condition",None)
            ns=condition.newNs(to_utf8(self.ns),None)
            condition.setNs(ns)
            condition=self.xmlnode.newChild(None,"unknown-legacy-error",None)
            ns=condition.newNs(PYXMPP_ERROR_NS,None)
            condition.setNs(ns)
        else:
            condition=self.xmlnode.newChild(None,cond,None)
            ns=condition.newNs(to_utf8(self.ns),None)
            condition.setNs(ns)
        txt=self.xmlnode.getContent()
        if txt:
            text=self.xmlnode.newTextChild(None,"text",txt)
            ns=text.newNs(to_utf8(self.ns),None)
            text.setNs(ns)

    def downgrade(self):
        """Downgrade an XMPP error element to the legacy format.

        Add a numeric code attribute according to the condition name."""
        if self.xmlnode.hasProp("code"):
            return
        cond=self.get_condition()
        if not cond:
            return
        cond=cond.name
        if stanza_errors.has_key(cond) and stanza_errors[cond][2]:
            self.xmlnode.setProp("code",to_utf8(stanza_errors[cond][2]))

    def serialize(self):
        """Serialize the element node.

        :return: serialized element in UTF-8 encoding.
        :returntype: `str`"""
        return self.xmlnode.serialize(encoding="utf-8")

class StreamErrorNode(ErrorNode):
    """Stream error element."""
    def __init__(self,xmlnode_or_cond,copy=1,parent=None):
        """Initialize a StreamErrorNode object.

        :Parameters:
            - `xmlnode_or_cond`: XML node to be wrapped into this object
              or the primary (defined by XMPP specification) error condition name.
            - `copy`: When `True` then the XML node will be copied,
              otherwise it is only borrowed.
            - `parent`: Parent node for the XML node to be copied or created.
        :Types:
            - `xmlnode_or_cond`: `libxml2.xmlNode` or `unicode`
            - `copy`: `bool`
            - `parent`: `libxml2.xmlNode`"""
        if type(xmlnode_or_cond) is str:
            xmlnode_or_cond = xmlnode_or_cond.decode("utf-8")
        if type(xmlnode_or_cond) is unicode:
            if not stream_errors.has_key(xmlnode_or_cond):
                raise ValueError, "Bad error condition"
        ErrorNode.__init__(self,xmlnode_or_cond,STREAM_ERROR_NS,copy=copy,parent=parent)

    def get_message(self):
        """Get the message for the error.

        :return: the error message.
        :returntype: `unicode`"""
        cond=self.get_condition()
        if not cond:
            self.upgrade()
            cond=self.get_condition()
            if not cond:
                return None
        cond=cond.name
        if not stream_errors.has_key(cond):
            return None
        return stream_errors[cond][0]

class StanzaErrorNode(ErrorNode):
    """Stanza error element."""
    def __init__(self,xmlnode_or_cond,error_type=None,copy=1,parent=None):
        """Initialize a StreamErrorNode object.

        :Parameters:
            - `xmlnode_or_cond`: XML node to be wrapped into this object
              or the primary (defined by XMPP specification) error condition name.
            - `error_type`: type of the error, one of: 'cancel', 'continue',
              'modify', 'auth', 'wait'.
            - `copy`: When `True` then the XML node will be copied,
              otherwise it is only borrowed.
            - `parent`: Parent node for the XML node to be copied or created.
        :Types:
            - `xmlnode_or_cond`: `libxml2.xmlNode` or `unicode`
            - `error_type`: `unicode`
            - `copy`: `bool`
            - `parent`: `libxml2.xmlNode`"""
        if type(xmlnode_or_cond) is str:
            xmlnode_or_cond=unicode(xmlnode_or_cond,"utf-8")
        if type(xmlnode_or_cond) is unicode:
            if not stanza_errors.has_key(xmlnode_or_cond):
                raise ValueError, "Bad error condition"

        ErrorNode.__init__(self,xmlnode_or_cond,STANZA_ERROR_NS,copy=copy,parent=parent)

        if type(xmlnode_or_cond) is unicode:
            if error_type is None:
                error_type=stanza_errors[xmlnode_or_cond][1]
            self.xmlnode.setProp("type",to_utf8(error_type))

    def get_type(self):
        """Get the error type.

        :return: type of the error.
        :returntype: `unicode`"""
        if not self.xmlnode.hasProp("type"):
            self.upgrade()
        return from_utf8(self.xmlnode.prop("type"))

    def upgrade(self):
        """Upgrade a legacy error element to the XMPP compliant one.

        Use the error code provided to select the condition and the
        <error/> CDATA for the error text."""
        ErrorNode.upgrade(self)
        if self.xmlnode.hasProp("type"):
            return

        cond=self.get_condition().name
        if stanza_errors.has_key(cond):
            typ=stanza_errors[cond][1]
            self.xmlnode.setProp("type",typ)

    def get_message(self):
        """Get the message for the error.

        :return: the error message.
        :returntype: `unicode`"""
        cond=self.get_condition()
        if not cond:
            self.upgrade()
            cond=self.get_condition()
            if not cond:
                return None
        cond=cond.name
        if not stanza_errors.has_key(cond):
            return None
        return stanza_errors[cond][0]

# vi: sts=4 et sw=4
