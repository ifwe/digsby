'''
OSCAR is the protocol used by AIM and ICQ.
'''
from common.Protocol import ProtocolException
class OscarException(ProtocolException): pass

import capabilities
from oscar.OscarSocket import OscarSocket as socket
from oscar.OscarConversation import OscarConversation as conversation
from oscar.OscarBuddies import OscarBuddies as buddies
from oscar.OscarBuddies import OscarBuddy as buddy
import oscar.OscarUtil as util
from oscar.OscarUtil import apply_format as unpack, decode
from OscarProtocol import SnacQueue, LoginError, ScreennameError, RedirectError
from oscar.snac import SnacError
from oscar.ssi import SSIException

import snac

from oscar.OscarProtocol import OscarProtocol as protocol

errors = (OscarException)

auth_errcode = {
  0x0001:       "Invalid nick or password",
  0x0002:       "Service temporarily unavailable",
  0x0003:       "All other errors",
  0x0004:       "Incorrect screenname or password.",
  0x0005:       "The username and password you entered do not match.",
  0x0006:       "Internal client error (bad input to authorizer)",
  0x0007:       "Invalid account",
  0x0008:       "Deleted account",
  0x0009:       "Expired account",
  0x000A:       "No access to database",
  0x000B:       "No access to resolver",
  0x000C:       "Invalid database fields",
  0x000D:       "Bad database status",
  0x000E:       "Bad resolver status",
  0x000F:       "Internal error",
  0x0010:       "Service temporarily offline",
  0x0011:       "Suspended account",
  0x0012:       "DB send error",
  0x0013:       "DB link error",
  0x0014:       "Reservation map error",
  0x0015:       "Reservation link error",
  0x0016:       "The users num connected from this IP has reached the maximum",
  0x0017:       "The users num connected from this IP has reached the maximum (reservation)",
  0x0018:       "You are trying to connect too frequently. Please try to reconnect in a few minutes.",
  0x0019:       "User too heavily warned",
  0x001A:       "Reservation timeout",
  0x001B:       "You are using an older version of ICQ. Upgrade required",
  0x001C:       "You are using an older version of ICQ. Upgrade recommended",
  0x001D:       "Rate limit exceeded. Please try to reconnect in a few minutes",
  0x001E:       "Can't register on the ICQ network. Reconnect in a few minutes",
  0x0020:       "Invalid SecurID",
  0x0022:       "Account suspended because of your age (age < 13)"
}

def _lowerstrip(name):
    if isinstance(name, bytes):
        name = name.decode('utf8')

    if not isinstance(name, unicode):
        # not a string?
        return name

    name = ''.join(name.split())
    name = name.lower()
    name = name.encode('utf8')

    return name

