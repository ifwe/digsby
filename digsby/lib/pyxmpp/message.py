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

"""Message XMPP stanza handling

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: message.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import libxml2
from pyxmpp.stanza import Stanza
from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.xmlextra import common_ns

message_types=("normal","chat","headline","error","groupchat")

class Message(Stanza):
    """Wraper object for <message /> stanzas."""
    stanza_type="message"
    def __init__(self, xmlnode = None, from_jid = None, to_jid = None, stanza_type = None, stanza_id = None,
            subject = None, body = None, thread = None, error = None, error_cond = None, stream = None):
        """Initialize a `Message` object.

        :Parameters:
            - `xmlnode`: XML node to_jid be wrapped into the `Message` object
              or other Message object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: "get", "set", "result" or "error".
            - `stanza_id`: stanza id -- value of stanza's "id" attribute. If not
              given, then unique for the session value is generated.
            - `subject`: message subject,
            - `body`: message body.
            - `thread`: message thread id.
            - `error_cond`: error condition name. Ignored if `stanza_type` is not "error".
        :Types:
            - `xmlnode`: `unicode` or `libxml2.xmlNode` or `Stanza`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `subject`: `unicode`
            - `body`: `unicode`
            - `thread`: `unicode`
            - `error_cond`: `unicode`"""

        self.xmlnode=None
        if isinstance(xmlnode,Message):
            pass
        elif isinstance(xmlnode,Stanza):
            raise TypeError, "Couldn't make Message from other Stanza"
        elif isinstance(xmlnode,libxml2.xmlNode):
            pass
        elif xmlnode is not None:
            raise TypeError, "Couldn't make Message from %r" % (type(xmlnode),)

        if xmlnode is None:
            xmlnode="message"

        Stanza.__init__(self, xmlnode, from_jid = from_jid, to_jid = to_jid, stanza_type = stanza_type,
                stanza_id = stanza_id, error = error, error_cond = error_cond, stream = stream)

        if subject is not None:
            self.xmlnode.newTextChild(common_ns,"subject",to_utf8(subject))
        if body is not None:
            self.xmlnode.newTextChild(common_ns,"body",to_utf8(body))
        if thread is not None:
            self.xmlnode.newTextChild(common_ns,"thread",to_utf8(thread))

    def get_subject(self):
        """Get the message subject.

        :return: the message subject or `None` if there is no subject.
        :returntype: `unicode`"""
        n=self.xpath_eval("ns:subject")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def get_thread(self):
        """Get the thread-id subject.

        :return: the thread-id or `None` if there is no thread-id.
        :returntype: `unicode`"""
        n=self.xpath_eval("ns:thread")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def copy(self):
        """Create a deep copy of the message stanza.

        :returntype: `Message`"""
        return Message(self)

    def get_body(self):
        """Get the body of the message.

        :return: the body of the message or `None` if there is no body.
        :returntype: `unicode`"""
        n=self.xpath_eval("ns:body")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def make_error_response(self,cond):
        """Create error response for any non-error message stanza.

        :Parameters:
            - `cond`: error condition name, as defined in XMPP specification.

        :return: new message stanza with the same "id" as self, "from" and
            "to" attributes swapped, type="error" and containing <error />
            element plus payload of `self`.
        :returntype: `unicode`"""

        if self.get_type() == "error":
            raise ValueError, "Errors may not be generated in response to errors"

        m=Message(stanza_type="error",from_jid=self.get_to(),to_jid=self.get_from(),
            stanza_id=self.get_id(),error_cond=cond)

        if self.xmlnode.children:
            n=self.xmlnode.children
            while n:
                m.xmlnode.children.addPrevSibling(n.copyNode(1))
                n=n.next
        return m

# vi: sts=4 et sw=4
