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
"""Base classes for PyXMPP SASL implementation.

Normative reference:
  - `RFC 2222 <http://www.ietf.org/rfc/rfc2222.txt>`__
"""
__revision__="$Id: core.py 720 2010-04-20 10:31:35Z jajcus $"
__docformat__="restructuredtext en"

import random
import logging
from binascii import b2a_base64

class PasswordManager:
    """Base class for password managers.

    Password manager is an object responsible for providing or verification
    of authentication credentials.

    All the methods of `PasswordManager` class may be overriden in derived
    classes for specific authentication and authorization policy."""
    def __init__(self):
        """Initialize a `PasswordManager` object."""
        pass

    def get_password(self,username,realm=None,acceptable_formats=("plain",)):
        """Get the password for user authentication.

        [both client or server]

        By default returns (None, None) providing no password. Should be
        overriden in derived classes.

        :Parameters:
            - `username`: the username for which the password is requested.
            - `realm`: the authentication realm for which the password is
              requested.
            - `acceptable_formats`: a sequence of acceptable formats of the
              password data. Could be "plain", "md5:user:realm:password" or any
              other mechanism-specific encoding. This allows non-plain-text
              storage of passwords. But only "plain" format will work with
              all password authentication mechanisms.
        :Types:
            - `username`: `unicode`
            - `realm`: `unicode`
            - `acceptable_formats`: sequence of `str`

        :return: the password and its encoding (format).
        :returntype: `unicode`,`str` tuple."""
        _unused, _unused, _unused = username, realm, acceptable_formats
        return None,None

    def check_password(self,username,password,realm=None):
        """Check the password validity.

        [server only]

        Used by plain-text authentication mechanisms.

        Retrieve a "plain" password for the `username` and `realm` using
        `self.get_password` and compare it with the password provided.

        May be overrided e.g. to check the password against some external
        authentication mechanism (PAM, LDAP, etc.).

        :Parameters:
            - `username`: the username for which the password verification is
              requested.
            - `password`: the password to verify.
            - `realm`: the authentication realm for which the password
              verification is requested.
        :Types:
            - `username`: `unicode`
            - `password`: `unicode`
            - `realm`: `unicode`

        :return: `True` if the password is valid.
        :returntype: `bool`"""
        _password,format=self.get_password(username,realm,("plain",))
        if _password and format=="plain" and _password==password:
            return True
        return False

    def get_realms(self):
        """Get available realms list.

        [server only]

        :return: a list of realms available for authentication. May be empty --
            the client may choose its own realm then or use no realm at all.
        :returntype: `list` of `unicode`"""
        return []

    def choose_realm(self,realm_list):
        """Choose an authentication realm from the list provided by the server.

        [client only]

        By default return the first realm from the list or `None` if the list
        is empty.

        :Parameters:
            - `realm_list`: the list of realms provided by a server.
        :Types:
            - `realm_list`: sequence of `unicode`

        :return: the realm chosen.
        :returntype: `unicode`"""
        if realm_list:
            return realm_list[0]
        else:
            return None

    def check_authzid(self,authzid,extra_info=None):
        """Check if the authenticated entity is allowed to use given
        authorization id.

        [server only]

        By default return `True` if the `authzid` is `None` or empty or it is
        equal to extra_info["username"] (if the latter is present).

        :Parameters:
            - `authzid`: an authorization id.
            - `extra_info`: information about an entity got during the
              authentication process. This is a mapping with arbitrary,
              mechanism-dependent items. Common keys are 'username' or
              'realm'.
        :Types:
            - `authzid`: `unicode`
            - `extra_info`: mapping

        :return: `True` if the authenticated entity is authorized to use
            the provided authorization id.
        :returntype: `bool`"""
        if not extra_info:
            extra_info={}
        return (not authzid
                or extra_info.has_key("username")
                        and extra_info["username"]==authzid)

    def get_serv_type(self):
        """Return the service type for DIGEST-MD5 'digest-uri' field.

        Should be overriden in derived classes.

        :return: the service type ("unknown" by default)"""
        return "unknown"

    def get_serv_host(self):
        """Return the host name for DIGEST-MD5 'digest-uri' field.

        Should be overriden in derived classes.

        :return: the host name ("unknown" by default)"""
        return "unknown"

    def get_serv_name(self):
        """Return the service name for DIGEST-MD5 'digest-uri' field.

        Should be overriden in derived classes.

        :return: the service name or `None` (which is the default)."""
        return None

    def generate_nonce(self):
        """Generate a random string for digest authentication challenges.

        The string should be cryptographicaly secure random pattern.

        :return: the string generated.
        :returntype: `str`"""
        # FIXME: use some better RNG (/dev/urandom maybe)
        r1=str(random.random())[2:]
        r2=str(random.random())[2:]
        return r1+r2

