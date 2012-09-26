import config
import sys
from path import path
inited = False

if config.platform == 'win':
    import ctypes
    SHGFP_TYPE_DEFAULT = 1
    MAX_PATH = 260
    u_buffer = ctypes.create_unicode_buffer(MAX_PATH)
    s_buffer = ctypes.create_string_buffer(MAX_PATH)
    SHGetFolderPath = ctypes.windll.shell32.SHGetFolderPathW

    def GetSpecialFolder(csidl):
        SHGetFolderPath(None, csidl, None, SHGFP_TYPE_DEFAULT, ctypes.byref(u_buffer))
        return u_buffer.value

    class SHItemID(ctypes.Structure):
        'http://msdn.microsoft.com/en-us/library/bb759800(VS.85).aspx'
        _fields_ = [("cb", ctypes.c_ushort),
                    ("abID", ctypes.POINTER(ctypes.c_byte))]

    class ItemIDList(ctypes.Structure):
        'http://msdn.microsoft.com/en-us/library/bb773321(VS.85).aspx'
        _fields_ = [("mkid", SHItemID)]

    SHGetFolderLocation = ctypes.windll.shell32.SHGetFolderLocation
    SHGetPathFromIDList = ctypes.windll.shell32.SHGetPathFromIDList
    def GetFolderLocation(csidl):
        idl = ItemIDList()

        idl.mkid.cb = ctypes.sizeof(ctypes.c_ushort)

        pidl = ctypes.pointer(idl)

        try:
            # http://msdn.microsoft.com/en-us/library/bb762180(VS.85).aspx
            if SHGetFolderLocation(0, csidl, 0, 0, ctypes.byref(pidl)):
                raise WindowsError(ctypes.GetLastError())

            # http://msdn.microsoft.com/en-us/library/bb762194(VS.85).aspx
            if not SHGetPathFromIDList(pidl, s_buffer):
                raise WindowsError(ctypes.GetLastError())
        except WindowsError:
            # if a special folder like "My Documents" cannot be resolved, use
            # the path returned by SHGetFolderPath with SHGFP_TYPE_DEFAULT,
            # which should be writable at least
            return GetSpecialFolder(csidl)

        return s_buffer.value

def init(reinit=False):
    global inited
    if inited and not reinit:
        return
    inited = True

    our_paths = {}
    our_paths.update(init_wx())

    sys.is_portable = False
    if (not sys.DEV) or sys.opts.allow_portable:
        try:
            portable_paths = init_portable()
        except Exception:
            sys.is_portable = False
            # can't print a traceback, it would go to the digsby-app.exe.log during normal app usage,
            # and that file is not accesssible to users when installed in a UAC environment.
            # it's also the normal case (non-portable), so who cares.
            #import traceback; traceback.print_exc()
        else:
            sys.is_portable = True
            our_paths.update(portable_paths)

    for k in our_paths:
        v = path(our_paths[k]).abspath()
        if v.isfile():
            continue
        if not v.isdir():
            try:
                v.makedirs()
            except Exception:
                import traceback; traceback.print_exc()

def __res_dir():
    # XXX: Mostly copied from util.program_dir()
    import locale

    if hasattr(sys, 'frozen') and sys.frozen == 'windows_exe':
        prog_dir = path(sys.executable.decode(locale.getpreferredencoding())).abspath().dirname()
    else:
        import digsbypaths
        prog_dir = path(digsbypaths.__file__).parent

    return prog_dir / 'res'

def init_portable():
    import syck
    with open(__res_dir() / "portable.yaml") as f:
        usb_info = syck.load(f)

    for name in usb_info.keys():
        usb_info[name] = path(usb_info[name]).abspath()

    _set_paths(**usb_info)

    return usb_info

def GetAppDir():
    return path(sys.executable).parent

def GetTempDir():
    import os
    for p in ('TMPDIR', 'TMP', 'TEMP'):
        try:
            return os.environ[p]
        except KeyError:
            pass
    return GetFolderLocation(CSIDL.LOCAL_APPDATA) + '\\Temp'

