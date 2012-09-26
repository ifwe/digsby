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
"""DIGEST-MD5 authentication mechanism for PyXMPP SASL implementation.

Normative reference:
  - `RFC 2831 <http://www.ietf.org/rfc/rfc2831.txt>`__
"""

__revision__="$Id: digest_md5.py 703 2010-04-03 17:45:43Z jajcus $"
__docformat__="restructuredtext en"

from binascii import b2a_hex
import re
import logging

import hashlib

from pyxmpp.sasl.core import ClientAuthenticator,ServerAuthenticator
from pyxmpp.sasl.core import Failure,Response,Challenge,Success,Failure

from pyxmpp.utils import to_utf8,from_utf8

quote_re=re.compile(r"(?<!\\)\\(.)")

def _unquote(s):
    """Unquote quoted value from DIGEST-MD5 challenge or response.

    If `s` doesn't start or doesn't end with '"' then return it unchanged,
    remove the quotes and escape backslashes otherwise.

    :Parameters:
        - `s`: a quoted string.
    :Types:
        - `s`: `str`

    :return: the unquoted string.
    :returntype: `str`"""
    if not s.startswith('"') or not s.endswith('"'):
        return s
    return quote_re.sub(r"\1",s[1:-1])

def _quote(s):
    """Prepare a string for quoting for DIGEST-MD5 challenge or response.

    Don't add the quotes, only escape '"' and "\\" with backslashes.

    :Parameters:
        - `s`: a raw string.
    :Types:
        - `s`: `str`

    :return: `s` with '"' and "\\" escaped using "\\".
    :returntype: `str`"""
    s=s.replace('\\','\\\\')
    s=s.replace('"','\\"')
    return '%s' % (s,)

def _h_value(s):
    """H function of the DIGEST-MD5 algorithm (MD5 sum).

    :Parameters:
        - `s`: a string.
    :Types:
        - `s`: `str`

    :return: MD5 sum of the string.
    :returntype: `str`"""
    return hashlib.md5(s).digest()

def _kd_value(k,s):
    """KD function of the DIGEST-MD5 algorithm.

    :Parameters:
        - `k`: a string.
        - `s`: a string.
    :Types:
        - `k`: `str`
        - `s`: `str`

    :return: MD5 sum of the strings joined with ':'.
    :returntype: `str`"""
    return _h_value("%s:%s" % (k,s))

def _make_urp_hash(username,realm,password):
    """Compute MD5 sum of username:realm:password.

    :Parameters:
        - `username`: a username.
        - `realm`: a realm.
        - `passwd`: a password.
    :Types:
        - `username`: `str`
        - `realm`: `str`
        - `passwd`: `str`

    :return: the MD5 sum of the parameters joined with ':'.
    :returntype: `str`"""
    if realm is None:
        realm=""
    if type(password) is unicode:
        password=password.encode("utf-8")
    return _h_value("%s:%s:%s" % (username,realm,password))

def _compute_response(urp_hash,nonce,cnonce,nonce_count,authzid,digest_uri):
    """Compute DIGEST-MD5 response value.

    :Parameters:
        - `urp_hash`: MD5 sum of username:realm:password.
        - `nonce`: nonce value from a server challenge.
        - `cnonce`: cnonce value from the client response.
        - `nonce_count`: nonce count value.
        - `authzid`: authorization id.
        - `digest_uri`: digest-uri value.
    :Types:
        - `urp_hash`: `str`
        - `nonce`: `str`
        - `nonce_count`: `int`
        - `authzid`: `str`
        - `digest_uri`: `str`

    :return: the computed response value.
    :returntype: `str`"""
    if authzid:
        a1="%s:%s:%s:%s" % (urp_hash,nonce,cnonce,authzid)
    else:
        a1="%s:%s:%s" % (urp_hash,nonce,cnonce)
    a2="AUTHENTICATE:"+digest_uri
    return b2a_hex(_kd_value( b2a_hex(_h_value(a1)),"%s:%s:%s:%s:%s" % (
            nonce,nonce_count,
            cnonce,"auth",b2a_hex(_h_value(a2)) ) ))

