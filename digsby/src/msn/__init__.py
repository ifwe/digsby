"""

MSN Protocol!

"""
import MSNUtil as util
import MSNClientID
import oim
from MSNCommands import CommandProcessor, Message, MSNTextMessage

from MSNSocket import MSNSocket, MSNSocketBase
from MsnHttpSocket import MsnHttpSocket
import MSNBuddies
from MSN import MSNClient as protocol
from MSNConversation import MSNConversation as Conversation

from MSNBuddy import MSNBuddy as buddy
from MSNBuddy import MSNContact as Contact
from MSNErrcodes import codes as error_codes
from MSNObject import MSNObject
import P2P
import MSNCommands

from p import Notification
from NSSBAdapter import NSSBAdapter


class MSNException(Exception):
    def __init__(self, code, *args):
        if isinstance(code, basestring):
            try:
                code = int(code)
            except (ValueError,):
                code = 100
        elif isinstance(code, message):
            code = code.error_code
            assert not args
        else:
            from util.primitives.funcs import isint
            assert isint(code)

        msg = error_codes.get(code, 'Unknown')
        Exception.__init__(self, code, msg, *args)
exception = MSNException

class LoginException(Exception): pass
class GeneralException(Exception): pass
class WrongVersionException(Exception): pass

errors = (LoginException, GeneralException, MSNException, WrongVersionException)
