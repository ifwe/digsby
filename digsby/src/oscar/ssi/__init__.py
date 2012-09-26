import oscar

ssi_types = {0x0000:'Buddy record (name: uin for ICQ and screenname for AIM)',
             0x0001:'Group record',
             0x0002:'Permit record ("Allow" list in AIM, and "Visible" list in ICQ)',
             0x0003:'Deny record ("Block" list in AIM, and "Invisible" list in ICQ)',
             0x0004:'Permit/deny settings or/and bitmask of the AIM classes',
             0x0005:'Presence info (if others can see your idle status, etc)',
             0x0009:'Unknown. ICQ2k shortcut bar items ?',
             0x000E:'Ignore list record.',
             0x000F:'Last update date (name: "LastUpdateDate").',
             0x0010:'Non-ICQ contact (to send SMS). Name: 1#EXT, 2#EXT, etc',
             0x0013:'Item that contain roster import time (name: "Import time")',
             0x0014:'Own icon (avatar) info. Name is an avatar id number as text',
             0x0017:'Linked screen name order',
             0x0018:'Linked screenname',
             0x001c:'Facebook group?',
            }

ssi_tlv_types = {0x00C8:'Group Header',
                 0x00CA:'Privacy Settings',
                 0x00CB:'bitmask of visibility to user classes',
                 0x00CC:'bitmask of what other users can see',
                 0x0131:'Alias',
                 0x0137:'email address',
                 0x013A:'SMS number',
                 0x013C:'buddy comment',
                 0x013D:'Alert settings',
                 0x013E:'Alert sound'
                }

buddy_types = {0x0000:"Buddy",
               0x0001:"Group",
               0x0002:"Allow/Visible",
               0x0003:"Block/InvisibleTo",
               0x0004:"Permit/deny settings",
               0x0005:"Presence info",
               0x0009:"Unknown",
               0x000E:"Ignore list record",
               0x000F:"LastUpdateDate",
               0x0010:"Non-ICQ contact (to send SMS)",
               0x0013:"Roster Import time",
               0x0014:"Self icon info. Name is an avatar id number as text",
               0x0017:'Linked screen name order',
               0x0018:'Linked screenname',
               0x0019:'Virtual Contact Metadata',
               0x001C:'Virtual Group Metadata',
               }

ssi_err_types = {
                 # TODO: (maybe): import official list from http://dev.aol.com/aim/oscar/#FEEDBAG__STATUS_CODES
                 #       except... some of them use wording like "Some kind of database error". great.
                 0x0000:"No errors (success)",
                 0x0001:'Unknown error (0x01)', # Dont know what this is, got it on release-eve
                 0x0002:"Item you want to modify not found in list",
                 0x0003:"Item you want to add already exists",
                 0x000A:"Error adding item (invalid id, already in list, invalid data)",
                 0x000C:"Can't add item. Limit for this type of items exceeded",
                 0x000D:"Trying to add ICQ contact to an AIM list",
                 0x000E:"Can't add this contact because it requires authorization",
                 0x0010:"Invalid Login ID",
                }

#
# Blocking / Privacy
#

# Attached to a root group SSI item buddy to indicate it is blocked
deny_flag = 3
permit_flag = 2

# types for privacy settings
privacy_info_types = { "all":1, "invisible":2, "permit":3, "block":4 }

# TLV in SSI for privacy settings
tlv_privacy_settings = 0x0ca

class SSIException(oscar.OscarException): pass

from oscar.ssi.SSIItem import SSIItem as item
from oscar.ssi.SSIItem import OscarSSIs as OscarSSIs
from oscar.ssi.SSIManager import SSIManager as manager
from oscar.ssi.SSIviewer import SSIViewer as viewer