def _compute_response_auth(urp_hash,nonce,cnonce,nonce_count,authzid,digest_uri):
    """Compute DIGEST-MD5 rspauth value.

    :Parameters:
        - `urp_hash`: MD5 sum of username:realm:password.
        - `nonce`: nonce value from a server challenge.
        - `cnonce`: cnonce value from the client response.
        - `nonce_count`: nonce count value.
        - `authzid`: authorization id.
        - `digest_uri`: digest-uri value.
    :Types:
        - `urp_hash`: `str`
        - `nonce`: `str`
        - `nonce_count`: `int`
        - `authzid`: `str`
        - `digest_uri`: `str`

    :return: the computed rspauth value.
    :returntype: `str`"""
    if authzid:
        a1="%s:%s:%s:%s" % (urp_hash,nonce,cnonce,authzid)
    else:
        a1="%s:%s:%s" % (urp_hash,nonce,cnonce)
    a2=":"+digest_uri
    return b2a_hex(_kd_value( b2a_hex(_h_value(a1)),"%s:%s:%s:%s:%s" % (
            nonce,nonce_count,
            cnonce,"auth",b2a_hex(_h_value(a2)) ) ))

_param_re=re.compile(r'^(?P<var>[^=]+)\=(?P<val>(\"(([^"\\]+)|(\\\")'
        r'|(\\\\))+\")|([^",]+))(\s*\,\s*(?P<rest>.*))?$')

