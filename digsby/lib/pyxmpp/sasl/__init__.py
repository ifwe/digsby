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
"""SASL authentication implementaion for PyXMPP.

Normative reference:
  - `RFC 2222 <http://www.ietf.org/rfc/rfc2222.txt>`__
"""

__revision__="$Id: __init__.py 720 2010-04-20 10:31:35Z jajcus $"
__docformat__="restructuredtext en"

import random

from pyxmpp.sasl.core import Reply,Response,Challenge,Success,Failure,PasswordManager

from pyxmpp.sasl.plain import PlainClientAuthenticator,PlainServerAuthenticator
from pyxmpp.sasl.digest_md5 import DigestMD5ClientAuthenticator,DigestMD5ServerAuthenticator
from pyxmpp.sasl.external import ExternalClientAuthenticator

safe_mechanisms_dict={"DIGEST-MD5":(DigestMD5ClientAuthenticator,DigestMD5ServerAuthenticator),
                      "EXTERNAL":(ExternalClientAuthenticator, None)}
try:
    from pyxmpp.sasl.gssapi import GSSAPIClientAuthenticator
except ImportError:
    pass # Kerberos not available
else:
    safe_mechanisms_dict["GSSAPI"] = (GSSAPIClientAuthenticator,None)
unsafe_mechanisms_dict={"PLAIN":(PlainClientAuthenticator,PlainServerAuthenticator)}
all_mechanisms_dict=safe_mechanisms_dict.copy()
all_mechanisms_dict.update(unsafe_mechanisms_dict)

safe_mechanisms=safe_mechanisms_dict.keys()
unsafe_mechanisms=unsafe_mechanisms_dict.keys()
all_mechanisms=safe_mechanisms+unsafe_mechanisms

def client_authenticator_factory(mechanism,password_manager):
    """Create a client authenticator object for given SASL mechanism and
    password manager.

    :Parameters:
        - `mechanism`: name of the SASL mechanism ("PLAIN", "DIGEST-MD5" or "GSSAPI").
        - `password_manager`: name of the password manager object providing
          authentication credentials.
    :Types:
        - `mechanism`: `str`
        - `password_manager`: `PasswordManager`

    :return: new authenticator.
    :returntype: `sasl.core.ClientAuthenticator`"""
    authenticator=all_mechanisms_dict[mechanism][0]
    return authenticator(password_manager)

def server_authenticator_factory(mechanism,password_manager):
    """Create a server authenticator object for given SASL mechanism and
    password manager.

    :Parameters:
        - `mechanism`: name of the SASL mechanism ("PLAIN", "DIGEST-MD5" or "GSSAPI").
        - `password_manager`: name of the password manager object to be used
          for authentication credentials verification.
    :Types:
        - `mechanism`: `str`
        - `password_manager`: `PasswordManager`

    :return: new authenticator.
    :returntype: `sasl.core.ServerAuthenticator`"""
    authenticator=all_mechanisms_dict[mechanism][1]
    return authenticator(password_manager)

# vi: sts=4 et sw=4