def init_wx_old():
    import wx

    s = wx.StandardPaths.Get()

    paths = dict(config = s.GetConfigDir(),
                 data   = s.GetDataDir(),
                 documents = s.GetDocumentsDir(),
                 executablepath = s.GetExecutablePath(),
                 localdata = s.GetLocalDataDir(),

                 userconfig = s.GetUserConfigDir(),
                 userdata = s.GetUserDataDir(),
                 userlocaldata = s.GetUserLocalDataDir(),

                 temp = s.GetTempDir())

    if sys.platform == 'win32':
        _winpaths = [
            ('GetUserStartupDir', CSIDL.STARTUP),
            ('GetStartupDir',     CSIDL.COMMON_STARTUP),
            ('GetUserDesktopDir', CSIDL.DESKTOP),
            ('GetDesktopDir',     CSIDL.COMMON_DESKTOPDIRECTORY)
        ]

        for method_name, csidl in _winpaths:
            setattr(wx.StandardPaths, method_name, lambda p, id=csidl: p.GetFolderLocation(id))

        # extended wxStandardPaths folders
        paths.update(userstartup = s.GetUserStartupDir(),
                     startup = s.GetStartupDir(),
                     userdesktop = s.GetUserDesktopDir(),
                     desktop = s.GetDesktopDir())

    _set_paths(**paths)
    return paths

def init_wx(appname='Digsby'):
    if config.platform != 'win':
        # on windows we don't use wxStandardPaths at all to avoid having to have
        # the app created.
        return init_wx_old()

    paths = \
    [('GetConfigDir', CSIDL.COMMON_APPDATA, True),
     ('GetDataDir', GetAppDir),
     ('GetDocumentsDir', CSIDL.PERSONAL, False),
     ('GetExecutablePath', lambda: sys.executable),
     ('GetLocalDataDir', GetAppDir),

     ('GetUserConfigDir', CSIDL.APPDATA, False),
     ('GetUserDataDir', CSIDL.APPDATA, True),
     ('GetUserLocalDataDir', CSIDL.LOCAL_APPDATA, True),
     ('GetUserLocalConfigDir', CSIDL.LOCAL_APPDATA, False),
     ('GetTempDir', GetTempDir)
     ]

    from util.primitives.mapping import Storage
    s = Storage()

    for p in paths:
        name = p[0]
        if hasattr(p[1], '__call__'):
            s[name] = p[1]
        else:
            csidl, append_app_name = p[1], p[2]
            if append_app_name:
                method = lambda id=csidl: GetFolderLocation(id) + '\\' + appname
            else:
                method = lambda id=csidl: GetFolderLocation(id)

            setattr(s, name, method)

    paths_dict = dict(config = s.GetConfigDir(),
                      data   = s.GetDataDir(),
                      documents = s.GetDocumentsDir(),
                      executablepath = s.GetExecutablePath(),
                      localdata = s.GetLocalDataDir(),

                      userconfig = s.GetUserConfigDir(),
                      userdata = s.GetUserDataDir(),
                      userlocaldata = s.GetUserLocalDataDir(),
                      userlocalconfig = s.GetUserLocalConfigDir(),

                      temp = s.GetTempDir())

    _winpaths = [
        ('GetUserStartupDir', CSIDL.STARTUP),
        ('GetStartupDir',     CSIDL.COMMON_STARTUP),
        ('GetUserDesktopDir', CSIDL.DESKTOP),
        ('GetDesktopDir',     CSIDL.COMMON_DESKTOPDIRECTORY)
    ]

    for method_name, csidl in _winpaths:
        setattr(s, method_name, lambda id=csidl: GetFolderLocation(id))

    # extended wxStandardPaths folders
    paths_dict.update(userstartup = s.GetUserStartupDir(),
                      startup = s.GetStartupDir(),
                      userdesktop = s.GetUserDesktopDir(),
                      desktop = s.GetDesktopDir())

    _set_paths(**paths_dict)
    return paths_dict