class DigestMD5ClientAuthenticator(ClientAuthenticator):
    """Provides PLAIN SASL authentication for a client.

    :Ivariables:
        - `password`: current authentication password
        - `pformat`: current authentication password format
        - `realm`: current authentication realm
    """

    def __init__(self,password_manager):
        """Initialize a `DigestMD5ClientAuthenticator` object.

        :Parameters:
            - `password_manager`: name of the password manager object providing
              authentication credentials.
        :Types:
            - `password_manager`: `PasswordManager`"""
        ClientAuthenticator.__init__(self,password_manager)
        self.username=None
        self.rspauth_checked=None
        self.response_auth=None
        self.authzid=None
        self.pformat=None
        self.realm=None
        self.password=None
        self.nonce_count=None
        self.__logger=logging.getLogger("pyxmpp.sasl.DigestMD5ClientAuthenticator")

    def start(self,username,authzid):
        """Start the authentication process initializing client state.

        :Parameters:
            - `username`: username (authentication id).
            - `authzid`: authorization id.
        :Types:
            - `username`: `unicode`
            - `authzid`: `unicode`

        :return: the (empty) initial response
        :returntype: `sasl.Response` or `sasl.Failure`"""
        self.username=from_utf8(username)
        if authzid:
            self.authzid=from_utf8(authzid)
        else:
            self.authzid=""
        self.password=None
        self.pformat=None
        self.nonce_count=0
        self.response_auth=None
        self.rspauth_checked=0
        self.realm=None
        return Response()

    def challenge(self,challenge):
        """Process a challenge and return the response.

        :Parameters:
            - `challenge`: the challenge from server.
        :Types:
            - `challenge`: `str`

        :return: the response or a failure indicator.
        :returntype: `sasl.Response` or `sasl.Failure`"""
        if not challenge:
            self.__logger.debug("Empty challenge")
            return Failure("bad-challenge")
        challenge=challenge.split('\x00')[0] # workaround for some buggy implementations
        if self.response_auth:
            return self._final_challenge(challenge)
        realms=[]
        nonce=None
        charset="iso-8859-1"
        while challenge:
            m=_param_re.match(challenge)
            if not m:
                self.__logger.debug("Challenge syntax error: %r" % (challenge,))
                return Failure("bad-challenge")
            challenge=m.group("rest")
            var=m.group("var")
            val=m.group("val")
            self.__logger.debug("%r: %r" % (var,val))
            if var=="realm":
                realms.append(_unquote(val))
            elif var=="nonce":
                if nonce:
                    self.__logger.debug("Duplicate nonce")
                    return Failure("bad-challenge")
                nonce=_unquote(val)
            elif var=="qop":
                qopl=_unquote(val).split(",")
                if "auth" not in qopl:
                    self.__logger.debug("auth not supported")
                    return Failure("not-implemented")
            elif var=="charset":
                val = _unquote(val)
                if val!="utf-8":
                    self.__logger.debug("charset given and not utf-8")
                    return Failure("bad-challenge")
                charset="utf-8"
            elif var=="algorithm":
                val = _unquote(val)
                if val!="md5-sess":
                    self.__logger.debug("algorithm given and not md5-sess")
                    return Failure("bad-challenge")
        if not nonce:
            self.__logger.debug("nonce not given")
            return Failure("bad-challenge")
        self._get_password()
        return self._make_response(charset,realms,nonce)

    def _get_password(self):
        """Retrieve user's password from the password manager.

        Set `self.password` to the password and `self.pformat`
        to its format name ('plain' or 'md5:user:realm:pass')."""
        if self.password is None:
            self.password,self.pformat=self.password_manager.get_password(
                        self.username,["plain","md5:user:realm:pass"])
        if not self.password or self.pformat not in ("plain","md5:user:realm:pass"):
            self.__logger.debug("Couldn't get plain password. Password: %r Format: %r"
                            % (self.password,self.pformat))
            return Failure("password-unavailable")

    def _make_response(self,charset,realms,nonce):
        """Make a response for the first challenge from the server.

        :Parameters:
            - `charset`: charset name from the challenge.
            - `realms`: realms list from the challenge.
            - `nonce`: nonce value from the challenge.
        :Types:
            - `charset`: `str`
            - `realms`: `str`
            - `nonce`: `str`

        :return: the response or a failure indicator.
        :returntype: `sasl.Response` or `sasl.Failure`"""
        params=[]
        realm=self._get_realm(realms,charset)
        if isinstance(realm,Failure):
            return realm
        elif realm:
            realm=_quote(realm)
            params.append('realm="%s"' % (realm,))

        try:
            username=self.username.encode(charset)
        except UnicodeError:
            self.__logger.debug("Couldn't encode username to %r" % (charset,))
            return Failure("incompatible-charset")

        username=_quote(username)
        params.append('username="%s"' % (username,))

        cnonce=self.password_manager.generate_nonce()
        cnonce=_quote(cnonce)
        params.append('cnonce="%s"' % (cnonce,))

        params.append('nonce="%s"' % (_quote(nonce),))

        self.nonce_count+=1
        nonce_count="%08x" % (self.nonce_count,)
        params.append('nc=%s' % (nonce_count,))

        params.append('qop=auth')

        serv_type=self.password_manager.get_serv_type().encode("us-ascii")
        host=self.password_manager.get_serv_host().encode("us-ascii")
        serv_name=self.password_manager.get_serv_name().encode("us-ascii")

        if serv_name and serv_name != host:
            digest_uri="%s/%s/%s" % (serv_type,host,serv_name)
        else:
            digest_uri="%s/%s" % (serv_type,host)

        digest_uri=_quote(digest_uri)
        params.append('digest-uri="%s"' % (digest_uri,))

        if self.authzid:
            try:
                authzid=self.authzid.encode(charset)
            except UnicodeError:
                self.__logger.debug("Couldn't encode authzid to %r" % (charset,))
                return Failure("incompatible-charset")
            authzid=_quote(authzid)
        else:
            authzid=""

        if self.pformat=="md5:user:realm:pass":
            urp_hash=self.password
        else:
            urp_hash=_make_urp_hash(username,realm,self.password)

        response=_compute_response(urp_hash,nonce,cnonce,nonce_count,
                            authzid,digest_uri)
        self.response_auth=_compute_response_auth(urp_hash,nonce,cnonce,
                            nonce_count,authzid,digest_uri)
        params.append('response=%s' % (response,))
        if authzid:
            params.append('authzid="%s"' % (authzid,))
        return Response(",".join(params))

    def _get_realm(self,realms,charset):
        """Choose a realm from the list specified by the server.

        :Parameters:
            - `realms`: the realm list.
            - `charset`: encoding of realms on the list.
        :Types:
            - `realms`: `list` of `str`
            - `charset`: `str`

        :return: the realm chosen or a failure indicator.
        :returntype: `str` or `Failure`"""
        if realms:
            realms=[unicode(r,charset) for r in realms]
            realm=self.password_manager.choose_realm(realms)
        else:
            realm=self.password_manager.choose_realm([])
        if realm:
            if type(realm) is unicode:
                try:
                    realm=realm.encode(charset)
                except UnicodeError:
                    self.__logger.debug("Couldn't encode realm to %r" % (charset,))
                    return Failure("incompatible-charset")
            elif charset!="utf-8":
                try:
                    realm=unicode(realm,"utf-8").encode(charset)
                except UnicodeError:
                    self.__logger.debug("Couldn't encode realm from utf-8 to %r"
                                        % (charset,))
                    return Failure("incompatible-charset")
            self.realm=realm
        return realm

    def _final_challenge(self,challenge):
        """Process the second challenge from the server and return the response.

        :Parameters:
            - `challenge`: the challenge from server.
        :Types:
            - `challenge`: `str`

        :return: the response or a failure indicator.
        :returntype: `sasl.Response` or `sasl.Failure`"""
        if self.rspauth_checked:
            return Failure("extra-challenge")
        challenge=challenge.split('\x00')[0]
        rspauth=None
        while challenge:
            m=_param_re.match(challenge)
            if not m:
                self.__logger.debug("Challenge syntax error: %r" % (challenge,))
                return Failure("bad-challenge")
            challenge=m.group("rest")
            var=m.group("var")
            val=m.group("val")
            self.__logger.debug("%r: %r" % (var,val))
            if var=="rspauth":
                rspauth=val
        if not rspauth:
            self.__logger.debug("Final challenge without rspauth")
            return Failure("bad-success")
        if rspauth==self.response_auth:
            self.rspauth_checked=1
            return Response("")
        else:
            self.__logger.debug("Wrong rspauth value - peer is cheating?")
            self.__logger.debug("my rspauth: %r" % (self.response_auth,))
            return Failure("bad-success")

    def finish(self,data):
        """Process success indicator from the server.

        Process any addiitional data passed with the success.
        Fail if the server was not authenticated.

        :Parameters:
            - `data`: an optional additional data with success.
        :Types:
            - `data`: `str`

        :return: success or failure indicator.
        :returntype: `sasl.Success` or `sasl.Failure`"""
        if not self.response_auth:
            self.__logger.debug("Got success too early")
            return Failure("bad-success")
        if self.rspauth_checked:
            return Success(self.username,self.realm,self.authzid)
        else:
            r = self._final_challenge(data)
            if isinstance(r, Failure):
                return r
            if self.rspauth_checked:
                return Success(self.username,self.realm,self.authzid)
            else:
                self.__logger.debug("Something went wrong when processing additional data with success?")
                return Failure("bad-success")

