#
# (C) Copyright 2008 Jelmer Vernooij <jelmer@samba.org>
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
"""GSSAPI authentication mechanism for PyXMPP SASL implementation.

Normative reference:
  - `RFC 4752 <http://www.ietf.org/rfc/rfc4752.txt>`__
"""

__revision__="$Id$"
__docformat__="restructuredtext en"

import base64
import kerberos

import logging

from pyxmpp.sasl.core import (ClientAuthenticator,Failure,Response,Challenge,Success)

class GSSAPIClientAuthenticator(ClientAuthenticator):
    """Provides client-side GSSAPI SASL (Kerberos 5) authentication."""

    def __init__(self,password_manager):
        ClientAuthenticator.__init__(self, password_manager)
        self.password_manager = password_manager
        self.__logger = logging.getLogger("pyxmpp.sasl.gssapi.GSSAPIClientAuthenticator")

    def start(self, username, authzid):
        self.username = username
        self.authzid = authzid
        rc, self._gss = kerberos.authGSSClientInit(authzid or "%s@%s" % ("xmpp", self.password_manager.get_serv_host()))
        self.step = 0
        return self.challenge("")

    def challenge(self, challenge):
        if self.step == 0:
            rc = kerberos.authGSSClientStep(self._gss, base64.b64encode(challenge))
            if rc != kerberos.AUTH_GSS_CONTINUE:
                self.step = 1
        elif self.step == 1:
            rc = kerberos.authGSSClientUnwrap(self._gss, base64.b64encode(challenge))
            response = kerberos.authGSSClientResponse(self._gss)
            rc = kerberos.authGSSClientWrap(self._gss, response, self.username)
        response = kerberos.authGSSClientResponse(self._gss)
        if response is None:
            return Response("")
        else:
            return Response(base64.b64decode(response))

    def finish(self, data):
        self.username = kerberos.authGSSClientUserName(self._gss)
        self.__logger.debug("Authenticated as %s" % kerberos.authGSSClientUserName(self._gss))
        return Success(self.username,None,self.authzid)


# vi: sts=4 et sw=4
