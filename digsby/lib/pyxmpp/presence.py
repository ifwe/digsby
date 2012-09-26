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

"""Presence XMPP stanza handling

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: presence.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.stanza import Stanza
from pyxmpp.xmlextra import common_ns

presence_types=("available","unavailable","probe","subscribe","unsubscribe","subscribed",
        "unsubscribed","invisible","error")

accept_responses={
        "subscribe": "subscribed",
        "subscribed": "subscribe",
        "unsubscribe": "unsubscribed",
        "unsubscribed": "unsubscribe",
        }

deny_responses={
        "subscribe": "unsubscribed",
        "subscribed": "unsubscribe",
        "unsubscribe": "subscribed",
        "unsubscribed": "subscribe",
        }

class Presence(Stanza):
    """Wraper object for <presence /> stanzas."""
    stanza_type="presence"
    def __init__(self, xmlnode = None, from_jid = None, to_jid = None, stanza_type = None, 
            stanza_id = None, show = None, status = None, priority = 0,
            error = None, error_cond = None, stream = None):
        """Initialize a `Presence` object.

        :Parameters:
            - `xmlnode`: XML node to_jid be wrapped into the `Presence` object
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
            - `xmlnode`: `unicode` or `libxml2.xmlNode` or `Stanza`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `show`: `unicode`
            - `status`: `unicode`
            - `priority`: `unicode`
            - `error_cond`: `unicode`"""
        self.xmlnode=None
        if isinstance(xmlnode,Presence):
            pass
        elif isinstance(xmlnode,Stanza):
            raise TypeError,"Couldn't make Presence from other Stanza"
        elif isinstance(xmlnode,libxml2.xmlNode):
            pass
        elif xmlnode is not None:
            raise TypeError,"Couldn't make Presence from %r" % (type(xmlnode),)

        if stanza_type and stanza_type not in presence_types:
            raise ValueError, "Invalid presence type: %r" % (type,)

        if stanza_type=="available":
            stanza_type=None

        if xmlnode is None:
            xmlnode="presence"

        Stanza.__init__(self, xmlnode, from_jid = from_jid, to_jid = to_jid, stanza_type = stanza_type,
                stanza_id = stanza_id, error = error, error_cond = error_cond, stream = stream)

        if show:
            self.xmlnode.newTextChild(common_ns,"show",to_utf8(show))
        if status:
            self.xmlnode.newTextChild(common_ns,"status",to_utf8(status))
        if priority and priority!=0:
            self.xmlnode.newTextChild(common_ns,"priority",to_utf8(unicode(priority)))

    def copy(self):
        """Create a deep copy of the presence stanza.

        :returntype: `Presence`"""
        return Presence(self)

    def set_status(self,status):
        """Change presence status description.

        :Parameters:
            - `status`: descriptive text for the presence stanza.
        :Types:
            - `status`: `unicode`"""
        n=self.xpath_eval("ns:status")
        if not status:
            if n:
                n[0].unlinkNode()
                n[0].freeNode()
            else:
                return
        if n:
            n[0].setContent(to_utf8(status))
        else:
            self.xmlnode.newTextChild(common_ns,"status",to_utf8(status))

    def get_status(self):
        """Get presence status description.

        :return: value of stanza's <status/> field.
        :returntype: `unicode`"""
        n=self.xpath_eval("ns:status")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def get_show(self):
        """Get presence "show" field.

        :return: value of stanza's <show/> field.
        :returntype: `unicode`"""
        n=self.xpath_eval("ns:show")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def set_show(self,show):
        """Change presence "show" field.

        :Parameters:
            - `show`: new value for the "show" field of presence stanza. One
              of: None, "away", "xa", "dnd", "chat".
        :Types:
            - `show`: `unicode`"""
        n=self.xpath_eval("ns:show")
        if not show:
            if n:
                n[0].unlinkNode()
                n[0].freeNode()
            else:
                return
        if n:
            n[0].setContent(to_utf8(show))
        else:
            self.xmlnode.newTextChild(common_ns,"show",to_utf8(show))

    def get_priority(self):
        """Get presence priority.

        :return: value of stanza's priority. 0 if the stanza doesn't contain
            <priority/> element.
        :returntype: `int`"""
        n=self.xpath_eval("ns:priority")
        if not n:
            return 0
        try:
            prio=int(n[0].getContent())
        except ValueError:
            return 0
        return prio

    def set_priority(self,priority):
        """Change presence priority.

        :Parameters:
            - `priority`: new presence priority.
        :Types:
            - `priority`: `int`"""
        n=self.xpath_eval("ns:priority")
        if not priority:
            if n:
                n[0].unlinkNode()
                n[0].freeNode()
            else:
                return
        priority=int(priority)
        if priority<-128 or priority>127:
            raise ValueError, "Bad priority value"
        priority=str(priority)
        if n:
            n[0].setContent(priority)
        else:
            self.xmlnode.newTextChild(common_ns,"priority",priority)

    def make_accept_response(self):
        """Create "accept" response for the "subscribe"/"subscribed"/"unsubscribe"/"unsubscribed"
        presence stanza.

        :return: new stanza.
        :returntype: `Presence`"""

        if self.get_type() not in ("subscribe","subscribed","unsubscribe","unsubscribed"):
            raise ValueError, ("Results may only be generated for 'subscribe',"
                "'subscribed','unsubscribe' or 'unsubscribed' presence")

        pr=Presence(stanza_type=accept_responses[self.get_type()],
            from_jid=self.get_to(),to_jid=self.get_from(),stanza_id=self.get_id())
        return pr

    def make_deny_response(self):
        """Create "deny" response for the "subscribe"/"subscribed"/"unsubscribe"/"unsubscribed"
        presence stanza.

        :return: new presence stanza.
        :returntype: `Presence`"""
        if self.get_type() not in ("subscribe","subscribed","unsubscribe","unsubscribed"):
            raise ValueError, ("Results may only be generated for 'subscribe',"
                "'subscribed','unsubscribe' or 'unsubscribed' presence")

        pr=Presence(stanza_type=deny_responses[self.get_type()],
            from_jid=self.get_to(),to_jid=self.get_from(),stanza_id=self.get_id())
        return pr

    def make_error_response(self,cond):
        """Create error response for the any non-error presence stanza.

        :Parameters:
            - `cond`: error condition name, as defined in XMPP specification.
        :Types:
            - `cond`: `unicode`

        :return: new presence stanza.
        :returntype: `Presence`"""

        if self.get_type() == "error":
            raise ValueError, "Errors may not be generated in response to errors"

        p=Presence(stanza_type="error",from_jid=self.get_to(),to_jid=self.get_from(),
            stanza_id=self.get_id(),error_cond=cond)

        if self.xmlnode.children:
            n=self.xmlnode.children
            while n:
                p.xmlnode.children.addPrevSibling(n.copyNode(1))
                n=n.next
        return p

# vi: sts=4 et sw=4
