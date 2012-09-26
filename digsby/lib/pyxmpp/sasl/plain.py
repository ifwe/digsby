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
"""PLAIN authentication mechanism for PyXMPP SASL implementation.

Normative reference:
  - `RFC 2595 <http://www.ietf.org/rfc/rfc2595.txt>`__
"""

__revision__="$Id: plain.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import logging

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.sasl.core import ClientAuthenticator,ServerAuthenticator
from pyxmpp.sasl.core import Success,Failure,Challenge,Response

class PlainClientAuthenticator(ClientAuthenticator):
    """Provides PLAIN SASL authentication for a client."""

    def __init__(self,password_manager):
        """Initialize a `PlainClientAuthenticator` object.

        :Parameters:
            - `password_manager`: name of the password manager object providing
              authentication credentials.
        :Types:
            - `password_manager`: `PasswordManager`"""
        ClientAuthenticator.__init__(self,password_manager)
        self.username=None
        self.finished=None
        self.password=None
        self.authzid=None
        self.__logger=logging.getLogger("pyxmpp.sasl.PlainClientAuthenticator")

    def start(self,username,authzid):
        """Start the authentication process and return the initial response.

        :Parameters:
            - `username`: username (authentication id).
            - `authzid`: authorization id.
        :Types:
            - `username`: `unicode`
            - `authzid`: `unicode`

        :return: the initial response or a failure indicator.
        :returntype: `sasl.Response` or `sasl.Failure`"""
        self.username=username
        if authzid:
            self.authzid=authzid
        else:
            self.authzid=""
        self.finished=0
        return self.challenge("")

    def challenge(self, challenge):
        """Process the challenge and return the response.

        :Parameters:
            - `challenge`: the challenge.
        :Types:
            - `challenge`: `str`

        :return: the response or a failure indicator.
        :returntype: `sasl.Response` or `sasl.Failure`"""
        _unused = challenge
        if self.finished:
            self.__logger.debug("Already authenticated")
            return Failure("extra-challenge")
        self.finished=1
        if self.password is None:
            self.password,pformat=self.password_manager.get_password(self.username)
        if not self.password or pformat!="plain":
            self.__logger.debug("Couldn't retrieve plain password")
            return Failure("password-unavailable")
        return Response("%s\000%s\000%s" % (    to_utf8(self.authzid),
                            to_utf8(self.username),
                            to_utf8(self.password)))

    def finish(self,data):
        """Handle authentication succes information from the server.

        :Parameters:
            - `data`: the optional additional data returned with the success.
        :Types:
            - `data`: `str`

        :return: a success indicator.
        :returntype: `Success`"""
        _unused = data
        return Success(self.username,None,self.authzid)

class PlainServerAuthenticator(ServerAuthenticator):
    """Provides PLAIN SASL authentication for a server."""

    def __init__(self,password_manager):
        """Initialize a `PlainServerAuthenticator` object.

        :Parameters:
            - `password_manager`: name of the password manager object providing
              authentication credential verification.
        :Types:
            - `password_manager`: `PasswordManager`"""
        ServerAuthenticator.__init__(self,password_manager)
        self.__logger=logging.getLogger("pyxmpp.sasl.PlainServerAuthenticator")

    def start(self,response):
        """Start the authentication process.

        :Parameters:
            - `response`: the initial response from the client.
        :Types:
            - `response`: `str`

        :return: a challenge, a success indicator or a failure indicator.
        :returntype: `sasl.Challenge`, `sasl.Success` or `sasl.Failure`"""
        if not response:
            return Challenge("")
        return self.response(response)

    def response(self,response):
        """Process a client reponse.

        :Parameters:
            - `response`: the response from the client.
        :Types:
            - `response`: `str`

        :return: a challenge, a success indicator or a failure indicator.
        :returntype: `sasl.Challenge`, `sasl.Success` or `sasl.Failure`"""
        s=response.split("\000")
        if len(s)!=3:
            self.__logger.debug("Bad response: %r" % (response,))
            return Failure("not-authorized")
        authzid,username,password=s
        authzid=from_utf8(authzid)
        username=from_utf8(username)
        password=from_utf8(password)
        if not self.password_manager.check_password(username,password):
            self.__logger.debug("Bad password. Response was: %r" % (response,))
            return Failure("not-authorized")
        info={"mechanism":"PLAIN","username":username}
        if self.password_manager.check_authzid(authzid,info):
            return Success(username,None,authzid)
        else:
            self.__logger.debug("Authzid verification failed.")
            return Failure("invalid-authzid")

# vi: sts=4 et sw=4
