from struct import pack
from common import pref

'''
Capabilities utility data. Also contains our client capabilities (enabled_names)

useful: http://micq.alpha345.com/ICQ-OSCAR-Protocol-v7-v8-v9/Define/CAPABILITIES.html
'''

#
# List enabled capabilities here.
#
enabled_names = """
digsby

avatar

ichatav_info

file_xfer

icq_to_aim
utf8_support
xhtml_support
extended_msgs

buddy_list_transfer

chat_service

""".split()



# temporarily removed:
#
# direct_im
# rtf_support

by_name = {}
by_bytes = {}

by_name = dict(

 # Stuff we do support
 avatar                = '094613464c7f11d18222444553540000'    .decode('hex'),
 buddy_list_transfer   = '0946134b4c7f11d18222444553540000'    .decode('hex'),
 file_xfer             = '094613434c7f11d18222444553540000'    .decode('hex'),
 ichatav_info          = '094601054c7f11d18222444545535400'    .decode('hex'),

 # Coming soon!
 chat_service          = '748f2420628711d18222444553540000'    .decode('hex'),

 # Stuff we might support
 file_share            = '094613484c7f11d18222444553540000'    .decode('hex'),
 livevideo             = '094601014c7f11d18222444553540000'    .decode('hex'),
 voice_chat            = '094613414c7f11d18222444553540000'    .decode('hex'),
 camera                = '094601024c7f11d18222444553540000'    .decode('hex'),

 # Stuff we'll probably never support
 games_1               = '0946134a4c7f11d18222444553540000'    .decode('hex'),
 games_2               = '0946134a4c7f11d12282444553540000'    .decode('hex'),
 direct_play           = '094613424c7f11d18222444553540000'    .decode('hex'),
 add_ins               = '094613474c7f11d18222444553540000'    .decode('hex'),

 # Messaging stuff
 icq_to_aim            = '0946134d4c7f11d18222444553540000'    .decode('hex'),
 utf8_support          = '0946134e4c7f11d18222444553540000'    .decode('hex'),
 rtf_support           = '97b12751243c4334ad22d6abf73f1492'    .decode('hex'),
 xhtml_support         = '094600024C7F11D18222444553540000'    .decode('hex'),
 direct_im             = '094613454c7f11d18222444553540000'    .decode('hex'),
 extended_msgs         = '094613494c7f11d18222444553540000'    .decode('hex'), # wtf is this? it's also known as "icq server relay"

 # Other clients
 miranda               = '4d6972616e6461410004033100000002'    .decode('hex'),
 #miranda               = '4d6972616e64614100070a0000070200'    .decode('hex'),
 trillian_encrypt      = 'f2e7c7f4fead4dfbb23536798bdf0000'    .decode('hex'),
 # Us!
 digsby                = 'digsby' + ('\0'*10),

 # Shit we don't know about
 short_caps            = '094600004c7f11d18222444553540000'    .decode('hex'),  # short caps?
 route_finder          = '094613444c7f11d18222444553540000'    .decode('hex'),
 microphone            = '094601034c7f11d18222444553540000'    .decode('hex'),
 multi_audio           = '094601074c7f11d18222444553540000'    .decode('hex'),  # was aim6_unknown1
 rtc_audio             = '094601044c7f11d18222444553540000'    .decode('hex'),
 mtn                   = '563fc8090b6f41bd9f79422609dfa2f3'    .decode('hex'),  # typing notifications
 #icq_direct            = '094613444c7f11d18222444553540000'    .decode('hex'),  # aka 'route_finder'
 icq_lite              = '178c2d9bdaa545bb8ddbf3bdbd53a10a'    .decode('hex'),  # icq lite / was icq6_unknown1
 icq_html_msgs         = '0138ca7b769a491588f213fc00979ea8'    .decode('hex'),  # HTML messages?! / was icq6_unknown2
 icq_xtraz_muc         = '67361515612d4c078f3dbde6408ea041'    .decode('hex'),  # XTraz in multi-user chat / was icq6_unknown3
 icq_xtraz             = '1a093c6cd7fd4ec59d51a6474e34f5a0'    .decode('hex'),  # XTraz / was icq6_unknown4
 icq_tzers             = 'b2ec8f167c6f451bbd79dc58497888b9'    .decode('hex'),  # TZers / was icq6_unknown5
 aim_file_xfer         = '0946134c4c7f11d18222444553540000'    .decode('hex'), # specifies an AIM specific file xfer? trillian sends it.
 secure_im             = '094600014C7F11D18222444553540000'    .decode('hex'),
 new_status_msg        = '0946010A4C7F11D18222444553540000'    .decode('hex'),
 realtime_im           = '0946010B4C7F11D18222444553540000'    .decode('hex'),
 smart_caps            = '094601FF4C7F11D18222444553540000'    .decode('hex'),

 icq7_unknown          = 'C8953A9F21F14FAAB0B26DE663ABF5B7'    .decode('hex'), # if it has this it's either ICQ lite 1.0 or ICQ7

)

by_bytes = dict((v,k) for (k,v) in by_name.items())

feature_capabilities = []

enabled_capabilities = {}.fromkeys(by_name.keys(), False)

for cap in enabled_names:
    assert cap in by_name
    enabled_capabilities[cap] = True

if pref('videochat.report_capability', True):
    enabled_capabilities['livevideo'] = True

for (capability, enabled) in enabled_capabilities.items():
    assert capability in by_name
    if enabled:
        feature_capabilities.append(by_name[capability])

