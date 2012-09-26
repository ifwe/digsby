#__LICENSE_GOES_HERE__
import commands
import os
import sys

scriptDir = os.path.abspath(sys.path[0])
digsbyDir = os.path.abspath(os.path.join(scriptDir, ".."))
sys.path += [digsbyDir]

startDir = os.getcwd()
homeDir = None

from .buildfileutils import which

if sys.platform.startswith("win"):
    homeDir = os.environ['USERPROFILE']
else:
    homeDir = os.environ["HOME"]

assert os.path.exists(homeDir)

def get_patch_cmd():
    if os.name != "nt":
        return 'patch'

    unix_tools = os.environ.get('UNIX_TOOLS')
    if unix_tools is not None:
        patch_cmd = os.path.join(unix_tools, 'patch')
    elif os.path.isdir(r'c:\Program Files (x86)\Git\bin'):
        patch_cmd = r'c:\Program Files (x86)\Git\bin\patch'
    else:
        patch_cmd = which('patch', r'c:\cygwin\bin\patch')

    return patch_cmd

class BuildDirs:
    def __init__(self):
        self.depsDir = None
        self.wxWidgetsDir = None
        self.wxPythonDir = None
        self.wxWebKitDir = None
        self.sipDir = None
        self.wxpyDir = None
        self.boostDir = None

    def initBuildDirs(self, depsDir, **overrides):
        self.depsDir = depsDir
        self.wxWidgetsDir = os.path.join(self.depsDir, "wxWidgets")
        self.wxPythonDir = os.path.join(self.wxWidgetsDir, "wxPython")
        self.wxWebKitDir = os.path.join(self.depsDir, overrides.get("wxWebKit", "wxWebKit"))
        self.sipDir = os.path.join(self.depsDir, "sip")
        self.wxpyDir = os.path.join(self.depsDir, "wxpy")
        self.boostDir = os.path.join(self.depsDir, 'boost_1_42_0')

buildDirs = BuildDirs()

if sys.platform.startswith('win'):
    common_dir = os.path.dirname(os.path.abspath(__file__))
    buildDirs.initBuildDirs(os.path.join(os.path.abspath(os.path.join(common_dir, '..')), 'msw'), wxWebKit='WebKit')
    # build boost
    from buildfileutils import tardep
    boost = tardep('http://mini/mirror/', 'boost_1_42_0', '.tar.gz', 40932853, dirname = buildDirs.boostDir)
    #boost.get()
    #^ copied from build-deps.py


def checkForDeps(swig=False):
    retVal = which("which bakefile")

    if retVal != 0:
        print "ERROR: You must have Bakefile (http://bakefile.org) installed to continue. Exiting..."
        sys.exit(1)

    if swig:
        retVal = which("which swig")

        if retVal != 0:
            print "ERROR: You must have Robin's SWIG (http://wxpython.wxcommunity.com/tools/) installed to continue. Exiting..."
            sys.exit(1)

        if not sys.platform.startswith("win") and commands.getoutput("swig -version").find("1.3.29") == -1:
            print "ERROR: Wrong SWIG. You must install Robin's SWIG (http://wxpython.wxcommunity.com/tools/). Exiting..."
            sys.exit(1)
