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
# pylint: disable-msg=W0232, E0201

"""jid -- Jabber ID handling

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: jid.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import re
import weakref
import warnings

from encodings import idna

from pyxmpp.xmppstringprep import nodeprep,resourceprep
from pyxmpp.exceptions import JIDError

node_invalid_re=re.compile(ur"[" u'"' ur"&'/:<>@\s\x00-\x19]",re.UNICODE)
resource_invalid_re=re.compile(ur"[\s\x00-\x19]",re.UNICODE)

def are_domains_equal(a,b):
    """Compare two International Domain Names.

    :Parameters:
        - `a`,`b`: domains names to compare

    :return: True `a` and `b` are equal as domain names."""

    a=idna.ToASCII(a)
    b=idna.ToASCII(b)
    return a.lower()==b.lower()

class JID(object):
    """JID.

    :Ivariables:
        - `node`: node part of the JID
        - `domain`: domain part of the JID
        - `resource`: resource part of the JID

    JID objects are immutable. They are also cached for better performance.
    """
    cache=weakref.WeakValueDictionary()
    __slots__=["node","domain","resource","__weakref__"]
    def __new__(cls,node_or_jid=None,domain=None,resource=None,check=True):
        """Create a new JID object or take one from the cache.

        :Parameters:
            - `node_or_jid`: node part of the JID, JID object to copy or
              Unicode representation of the JID.
            - `domain`: domain part of the JID
            - `resource`: resource part of the JID
            - `check`: if `False` then JID is not checked for specifiaction
              compliance.
        """

        if isinstance(node_or_jid,JID):
            return node_or_jid

        if domain is None and resource is None:
            obj=cls.cache.get(node_or_jid)
            if obj:
                return obj
        else:
            obj=None
        if obj is None:
            obj=object.__new__(cls)

        if node_or_jid:
            node_or_jid = unicode(node_or_jid)
        if (node_or_jid and
                ((u"@" in node_or_jid) or (u"/" in node_or_jid))):
            obj.__from_unicode(node_or_jid)
            cls.cache[node_or_jid]=obj
        else:
            if domain is None and resource is None:
                if node_or_jid is None:
                    raise JIDError,"At least domain must be given"
                domain=node_or_jid
                node_or_jid=None
            if check:
                obj.__set_node(node_or_jid)
                obj.__set_domain(domain)
                obj.__set_resource(resource)
            else:
                object.__setattr__(obj,"node",node_or_jid)
                object.__setattr__(obj,"domain",domain)
                object.__setattr__(obj,"resource",resource)
        return obj

    def __setattr__(self,name,value):
        raise RuntimeError,"JID objects are immutable!"

    def __from_unicode(self,s,check=True):
        """Initialize JID object from Unicode string.

        :Parameters:
            - `s`: the JID string
            - `check`: when `False` then the JID is not checked for
              specification compliance."""
        s1=s.split(u"/",1)
        s2=s1[0].split(u"@",1)
        if len(s2)==2:
            if check:
                self.__set_node(s2[0])
                self.__set_domain(s2[1])
            else:
                object.__setattr__(self,"node",s2[0])
                object.__setattr__(self,"domain",s2[1])
        else:
            if check:
                self.__set_domain(s2[0])
            else:
                object.__setattr__(self,"domain",s2[0])
            object.__setattr__(self,"node",None)
        if len(s1)==2:
            if check:
                self.__set_resource(s1[1])
            else:
                object.__setattr__(self,"resource",s1[1])
        else:
            object.__setattr__(self,"resource",None)
        if not self.domain:
            raise JIDError,"Domain is required in JID."

    def __set_node(self,s):
        """Initialize `self.node`

        :Parameters:
            - `s`: Node part of the JID
        :Types:
            - `s`: unicode

        :raise JIDError: if the node name is too long.
        :raise pyxmpp.xmppstringprep.StringprepError: if the
            node name fails Nodeprep preparation."""
        if s:
            s = unicode(s)
            s=nodeprep.prepare(s)
            if len(s.encode("utf-8"))>1023:
                raise JIDError,"Node name too long"
        else:
            s=None
        object.__setattr__(self,"node",s)

    def __set_domain(self,s):
        """Initialize `self.domain`

        :Parameters:
            - `s`: Unicode or UTF-8 domain part of the JID

        :raise JIDError: if the domain name is too long."""

        if s is None:
            raise JIDError,"Domain must be given"
        if s:
            s = unicode(s)
        s=idna.nameprep(s)
        if len(s.encode("utf-8"))>1023:
            raise JIDError,"Domain name too long"
        object.__setattr__(self,"domain",s)

    def __set_resource(self,s):
        """Initialize `self.resource`

        :Parameters:
            - `s`: Unicode or UTF-8 resource part of the JID

        :raise JIDError: if the resource name is too long.
        :raise pyxmpp.xmppstringprep.StringprepError: if the
            node name fails Resourceprep preparation."""
        if s:
            s = unicode(s)
            s=resourceprep.prepare(s)
            if len(s.encode("utf-8"))>1023:
                raise JIDError,"Resource name too long"
        else:
            s=None
        object.__setattr__(self,"resource",s)

    def __str__(self):
#        warnings.warn("JIDs should not be used as strings", DeprecationWarning, stacklevel=2)
        return self.as_utf8()

    def __unicode__(self):
        return self.as_unicode()

    def __repr__(self):
        return "<JID: %r>" % (self.as_unicode())

    def as_utf8(self):
        """UTF-8 encoded JID representation.

        :return: UTF-8 encoded JID."""
        return self.as_unicode().encode("utf-8")

    def as_string(self):
        """UTF-8 encoded JID representation.

        *Deprecated* Always use Unicode objects, or `as_utf8` if you really want.

        :return: UTF-8 encoded JID."""
        warnings.warn("JID.as_string() is deprecated. Use unicode() or `as_utf8` instead.",
                 DeprecationWarning, stacklevel=1)
        return self.as_utf8()

    def as_unicode(self):
        """Unicode string JID representation.

        :return: JID as Unicode string."""
        r=self.domain
        if self.node:
            r=self.node+u'@'+r
        if self.resource:
            r=r+u'/'+self.resource
        if not JID.cache.has_key(r):
            JID.cache[r]=self
        return r

    def bare(self):
        """Make bare JID made by removing resource from current `self`.

        :return: new JID object without resource part."""
        return JID(self.node,self.domain,check=False)

    def __eq__(self,other):
        if other is None:
            return False
        elif type(other) in (str, unicode):
            try:
                other=JID(other)
            except:
                return False
        elif not isinstance(other,JID):
            return False

        return (self.node==other.node
            and are_domains_equal(self.domain,other.domain)
            and self.resource==other.resource)

    def __ne__(self,other):
        return not self.__eq__(other)

    def __cmp__(self,other):
        a=self.as_unicode()
        return cmp(a,other)

    def __hash__(self):
        return hash(self.node)^hash(self.domain)^hash(self.resource)

# vi: sts=4 et sw=4
