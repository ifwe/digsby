#
# (C) Copyright 2006 Jacek Konieczny <jajcus@jajcus.net>
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

"""Interface API.

If zope.interface is available this module will be its equivalent, otherwise
minimum interface API (partially compatible with zope.interface) will be
defined here. 

When full ZopeInterfaces API is needed impoer zope.interface instead of this module."""

__revision__="$Id: utils.py 647 2006-08-26 18:27:39Z jajcus $"

try:
    from zope.interface import Interface, Attribute, providedBy, implementedBy, implements
except ImportError:
    from pyxmpp.interface_micro_impl import Interface, Attribute, providedBy, implementedBy, implements


__all__ = ("Interface", "Attribute", "providedBy", "implementedBy", "implements")

# vi: sts=4 et sw=4
