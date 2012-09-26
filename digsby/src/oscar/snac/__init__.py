from oscar import OscarException

#
# why not this?
#
#[__import__('oscar.snac.family_%s' % fam)
#    for fam in ['%02x' % x for x in range(1,17)] + \
#               ['13','15','17','22','85']]
#
# '__import__(...)' doesn't do everything 'import ...' does, there's a bit of
# extra work to be done. not a bad idea though.


from family_x01 import *
from family_x02 import *
from family_x03 import *
from family_x04 import *
from family_x05 import *
from family_x06 import *
from family_x07 import *
from family_x08 import *
from family_x09 import *
from family_x0a import *
from family_x0b import *
from family_x0c import *
from family_x0d import *
from family_x0e import *
from family_x0f import *
from family_x10 import *
from family_x13 import *
from family_x15 import *
from family_x17 import *
from family_x22 import *
from family_x25 import *
from family_x85 import *

errcodes = {
          0x01       :"Invalid SNAC header.",
          0x02       :"Server rate limit exceeded",
          0x03       :"Client rate limit exceeded",
          0x04       :"Recipient is not logged in",
          0x05       :"Requested service unavailable",
          0x06       :"Requested service not defined",
          0x07       :"You sent obsolete SNAC",
          0x08       :"Not supported by server",
          0x09       :"Not supported by client",
          0x0A       :"Refused by client",
          0x0B       :"Reply too big",
          0x0C       :"Responses lost", #request denied
          0x0D       :"Request denied",
          0x0E       :"Incorrect SNAC format",
          0x0F       :"Insufficient rights",
          0x10       :"In local permit/deny (recipient blocked)",
          0x11       :"Sender too evil",
          0x12       :"Receiver too evil",
          0x13       :"User temporarily unavailable",
          0x14       :"No match", #item not found
          0x15       :"List overflow", #too many items specified in a list
          0x16       :"Request ambiguous",
          0x17       :"Server queue full",
          0x18       :"Not while on AOL",
          0x1A       :"Timeout",
          0x1C       :"General Failure",
          0x1F       :"Restricted by parental controls",
          0x20       :"Remote user is restricted by parental controls",
          }

class SnacError(OscarException):
    def __init__(self, fam, *args):
        name = getattr(oscar.snac, 'x%02x_name' % fam, None)
        OscarException.__init__(self, (fam, name), *args)

import struct
def error(data):
    errcode, data = oscar.unpack((('err', 'H'),), data)
    from util.primitives.funcs import get
    errmsg = get(errcodes,errcode,'Unknown')

    tlv = None
    if data:
        tlv, data = oscar.unpack((('tlv', 'tlv'),), data)
    # ICQ (family x15) has an additional tlv
    if data:
        tlv2, data = oscar.unpack(('tlv', 'tlv'),data)
    assert not data
    if tlv and tlv.t == 8:
        (subcode,) = struct.unpack('!H', tlv.v)
    else: subcode = None

    return errcode, errmsg, subcode

version, dll_high, dll_low = 1, 0x0110, 0x164f