class DigestMD5ServerAuthenticator(ServerAuthenticator):
    """Provides DIGEST-MD5 SASL authentication for a server."""

    def __init__(self,password_manager):
        """Initialize a `DigestMD5ServerAuthenticator` object.

        :Parameters:
            - `password_manager`: name of the password manager object providing
              authentication credential verification.
        :Types:
            - `password_manager`: `PasswordManager`"""
        ServerAuthenticator.__init__(self,password_manager)
        self.nonce=None
        self.username=None
        self.realm=None
        self.authzid=None
        self.done=None
        self.last_nonce_count=None
        self.__logger=logging.getLogger("pyxmpp.sasl.DigestMD5ServerAuthenticator")

    def start(self,response):
        """Start the authentication process.

        :Parameters:
            - `response`: the initial response from the client (empty for
              DIGEST-MD5).
        :Types:
            - `response`: `str`

        :return: a challenge, a success indicator or a failure indicator.
        :returntype: `sasl.Challenge`, `sasl.Success` or `sasl.Failure`"""
        _unused = response
        self.last_nonce_count=0
        params=[]
        realms=self.password_manager.get_realms()
        if realms:
            self.realm=_quote(realms[0])
            for r in realms:
                r=_quote(r)
                params.append('realm="%s"' % (r,))
        else:
            self.realm=None
        nonce=_quote(self.password_manager.generate_nonce())
        self.nonce=nonce
        params.append('nonce="%s"' % (nonce,))
        params.append('qop="auth"')
        params.append('charset=utf-8')
        params.append('algorithm=md5-sess')
        self.authzid=None
        self.done=0
        return Challenge(",".join(params))

    def response(self,response):
        """Process a client reponse.

        :Parameters:
            - `response`: the response from the client.
        :Types:
            - `response`: `str`

        :return: a challenge, a success indicator or a failure indicator.
        :returntype: `sasl.Challenge`, `sasl.Success` or `sasl.Failure`"""
        if self.done:
            return Success(self.username,self.realm,self.authzid)
        if not response:
            return Failure("not-authorized")
        return self._parse_response(response)

    def _parse_response(self,response):
        """Parse a client reponse and pass to further processing.

        :Parameters:
            - `response`: the response from the client.
        :Types:
            - `response`: `str`

        :return: a challenge, a success indicator or a failure indicator.
        :returntype: `sasl.Challenge`, `sasl.Success` or `sasl.Failure`"""
        response=response.split('\x00')[0] # workaround for some SASL implementations
        if self.realm:
            realm=to_utf8(self.realm)
            realm=_quote(realm)
        else:
            realm=None
        username=None
        cnonce=None
        digest_uri=None
        response_val=None
        authzid=None
        nonce_count=None
        while response:
            m=_param_re.match(response)
            if not m:
                self.__logger.debug("Response syntax error: %r" % (response,))
                return Failure("not-authorized")
            response=m.group("rest")
            var=m.group("var")
            val=m.group("val")
            self.__logger.debug("%r: %r" % (var,val))
            if var=="realm":
                realm=val[1:-1]
            elif var=="cnonce":
                if cnonce:
                    self.__logger.debug("Duplicate cnonce")
                    return Failure("not-authorized")
                cnonce=val[1:-1]
            elif var=="qop":
                if val!='auth':
                    self.__logger.debug("qop other then 'auth'")
                    return Failure("not-authorized")
            elif var=="digest-uri":
                digest_uri=val[1:-1]
            elif var=="authzid":
                authzid=val[1:-1]
            elif var=="username":
                username=val[1:-1]
            elif var=="response":
                response_val=val
            elif var=="nc":
                nonce_count=val
                self.last_nonce_count+=1
                if int(nonce_count)!=self.last_nonce_count:
                    self.__logger.debug("bad nonce: %r != %r"
                            % (nonce_count,self.last_nonce_count))
                    return Failure("not-authorized")
        return self._check_params(username,realm,cnonce,digest_uri,
                response_val,authzid,nonce_count)

    def _check_params(self,username,realm,cnonce,digest_uri,
            response_val,authzid,nonce_count):
        """Check parameters of a client reponse and pass them to further
        processing.

        :Parameters:
            - `username`: user name.
            - `realm`: realm.
            - `cnonce`: cnonce value.
            - `digest_uri`: digest-uri value.
            - `response_val`: response value computed by the client.
            - `authzid`: authorization id.
            - `nonce_count`: nonce count value.
        :Types:
            - `username`: `str`
            - `realm`: `str`
            - `cnonce`: `str`
            - `digest_uri`: `str`
            - `response_val`: `str`
            - `authzid`: `str`
            - `nonce_count`: `int`

        :return: a challenge, a success indicator or a failure indicator.
        :returntype: `sasl.Challenge`, `sasl.Success` or `sasl.Failure`"""
        if not cnonce:
            self.__logger.debug("Required 'cnonce' parameter not given")
            return Failure("not-authorized")
        if not response_val:
            self.__logger.debug("Required 'response' parameter not given")
            return Failure("not-authorized")
        if not username:
            self.__logger.debug("Required 'username' parameter not given")
            return Failure("not-authorized")
        if not digest_uri:
            self.__logger.debug("Required 'digest_uri' parameter not given")
            return Failure("not-authorized")
        if not nonce_count:
            self.__logger.debug("Required 'nc' parameter not given")
            return Failure("not-authorized")
        return self._make_final_challenge(username,realm,cnonce,digest_uri,
                response_val,authzid,nonce_count)

    def _make_final_challenge(self,username,realm,cnonce,digest_uri,
            response_val,authzid,nonce_count):
        """Send the second challenge in reply to the client response.

        :Parameters:
            - `username`: user name.
            - `realm`: realm.
            - `cnonce`: cnonce value.
            - `digest_uri`: digest-uri value.
            - `response_val`: response value computed by the client.
            - `authzid`: authorization id.
            - `nonce_count`: nonce count value.
        :Types:
            - `username`: `str`
            - `realm`: `str`
            - `cnonce`: `str`
            - `digest_uri`: `str`
            - `response_val`: `str`
            - `authzid`: `str`
            - `nonce_count`: `int`

        :return: a challenge, a success indicator or a failure indicator.
        :returntype: `sasl.Challenge`, `sasl.Success` or `sasl.Failure`"""
        username_uq=from_utf8(username.replace('\\',''))
        if authzid:
            authzid_uq=from_utf8(authzid.replace('\\',''))
        else:
            authzid_uq=None
        if realm:
            realm_uq=from_utf8(realm.replace('\\',''))
        else:
            realm_uq=None
        digest_uri_uq=digest_uri.replace('\\','')
        self.username=username_uq
        self.realm=realm_uq
        password,pformat=self.password_manager.get_password(
                    username_uq,realm_uq,("plain","md5:user:realm:pass"))
        if pformat=="md5:user:realm:pass":
            urp_hash=password
        elif pformat=="plain":
            urp_hash=_make_urp_hash(username,realm,password)
        else:
            self.__logger.debug("Couldn't get password.")
            return Failure("not-authorized")
        valid_response=_compute_response(urp_hash,self.nonce,cnonce,
                            nonce_count,authzid,digest_uri)
        if response_val!=valid_response:
            self.__logger.debug("Response mismatch: %r != %r" % (response_val,valid_response))
            return Failure("not-authorized")
        s=digest_uri_uq.split("/")
        if len(s)==3:
            serv_type,host,serv_name=s
        elif len(s)==2:
            serv_type,host=s
            serv_name=None
        else:
            self.__logger.debug("Bad digest_uri: %r" % (digest_uri_uq,))
            return Failure("not-authorized")
        info={}
        info["mechanism"]="DIGEST-MD5"
        info["username"]=username_uq
        info["serv-type"]=serv_type
        info["host"]=host
        info["serv-name"]=serv_name
        if self.password_manager.check_authzid(authzid_uq,info):
            rspauth=_compute_response_auth(urp_hash,self.nonce,
                            cnonce,nonce_count,authzid,digest_uri)
            self.authzid=authzid
            self.done=1
            return Challenge("rspauth="+rspauth)
        else:
            self.__logger.debug("Authzid check failed")
            return Failure("invalid_authzid")

# vi: sts=4 et sw=4