class Reply:
    """Base class for SASL authentication reply objects.

    :Ivariables:
        - `data`: optional reply data.
        - `encode`: whether to base64 encode the data or not
    :Types:
        - `data`: `str`
        - `encode`; `bool`"""
    def __init__(self,data="", encode=True):
        """Initialize the `Reply` object.

        :Parameters:
            - `data`: optional reply data.
        :Types:
            - `data`: `str`"""
        self.data=data
        self.encode=encode

    def base64(self):
        """Base64-encode the data contained in the reply.

        :return: base64-encoded data.
        :returntype: `str`"""
        if self.data is not None:
            ret=b2a_base64(self.data)
            if ret[-1]=='\n':
                ret=ret[:-1]
            return ret
        else:
            return None

class Challenge(Reply):
    """The challenge SASL message (server's challenge for the client)."""
    def __init__(self,data):
        """Initialize the `Challenge` object."""
        Reply.__init__(self,data)
    def __repr__(self):
        return "<sasl.Challenge: %r>" % (self.data,)

class Response(Reply):
    """The response SASL message (clients's reply the the server's challenge)."""
    def __init__(self,data="", encode=True):
        """Initialize the `Response` object."""
        Reply.__init__(self,data, encode)
    def __repr__(self):
        return "<sasl.Response: %r>" % (self.data,)

class Failure(Reply):
    """The failure SASL message.

    :Ivariables:
        - `reason`: the failure reason.
    :Types:
        - `reason`: unicode."""
    def __init__(self,reason,encode=True):
        """Initialize the `Failure` object.

        :Parameters:
            - `reason`: the failure reason.
        :Types:
            - `reason`: unicode."""
        Reply.__init__(self,"",encode)
        self.reason=reason
    def __repr__(self):
        return "<sasl.Failure: %r>" % (self.reason,)

class Success(Reply):
    """The success SASL message (sent by the server on authentication success)."""
    def __init__(self,username,realm=None,authzid=None,data=None):
        """Initialize the `Success` object.

        :Parameters:
            - `username`: authenticated username (authentication id).
            - `realm`: authentication realm used.
            - `authzid`: authorization id.
            - `data`: the success data to be sent to the client.
        :Types:
            - `username`: `unicode`
            - `realm`: `unicode`
            - `authzid`: `unicode`
            - `data`: `str`
        """
        Reply.__init__(self,data)
        self.username=username
        self.realm=realm
        self.authzid=authzid
    def __repr__(self):
        return "<sasl.Success: authzid: %r data: %r>" % (self.authzid,self.data)

class ClientAuthenticator:
    """Base class for client authenticators.

    A client authenticator class is a client-side implementation of a SASL
    mechanism. One `ClientAuthenticator` object may be used for one
    client authentication process."""

    def __init__(self,password_manager):
        """Initialize a `ClientAuthenticator` object.

        :Parameters:
            - `password_manager`: a password manager providing authentication
              credentials.
        :Types:
            - `password_manager`: `PasswordManager`"""
        self.password_manager=password_manager
        self.__logger=logging.getLogger("pyxmpp.sasl.ClientAuthenticator")

    def start(self,username,authzid):
        """Start the authentication process.

        :Parameters:
            - `username`: the username (authentication id).
            - `authzid`: the authorization id requester.
        :Types:
            - `username`: `unicode`
            - `authzid`: `unicode`

        :return: the initial response to send to the server or a failuer
            indicator.
        :returntype: `Response` or `Failure`"""
        _unused, _unused = username, authzid
        return Failure("Not implemented")

    def challenge(self,challenge):
        """Process the server's challenge.

        :Parameters:
            - `challenge`: the challenge.
        :Types:
            - `challenge`: `str`

        :return: the response or a failure indicator.
        :returntype: `Response` or `Failure`"""
        _unused = challenge
        return Failure("Not implemented")

    def finish(self,data):
        """Handle authentication succes information from the server.

        :Parameters:
            - `data`: the optional additional data returned with the success.
        :Types:
            - `data`: `str`

        :return: success or failure indicator.
        :returntype: `Success` or `Failure`"""
        _unused = data
        return Failure("Not implemented")

class ServerAuthenticator:
    """Base class for server authenticators.

    A server authenticator class is a server-side implementation of a SASL
    mechanism. One `ServerAuthenticator` object may be used for one
    client authentication process."""

    def __init__(self,password_manager):
        """Initialize a `ServerAuthenticator` object.

        :Parameters:
            - `password_manager`: a password manager providing authentication
              credential verfication.
        :Types:
            - `password_manager`: `PasswordManager`"""
        self.password_manager=password_manager
        self.__logger=logging.getLogger("pyxmpp.sasl.ServerAuthenticator")

    def start(self,initial_response):
        """Start the authentication process.

        :Parameters:
            - `initial_response`: the initial response send by the client with
              the authentication request.

        :Types:
            - `initial_response`: `str`

        :return: a challenge, a success or a failure indicator.
        :returntype: `Challenge` or `Failure` or `Success`"""
        _unused = initial_response
        return Failure("not-authorized")

    def response(self,response):
        """Process a response from a client.

        :Parameters:
            - `response`: the response from the client to our challenge.
        :Types:
            - `response`: `str`

        :return: a challenge, a success or a failure indicator.
        :returntype: `Challenge` or `Success` or `Failure`"""
        _unused = response
        return Failure("not-authorized")

# vi: sts=4 et sw=4
