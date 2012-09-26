'''
Human readable names for Yahoo packet values and dictionary keys.

Incoming packets with Yahoo dictionaries get mapped to function calls with
named arguments via the values in these dictionaries.

i.e., command_status(namedarg1, namedarg2)
'''

from __future__ import with_statement
from util import lookup_table

# The eleventh and twelfth bytes of a YMSG packet header form this network order
# short:
commands = lookup_table(
    logon  =  1,
    logoff = 2,
    isaway = 3,
    isback = 4,
    idle = 5,
    message = 6,
    idact = 7,
    iddeact = 8,
    mailstat = 9,
    userstat = 10,
    newmail = 11,
    chatinvite = 12,
    calendar = 13,
    newpersonalmail = 14,
    newcontact = 15,
    addident = 16,
    addignore = 17,
    ping = 18,
    gotgrouprename = 19, # < 1, 36(old)
    sysmessage  = 20,
    skinname  = 21,
    passthrough2  = 22,
    confinvite  = 24,
    conflogon = 25,
    confdecline = 26,
    conflogoff = 27,
    confaddinvite = 28,
    confmsg = 29,
    chatlogon = 30,
    chatlogoff = 31,
    chatmsg  = 32,
    gamelogon  = 40,
    gamelogoff = 41,
    gamemsg  = 42,
    filetransfer  = 70,
    voicechat  = 74,
    notify = 75,
    verify = 76,
    p2pfilexfer = 77,
    peertopeer  = 79,
    webcam = 80,
    authresp  = 84,
    list = 85,
    auth  = 87,
    addbuddy  = 131,
    rembuddy = 132,
    ignorecontact = 133,    # > 1, 7, 13 < 1, 66, 13
    rejectcontact = 134,
    grouprename  = 137,
    keepalive    = 138,
    chatonline  = 150,
    chatgoto = 151,
    chatjoin = 152,
    chatleave = 153,
    chatexit  = 155,
    chataddinvite  = 157,
    chatlogout  = 160,
    chatping = 161,
    comment  = 168,
    stealth_perm = 185,
    stealth_session = 186,
    avatar  = 188,
    picture_checksum  = 189,
    picture  = 190,
    picture_update  = 193,
    picture_upload  = 194,
    invisible = 197,
    yahoo6_status_update  = 198,
    avatar_update  = 199,
    audible  = 208,
    send_buddylist = 211,
    # send_checksum = 212, # ????
    listallow = 214,

    peerrequest = 220,
    peersetup   = 221,
    peerinit    = 222,

    yahoo360 = 225,
    yahoo360update = 226,
    movebuddy = 231,
    awaylogin = 240,
    list15    = 241,
    msg_ack   = 251,
    weblogin  = 550,
    sms_message = 746,
    sms_login = 748,


)

# Four byte integer following the command.
statuses = lookup_table(
    available=  0,
    brb = 1,
    busy = 2,
    notathome = 3,
    notatdesk = 4,
    notinoffice = 5,
    onphone = 6,
    onvacation = 7,
    outtolunch = 8,
    steppedout = 9,
    invisible  =  12,
    typing = 22,
    custom  =  99,
    idle  =  999,
    weblogin  = 1515563605,
    offline  = 1515563606,
    cancel = -1,
)

#
# Meanings for Yahoo! dictionary keys.
#
# These were not in Ethereal--their meanings are guessed from context alone,
# so they come with the disclaimer that some of them may be totally wrong.
#
# YahooSocket uses these to make named argument calls into YahooProtocol.
#
ykeys = {
    0:   'away_buddy',
    1:   'frombuddy',
    2:   'identity',
    3:   'conf_from',
    4:   'buddy',
    5:   'to',
    6:   'chatflag',
    7:   'contact',
#   8:   ? don't know. appear in logon_brb as 3
    9:   'count',
    10:  'status',
    11:  'session_id',
    12:  'base64ip',
    13:  'flag',
    14:  'message',
    15:  'unix_time',
    16:  'error_message',
    19:  'custom_message',
    20:  'url',
    27:  'filename',
    28:  'filesize',
    29:  'filedata',
    31:  'block',
#   32:  'unknown file xfer flag',
    38:  'expires',
    47:  'away',
    49:  'typing_status',
    50:  'conf_buddy',
    51:  'conf_invite_buddy',
    52:  'conf_tobuddy',
    53:  'conf_entering',
    56:  'conf_leaving',
    57:  'conf_name',
    58:  'conf_invite_message',
    59:  'login_cookie', #bcookie?
    62:  'chat_search',
#    63: ,
#    64: ,
    65:  'group',
    66:  'error',
    67:  'new_group',
    68:  'sms_carrier',
    69:  'sms_alias',
    87:  'buddy_list',
    88:  'ignore_list',
    89:  'identity_list',
    97:  'msg_encoding', #1=utf-8, omit for ascii? thanks jYMSG API
    98:  'locale', #? saw as 'us' in yahoo http packet
    104: 'room_name',
    105: 'topic',
    109: 'chat_buddy',
    117: 'chat_message',
    135: 'version_str',
    137: 'idle_seconds',
    138: 'idle_duration_privacy',
#   140: 'unknown file xfer flag'

    184: 'opentalk',
    185: 'appear_offline_list',
#   187: something related to away messages?
    192: 'checksum',
#    198: , ? seen in "awaylogin_available" packet
    203: 'mingle_xml',
    206: 'icon_flag',
    213: 'avatar_flag',
    216: 'firstname',
    222: 'acceptxfer',
    223: 'pending_auth',
    224: 'fromgroup',
    231: 'audible_message',
    233: 'cookie',
    234: 'conf_cookie',
    241: 'buddy_service',
#    242: , something to do with msn buddies?
    244: 'mystery_login_num',
    249: 'transfertype',
    250: 'peerip',
    251: 'peer_path',

    254: 'lastname',
    257: 'yahoo360xml',
    264: 'togroup',

    265: 'p2pcookie',
    267: 'longcookie',

    277: 'ycookie',
    278: 'tcookie',

#    283: , ? seen in "awaylogin_brb" packet

    300: 'begin_entry',
    301: 'end_entry',
    302: 'begin_mode',
    303: 'end_mode',

    307: 'crumbchallengehash',
    317: 'stealth',

#   334:

    429: 'msgid',
    430: 'msgid_ack',
#    440: , ? seen in "awaylogin_available" packet
    450: 'send_attempt', #0-based

#   10093: 'unknown file xfer flag',
}

# stringify the numbers and add the dictionary's reverse
ykeys = lookup_table(dict((str(k), v) for k,v in ykeys.iteritems()))
