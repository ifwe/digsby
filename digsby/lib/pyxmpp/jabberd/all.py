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
# pylint: disable-msg=W0611

"""Convenience module containing most important objects fr pyxmpp.jabberd package.

Suggested usage::
import pyxmpp.jabberd.all

(imports all important names into pyxmpp.jabberd namespace)"""

__revision__="$Id: __init__.py 477 2004-12-29 13:25:42Z jajcus $"
__docformat__="restructuredtext en"

import pyxmpp.jabberd

from pyxmpp.jabberd.componentstream import ComponentStream
from pyxmpp.jabberd.component import Component

for name in dir():
    if not name.startswith("__") and name!="pyxmpp":
        setattr(pyxmpp.jabberd,name,globals()[name])

# vi: sts=4 et sw=4
