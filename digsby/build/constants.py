#__LICENSE_GOES_HERE__
import sys

#set this to "True" to prefer mini's mirror repositories when they exist
MINI_LOCAL = True
#in case of differing hostname/ip/port/etc.
MINI_LOCATION = 'mini'
MINI_HTTP     = 'http://%s' % MINI_LOCATION

if MINI_LOCAL:
    PYTHON_PROJECTS_SVN = '%s/svn/python-mirror' % MINI_HTTP
else:
    PYTHON_PROJECTS_SVN = 'http://svn.python.org/projects'

# remote SIP info
SIP_GIT_REPO   = 'https://github.com/tagged/sip.git'
SIP_GIT_REMOTE = 'origin'
SIP_GIT_BRANCH = 'master'

# location of some extra tarballs
TARBALL_URL = '%s/deps/' % MINI_HTTP

WXWEBKIT_GIT_REPO = 'https://github.com/mikedougherty/webkit.git'

WXWEBKIT_SVN_DIR = "http://svn.webkit.org/repository/webkit/trunk"

if MINI_LOCAL:
    WXWIDGETS_BASE_SVN = "%s/svn/wx-mirror/" % MINI_HTTP
else:
    WXWIDGETS_BASE_SVN = "http://svn.wxwidgets.org/svn/wx/"

WXWIDGETS_28_SVN_DIR = WXWIDGETS_BASE_SVN + "wxWidgets/branches/wxWebKitBranch-2.8"
WXPYTHON_28_SVN_DIR = WXWIDGETS_BASE_SVN + "wxPython/branches/WX_2_8_BRANCH"

WXWIDGETS_TRUNK_SVN_DIR = WXWIDGETS_BASE_SVN + "wxWidgets/trunk"
WXPYTHON_TRUNK_SVN_DIR = WXWIDGETS_BASE_SVN + "wxPython/trunk"

# remote WXPY info
WXPY_GIT_REPO = 'https://github.com/tagged/wxpy.git'

DEBUG_ARG = '--DEBUG'
DEBUG = False

if DEBUG_ARG in sys.argv:
    sys.argv.remove(DEBUG_ARG)
    DEBUG = True
elif hasattr(sys, 'gettotalrefcount'):
    DEBUG = True

DEBUG_POSTFIX = '_d' if DEBUG else ''

if DEBUG:
    class wxconfig:
        debug_runtime = True
        debug_assertions = True
        debug_symbols = True
        whole_program_optimization = False
        exceptions = False
        disable_all_optimization = True
        html = False
else:
    class wxconfig:
        debug_runtime              = False   # /MDd
        debug_assertions           = False   # (/D__WXDEBUG__)
        debug_symbols              = True    # (/Zi, /DEBUG) if True, PDB symbol files will be generated alongside teh DLLs
        whole_program_optimization = True    # (/GL, /LTCG)  enable whole program optimization
        exceptions                 = False   # (/EHa)        enables C++ exceptions
        disable_all_optimization   = False   # (/Od)         disables all optimizations
        html = False

#
# These entries correspond to wxUSE_XXX entries and are edited
# into wxWidgets/include/msw/setup.h.
#
# The goal is to make the binaries as small as possible!
#
setup_h_use_flags = dict(
    EXCEPTIONS = int(wxconfig.exceptions),
    UNICODE = 1,
    CMDLINE_PARSER = 0,
    FSVOLUME = 0,
    DIALUP_MANAGER = 0,
    FS_ZIP = 0,
    FS_ARCHIVE = 0,
    FS_INET = 0,
    ARCHIVE_STREAMS = 0,
    ZIPSTREAM = 0,
    TARSTREAM = 0,
    JOYSTICK = 0,
    PROTOCOL_FTP = 0,
    PROTOCOL_HTTP = 0,
    VARIANT = 0,
    REGEX = 0,
    MEDIACTRL = 0,
    XRC = 0,

    AUI = 0,
    GRAPHICS_CONTEXT = 1,
    ANIMATIONCTRL = 0,
    COLLPANE = 0,
    DATAVIEWCTRL = 0,
    DATEPICKCTRL = 0,
    LISTBOOK = 0,
    CHOICEBOOK = 0,
    TREEBOOK = 0,
    TOOLBOOK = 0,
    GRID = 0,
    FINDREPLDLG = 0,
    PROGRESSDLG = 0,
    STARTUP_TIPS = 0,
    SPLASH = 0,
    WIZARDDLG = 0,
    ABOUTDLG = 0,
    METAFILE = 0,
    ENH_METAFILE = 0,
    MDI = 0,
    DOC_VIEW_ARCHITECTURE = 0,
    MDI_ARCHITECTURE = 0,
    PRINTING_ARCHITECTURE = 0,
    RICHTEXT = 0,
    HELP = 0,
    HTML = 1 if wxconfig.html else 0,
    WXHTML_HELP = 1 if wxconfig.html else 0,
    CONSTRAINTS = 0,

    PNM = 0, # image formats
    IFF = 0,
    PCX = 0,

    POSTSCRIPT_ARCHITECTURE_IN_MSW = 0,

    CONFIG_NATIVE = 0,

    #CAIRO = 1,

    #STL = 0,      causeswebkit compiliation errors?

    #INKEDIT = 1,  FIX tablet support first!
    #SOCKET = 0,   makes wxURL fail -- needed by wxHTML
    XML = 0,
)

configure_flags = [
    "--enable-graphics_ctx",
    "--disable-cmdline",
    "--disable-fs_archive",
    "--disable-fs_inet",
    "--disable-fs_zip",
    "--disable-dialupman",
    "--disable-arcstream",
    "--disable-tarstream",
    "--disable-zipstream",
    "--disable-joystick",
    "--disable-protocol",
    "--disable-protocols",
    "--disable-variant",
    "--without-regex",
    "--disable-mediactrl",
    "--disable-xrc",
    "--disable-aui",
    "--disable-animatectrl",
    "--disable-collpane",
    "--enable-logwin",
    "--disable-logdialog",
    "--disable-dataviewctrl",
    "--disable-datepick",
    "--disable-listbook",
    "--disable-choicebook",
    "--disable-treebook",
    "--disable-toolbook",
    "--disable-grid",
    "--disable-finddlg",
    "--disable-progressdlg",
    "--disable-tipdlg",
    "--disable-splash",
    "--disable-wizarddlg",
    "--disable-aboutdlg",
    "--disable-metafiles",
    "--disable-mdi",
    "--disable-docview",
    "--disable-mdidoc",
    "--disable-printarch",
    "--disable-richtext",
    "--disable-help",
    "--disable-htmlhelp",
    "--disable-html",
    "--disable-constraints",
    "--disable-propgrid",
    "--enable-config",
    "--enable-debug_flag",
    "--enable-std_string",
    "--enable-stl"
]

if sys.platform.startswith('darwin'):
    configure_flags += [
        '--with-macosx-version-min=10.4',
        # '--with-macosx-sdk=/Developer/SDKs/MacOSX10.4u.sdk',
    ]
