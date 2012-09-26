#=======================================================================================================================
# Message types and flags
#=======================================================================================================================

#=======================================================================================================================
# Message types.
# Each OSCAR message has type. It can be just plain message, url message, contact list, wwp,
# email express or another. Only one byte used for message type. Here is the list of known message types:
#=======================================================================================================================

class MType:
    PLAIN = 0x01    # Plain text (simple) message
    CHAT = 0x02     # Chat request message
    FILEREQ = 0x03  # File request / file ok message
    URL = 0x04      # URL message (0xFE formatted)
    AUTHREQ = 0x06  # Authorization request message (0xFE formatted)
    AUTHDENY = 0x07 # Authorization denied message (0xFE formatted)
    AUTHOK = 0x08   # Authorization given message (empty)
    SERVER = 0x09   # Message from OSCAR server (0xFE formatted)
    ADDED = 0x0C    # "You-were-added" message (0xFE formatted)
    WWP = 0x0D      # Web pager message (0xFE formatted)
    EEXPRESS = 0x0E # Email express message (0xFE formatted)
    CONTACTS = 0x13 # Contact list message
    PLUGIN = 0x1A   # Plugin message described by text string
    AUTOAWAY = 0xE8 # Auto away message
    AUTOBUSY = 0xE9 # Auto occupied message
    AUTONA = 0xEA   # Auto not available message
    AUTODND = 0xEB  # Auto do not disturb message
    AUTOFFC = 0xEC  # Auto free for chat message

#=======================================================================================================================
# Message flags.
# Message flag used to indicate additional message properties.
# like auto message, multiple recipients message, etc.
# Message flag field occupy 1 byte. Here is the list of known message flag codes:
#=======================================================================================================================
class MFlag:
    NORMAL = 0x01  # Normal message
    AUTO = 0x03    # Auto-message flag
    MULTI = 0x80    # This is multiple recipients message



#=======================================================================================================================
# User classes
# AOL users are divided into several classes. User class field is a 2 byte bitmask.
# For example ICQ non-commercial account with away status has user-class=0x0070
# (CLASS_FREE | CLASS_AWAY | CLASS_ICQ = 0x0070).
# Here is the list of known bit values in user class bitmask:
#=======================================================================================================================
class UserClass:
    UNCONFIRMED = 0x0001    # AOL unconfirmed user flag
    ADMINISTRATOR = 0x0002  # AOL administrator flag
    AOL = 0x0004            # AOL staff user flag
    COMMERCIAL = 0x0008     # AOL commercial account flag
    FREE = 0x0010           # ICQ non-commercial account flag
    AWAY = 0x0020           # Away status flag
    ICQ = 0x0040            # ICQ user sign
    WIRELESS = 0x0080       # AOL wireless user
    UNKNOWN100 = 0x0100     # Unknown bit
    UNKNOWN200 = 0x0200     # Unknown bit
    UNKNOWN400 = 0x0400     # Unknown bit
    UNKNOWN800 = 0x0800     # Unknown bit



#=======================================================================================================================
# User status
# ICQ service presence notifications use user status field which consist of two parts.
# First is a various flags (birthday flag, webaware flag, etc).
# Second is a user status (online, away, busy, etc) flags. Each part is a two bytes long.
# Here is the list of masks for both parts:
#=======================================================================================================================
class UserStatus:
    WEBAWARE = 0x0001    # Status webaware flag
    SHOWIP = 0x0002      # Status show ip flag
    BIRTHDAY = 0x0008    # User birthday flag
    WEBFRONT = 0x0020    # User active webfront flag
    DCDISABLED = 0x0100  # Direct connection not supported
    DCAUTH = 0x1000      # Direct connection upon authorization
    DCCONT = 0x2000      # DC only with contact users
    ONLINE = 0x0000      # Status is online
    AWAY = 0x0001        # Status is away
    DND = 0x0002         # Status is no not disturb (DND)
    NA = 0x0004          # Status is not available (N/A)
    OCCUPIED = 0x0010    # Status is occupied (BISY)
    FREE4CHAT = 0x0020   # Status is free for chat
    INVISIBLE = 0x0100   # Status is invisible



#=======================================================================================================================
#  Direct connection type
#  ICQ clients can send messages and files using peer-to-peer connection called "direct connection" (DC).
#  Each ICQ client may have different internet connection:
#  direct, proxy, firewall or other and to establish DC one client should know connection type of another client.
#  This connection type also used by direct connections and called "DC type". Here is the list of values:
#=======================================================================================================================
class DCType:
    DISABLED = 0x0000  # Direct connection disabled / auth required
    HTTPS = 0x0001     # Direct connection thru firewall or https proxy
    SOCKS = 0x0002     # Direct connection thru socks4/5 proxy server
    NORMAL = 0x0004    # Normal direct connection (without proxy/firewall)
    WEB = 0x0006       # Web client - no direct connection



#=======================================================================================================================
#  Direct connection protocol version
#  ICQ clients can send messages and files using peer-to-peer connection called "direct connection" (DC).
#  Here is the list of direct connection protocol versions:
#=======================================================================================================================

class DCProtoVersion:
    ICQ98 = 0x0004     # ICQ98
    ICQ99 = 0x0006     # ICQ99
    ICQ2000 = 0x0007   # ICQ2000
    ICQ2001 = 0x0008   # ICQ2001
    ICQLITE = 0x0009   # ICQ Lite
    ICQ2003B = 0x000A  # ICQ2003B



#=======================================================================================================================
#  Random chat groups
#  ICQ service has ability to search a random user in specific group and each ICQ client
#  may choose group where another client can find it. Here is the list of groups and their codes:
#=======================================================================================================================
class RandomChat:
    GENERAL = 0x0001      # General chat group
    ROMANCE = 0x0002      # Romance random chat group
    GAMES = 0x0003        # Games random chat group
    STUDENTS = 0x0004     # Students random chat group
    SOMETHING20 = 0x0006  # 20 something random chat group
    SOMETHING30 = 0x0007  # 30 something random chat group
    SOMETHING40 = 0x0008  # 40 something random chat group
    PLUS50 = 0x0009       # 50+ random chat group
    SWOMEN = 0x000A       # Seeking women random chat group
    SMAN = 0x000B         # Seeking man random chat group

#=======================================================================================================================
#  Motd types list
#  ICQ/AIM services use special SNAC(01,13) for motd (message of the day) notices during login.
#  Here is the list of known motd types:
#=======================================================================================================================
class MOTD:
    MDT_UPGRAGE = 0x0001   # Mandatory upgrade needed notice
    ADV_UPGRAGE = 0x0002   # Advisable upgrade notice
    SYS_BULLETIN = 0x0003  # AIM/ICQ service system announcements
    NORMAL = 0x0004        # Standart notice
    NEWS = 0x0006          # Some news from AOL service

#=======================================================================================================================
#  Marital status code list
#  There was some new fields added to ICQ client data. One of them is marital status field.
#  Here is the marital status code list:
#=======================================================================================================================
class MaritalStatus:
    NONE = 0x0000       # Marital status not specified
    SINGLE = 0x000A     # User is single
    LONGRS = 0x000B     # User is in a long-term relationship
    ENGAGED = 0x000C    # User is engaged
    MARRIED = 0x0014    # User is married
    DIVORCED = 0x001E   # User is divorced
    SEPARATED = 0x001F  # User is separated
    WIDOWED = 0x0028    # User is widowed
