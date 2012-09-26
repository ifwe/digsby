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

"""
PyXMPP - Jabber/XMPP protocol implementation
============================================

Conventions
-----------

PyXMPP is object-oriented, most of its fetures are implemented via classes,
defined in various pyxmpp modules. The API is very asynchronous -- often
requested objects are not returned immediately, but instead a callback is
called when the object is available or an event occurs.

As python is not a strongly-typed language so the parameter and attribute types
shown in this documentation are not enforced, but those types are expected by
the package and others may simply not work or stop working in future releases
of PyXMPP.

Module hierarchy
................

Base XMPP features (`RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__, `RFC
3921 <http://www.ietf.org/rfc/rfc3921.txt>`__) are implemented in direct
submodules of `pyxmpp` package. Most `JSF <http://www.jabber.org>`__ defined
extensions are defined in `pyxmpp.jabber` package and modules for server
components are placed in `pyxmpp.jabberd`.

For convenience most important names (classes for application use) may be
imported into `pyxmpp`, `pyxmpp.jabber` or `pyxmpp.jabberd` packages. To do
that `pyxmpp.all`, `pyxmpp.jabber.all` or `pyxmpp.jabberd.all` must be
imported. One doesn't have to remember any other module name then.

Constructors
............

Most of PyXMPP object constructors are polymorphic. That means they accept
different types and number of arguments to create object from various input.
Usually the first argument may be an XML node to parse/wrap into the object
or parameters needed to create a new object from scratch. E.g.
`pyxmpp.stanza.Stanza` constructor accepts single `libxml2.xmlNode` argument
with XML stanza or set of keyword arguments (from_jid, to_jid, stanza_type,
etc.) to create such XML stanza. Most of the constructors will also accept
instance of their own class to create a copy of it.

Common methods
..............

Most objects describing elements of the XMPP protocol or its extensions have
method as_xml() providing their XML representations.
"""


__revision__="$Id: __init__.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

# vi: sts=4 et sw=4
