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

"""Iq XMPP stanza handling

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: iq.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.xmlextra import get_node_ns_uri
from pyxmpp.stanza import Stanza, gen_id

class Iq(Stanza):
    """Wraper object for <iq /> stanzas."""
    stanza_type="iq"
    def __init__(self, xmlnode = None, from_jid = None, to_jid = None, stanza_type = None,
            stanza_id = None, error = None, error_cond=None, stream = None):
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
        self.xmlnode=None
        if isinstance(xmlnode,Iq):
            pass
        elif isinstance(xmlnode,Stanza):
            raise TypeError,"Couldn't make Iq from other Stanza"
        elif isinstance(xmlnode,libxml2.xmlNode):
            pass
        elif xmlnode is not None:
            raise TypeError,"Couldn't make Iq from %r" % (type(xmlnode),)
        elif not stanza_type:
            raise ValueError, "type is required for Iq"
        else:
            if not stanza_id and stanza_type in ("get", "set"):
                stanza_id=gen_id()

        if not xmlnode and stanza_type not in ("get","set","result","error"):
            raise ValueError, "Invalid Iq type: %r" % (stanza_type,)

        if xmlnode is None:
            xmlnode="iq"

        Stanza.__init__(self, xmlnode, from_jid = from_jid, to_jid = to_jid,
            stanza_type = stanza_type, stanza_id = stanza_id, error = error,
            error_cond = error_cond, stream = stream)

    def copy(self):
        """Create a deep copy of the iq stanza.

        :returntype: `Iq`"""
        return Iq(self)

    def make_error_response(self,cond):
        """Create error response for the a "get" or "set" iq stanza.

        :Parameters:
            - `cond`: error condition name, as defined in XMPP specification.

        :return: new `Iq` object with the same "id" as self, "from" and "to"
            attributes swapped, type="error" and containing <error /> element
            plus payload of `self`.
        :returntype: `Iq`"""

        if self.get_type() in ("result", "error"):
            raise ValueError, "Errors may not be generated for 'result' and 'error' iq"

        iq=Iq(stanza_type="error",from_jid=self.get_to(),to_jid=self.get_from(),
            stanza_id=self.get_id(),error_cond=cond)
        n=self.get_query()
        if n:
            n=n.copyNode(1)
            iq.xmlnode.children.addPrevSibling(n)
        return iq

    def make_result_response(self):
        """Create result response for the a "get" or "set" iq stanza.

        :return: new `Iq` object with the same "id" as self, "from" and "to"
            attributes replaced and type="result".
        :returntype: `Iq`"""

        if self.get_type() not in ("set","get"):
            raise ValueError, "Results may only be generated for 'set' or 'get' iq"

        iq=Iq(stanza_type="result", from_jid=self.get_to(),
                to_jid=self.get_from(), stanza_id=self.get_id())

        return iq

    def new_query(self,ns_uri,name="query"):
        """Create new payload element for the stanza.

        :Parameters:
            - `ns_uri`: namespace URI of the element.
            - `name`: element name.
        :Types:
            - `ns_uri`: `str`
            - `name`: `unicode`

        :return: the new payload node.
        :returntype: `libxml2.xmlNode`"""
        return self.set_new_content(ns_uri,name)

    def get_query(self):
        """Get the payload element of the stanza.

        :return: the payload element or None if there is no payload.
        :returntype: `libxml2.xmlNode`"""
        c = self.xmlnode.children
        while c:
            try:
                if c.ns():
                    return c
            except libxml2.treeError:
                pass
            c = c.next
        return None

    def get_query_ns(self):
        """Get a namespace of the stanza payload.

        :return: XML namespace URI of the payload or None if there is no
            payload.
        :returntype: `str`"""
        q=self.get_query()
        if q:
            return get_node_ns_uri(q)
        else:
            return None

# vi: sts=4 et sw=4
