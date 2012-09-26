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

"""Convenience module containing most important objects from pyxmpp package.

Suggested usage::
import pyxmpp.all

(imports all important names into pyxmpp namespace)"""

"""PyXMPP - Jabber/XMPP protocol implementation"""

__revision__="$Id: __init__.py 477 2004-12-29 13:25:42Z jajcus $"
__docformat__="restructuredtext en"

import pyxmpp

from pyxmpp.stream import Stream
from pyxmpp.streambase import StreamError,FatalStreamError,StreamParseError
from pyxmpp.streamtls import StreamEncryptionRequired,tls_available,TLSSettings
from pyxmpp.clientstream import ClientStream,ClientStreamError
from pyxmpp.client import Client,ClientError
from pyxmpp.iq import Iq
from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.jid import JID,JIDError
from pyxmpp.roster import Roster,RosterItem
from pyxmpp.exceptions import *

for name in dir():
    if not name.startswith("_") and name != "pyxmpp":
        setattr(pyxmpp,name,globals()[name])

# vi: sts=4 et sw=4
