#
# (C) Copyright 2009 Michal Witkowski <neuro@o2.pl>
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
"""External SASL authentication mechanism for PyXMPP SASL implementation.

Normative reference:
  - `RFC 3920bis <http://xmpp.org/internet-drafts/draft-saintandre-rfc3920bis-08.html#security>`__
  - `XEP-0178 <http://xmpp.org/extensions/xep-0178.html#c2s>__`
"""

__revision__="$Id$"
__docformat__="restructuredtext en"

import base64

import logging

from pyxmpp.sasl.core import (ClientAuthenticator,Failure,Response,Challenge,Success)

class ExternalClientAuthenticator(ClientAuthenticator):
    """Provides client-side External SASL (TLS-Identify) authentication."""
    
    
    def __init__(self,password_manager):
        ClientAuthenticator.__init__(self, password_manager)
        self.password_manager = password_manager
        self.__logger = logging.getLogger("pyxmpp.sasl.external.ExternalClientAuthenticator")

    def start(self, username, authzid):
        self.username = username
        self.authzid = authzid
        # TODO: This isn't very XEP-0178'ish.
        # XEP-0178 says "=" should be sent when only one id-on-xmppAddr is 
        # in the cert, but we don't know that. Still, this conforms to the
        # standard and works.
        return Response(self.authzid, encode = True)
        #return Response("=", encode = False)

    def finish(self,data):
        """Handle authentication success information from the server.

        :Parameters:
            - `data`: the optional additional data returned with the success.
        :Types:
            - `data`: `str`

        :return: a success indicator.
        :returntype: `Success`"""
        _unused = data
        return Success(self.username,None,self.authzid)

# vi: sts=4 et sw=4