if sys.platform == 'win32':

    # use these with wxStandardPaths::GetFolderLocation

    class CSIDL(object):
        DESKTOP                   = 0x0000        # <desktop>
        INTERNET                  = 0x0001        # Internet Explorer (icon on desktop)
        PROGRAMS                  = 0x0002        # Start Menu\Programs
        CONTROLS                  = 0x0003        # My Computer\Control Panel
        PRINTERS                  = 0x0004        # My Computer\Printers
        PERSONAL                  = 0x0005        # My Documents
        FAVORITES                 = 0x0006        # <user name>\Favorites
        STARTUP                   = 0x0007        # Start Menu\Programs\Startup
        RECENT                    = 0x0008        # <user name>\Recent
        SENDTO                    = 0x0009        # <user name>\SendTo
        BITBUCKET                 = 0x000a        # <desktop>\Recycle Bin
        STARTMENU                 = 0x000b        # <user name>\Start Menu
        MYDOCUMENTS               = 0x000c        # logical "My Documents" desktop icon
        MYMUSIC                   = 0x000d        # "My Music" folder
        MYVIDEO                   = 0x000e        # "My Videos" folder
        DESKTOPDIRECTORY          = 0x0010        # <user name>\Desktop
        DRIVES                    = 0x0011        # My Computer
        NETWORK                   = 0x0012        # Network Neighborhood (My Network Places)
        NETHOOD                   = 0x0013        # <user name>\nethood
        FONTS                     = 0x0014        # windows\fonts
        TEMPLATES                 = 0x0015
        COMMON_STARTMENU          = 0x0016        # All Users\Start Menu
        COMMON_PROGRAMS           = 0x0017        # All Users\Start Menu\Programs
        COMMON_STARTUP            = 0x0018        # All Users\Startup
        COMMON_DESKTOPDIRECTORY   = 0x0019        # All Users\Desktop
        APPDATA                   = 0x001a        # <user name>\Application Data
        PRINTHOOD                 = 0x001b        # <user name>\PrintHood

        LOCAL_APPDATA             = 0x001c        # <user name>\Local Settings\Applicaiton Data (non roaming)

        ALTSTARTUP                = 0x001d        # non localized startup
        COMMON_ALTSTARTUP         = 0x001e        # non localized common startup
        COMMON_FAVORITES          = 0x001f

        INTERNET_CACHE            = 0x0020
        COOKIES                   = 0x0021
        HISTORY                   = 0x0022
        COMMON_APPDATA            = 0x0023        # All Users\Application Data
        WINDOWS                   = 0x0024        # GetWindowsDirectory()
        SYSTEM                    = 0x0025        # GetSystemDirectory()
        PROGRAM_FILES             = 0x0026        # C:\Program Files
        MYPICTURES                = 0x0027        # C:\Program Files\My Pictures

        PROFILE                   = 0x0028        # USERPROFILE
        SYSTEMX86                 = 0x0029        # x86 system directory on RISC
        PROGRAM_FILESX86          = 0x002a        # x86 C:\Program Files on RISC

        PROGRAM_FILES_COMMON      = 0x002b        # C:\Program Files\Common

        PROGRAM_FILES_COMMONX86   = 0x002c        # x86 Program Files\Common on RISC
        COMMON_TEMPLATES          = 0x002d        # All Users\Templates

        COMMON_DOCUMENTS          = 0x002e        # All Users\Documents
        COMMON_ADMINTOOLS         = 0x002f        # All Users\Start Menu\Programs\Administrative Tools
        ADMINTOOLS                = 0x0030        # <user name>\Start Menu\Programs\Administrative Tools

        CONNECTIONS               = 0x0031        # Network and Dial-up Connections
        COMMON_MUSIC              = 0x0035        # All Users\My Music
        COMMON_PICTURES           = 0x0036        # All Users\My Pictures
        COMMON_VIDEO              = 0x0037        # All Users\My Video
        RESOURCES                 = 0x0038        # Resource Direcotry

        RESOURCES_LOCALIZED       = 0x0039        # Localized Resource Direcotry

        COMMON_OEM_LINKS          = 0x003a        # Links to All Users OEM specific apps
        CDBURN_AREA               = 0x003b        # USERPROFILE\Local Settings\Application Data\Microsoft\CD Burning


def _set_paths(**d):
    for k in d.keys():
        v = path(d[k]).abspath()
        globals()[k] = v
