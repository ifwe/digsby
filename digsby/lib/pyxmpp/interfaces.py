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

"""Interfaces for flexible API extensions."""

__revision__ = "$Id: error.py 647 2006-08-26 18:27:39Z jajcus $"
__docformat__ = "restructuredtext en"

from pyxmpp.interface import Interface, Attribute

class IPyXMPPHelper(Interface):
    """Base for all interfaces used as PyXMPP helpers."""

class IPresenceHandlersProvider(IPyXMPPHelper):
    def get_presence_handlers():
        """Returns iterable over (presence_type, handler[, namespace[, priority]]) tuples.

        The tuples will be used as arguments for `Stream.set_presence_handler`."""

class IMessageHandlersProvider(IPyXMPPHelper):
     def get_message_handlers():
        """Returns iterable over (message_type, handler[, namespace[, priority]]) tuples.

        The tuples will be used as arguments for `Stream.set_message_handler`."""
 
class IIqHandlersProvider(IPyXMPPHelper):
     def get_iq_get_handlers():
        """Returns iterable over (element_name, namespace) tuples.

        The tuples will be used as arguments for `Stream.set_iq_get_handler`."""
     def get_iq_set_handlers():
        """Returns iterable over (element_name, namespace) tuples.

        The tuples will be used as arguments for `Stream.set_iq_set_handler`."""

class IStanzaHandlersProvider(IPresenceHandlersProvider, IMessageHandlersProvider, IIqHandlersProvider):
    pass

class IFeaturesProvider(IPyXMPPHelper):
    def get_features():
        """Return iterable of namespaces (features) supported, for disco#info
        query response."""


__all__ = [ name for name in dir() if name.startswith("I") and name != "Interface" ]

# vi: sts=4 et sw=4
