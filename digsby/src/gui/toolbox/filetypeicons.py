from ctypes import *

MAX_PATH = 260
HICON = c_int

class SHFILEINFO(Structure):
    _fields_ = [("hIcon", HICON),
                ("iIcon", c_int),
                ("dwAttributes", c_uint),
                ("szDisplayName", c_char * MAX_PATH),
                ("szTypeName", c_char * 80)]

FILE_ATTRIBUTE_NORMAL = 0x80

SHGFI_ICON              = 0x000000100
SHGFI_DISPLAYNAME       = 0x000000200
SHGFI_TYPENAME          = 0x000000400
SHGFI_ATTRIBUTES        = 0x000000800
SHGFI_ICONLOCATION      = 0x000001000
SHGFI_EXETYPE           = 0x000002000
SHGFI_SYSICONINDEX      = 0x000004000
SHGFI_LINKOVERLAY       = 0x000008000
SHGFI_SELECTED          = 0x000010000
SHGFI_ATTR_SPECIFIED    = 0x000020000
SHGFI_LARGEICON         = 0x000000000
SHGFI_SMALLICON         = 0x000000001
SHGFI_OPENICON          = 0x000000002
SHGFI_SHELLICONSIZE     = 0x000000004
SHGFI_PIDL              = 0x000000008
SHGFI_USEFILEATTRIBUTES = 0x000000010


shfileinfo = SHFILEINFO()

import sys

#flags = SHGFI_DISPLAYNAME | SHGFI_TYPENAME | SHGFI_ATTRIBUTES
flags = SHGFI_ICON | SHGFI_USEFILEATTRIBUTES

fileAttributes = FILE_ATTRIBUTE_NORMAL

#print\
windll.shell32.SHGetFileInfo('foo.txt',
                                   fileAttributes,
                                   byref(shfileinfo),
                                   sizeof(shfileinfo),
                                   flags)

#print\
shfileinfo.hIcon
#print hex(shfileinfo.dwAttributes)
#print repr(shfileinfo.szDisplayName)
#print repr(shfileinfo.szTypeName)