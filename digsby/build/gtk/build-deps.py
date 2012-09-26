#!/usr/bin/python
#__LICENSE_GOES_HERE__

import sys
import os
import commands

# command line options
update = False
clean = False
debug = False
debug_str = ""

if "update" in sys.argv:
    update = True

if "clean" in sys.argv:
    clean = True

if "debug" in sys.argv:
    debug = True
    debug_str = " debug"

WXWIDGETS_28_SVN_DIR = "http://svn.wxwidgets.org/svn/wx/wxWidgets/branches/wxWebKitBranch-2.8"
WXPYTHON_28_SVN_DIR = "http://svn.wxwidgets.org/svn/wx/wxPython/branches/WX_2_8_BRANCH"
WXWEBKIT_SVN_DIR = "http://svn.webkit.org/repository/webkit/trunk"

# Automatically update if Digsby needs a revision of wx that is > what is currently
# in the tree.
MIN_WX_REVISION = 53385

scriptDir = os.path.abspath(sys.path[0])
digsbyDir = os.path.abspath(os.path.join(scriptDir, "..", ".."))

sys.path += [digsbyDir]

#import config

depsDir = os.path.join(digsbyDir, "build", "gtk", "dependencies")

wxWidgetsDir = os.path.join(depsDir, "wxWebKitBranch-2.8")
wxPythonDir = os.path.join(wxWidgetsDir, "wxPython")
wxWebKitDir = os.path.join(depsDir, "wxWebKit")

startDir = os.getcwd()

def runCommand(command, exitOnError=True):
    print "Running %s" % command
    retval = os.system(command)
    print "Command result = %d" % retval
    if retval != 0:
        print "Error running `%s`." % command
        if exitOnError:
            sys.exit(1)

    return retval == 0

def checkForDeps():
    retVal = os.system("which bakefile")

    if retVal != 0:
        print "ERROR: You must have Bakefile (http://bakefile.org) installed to continue. Exiting..."
        sys.exit(1)

    retVal = os.system("which swig")

    if retVal != 0:
        print "ERROR: You must have Robin's SWIG (http://wxpython.wxcommunity.com/tools/) installed to continue. Exiting..."
        sys.exit(1)

    if commands.getoutput("swig -version").find("1.3.29") == -1:
        print "ERROR: Wrong SWIG. You must install Robin's SWIG (http://wxpython.wxcommunity.com/tools/). Exiting..."
        sys.exit(1)



checkForDeps()

if not os.path.exists(depsDir):
    os.mkdir(depsDir)

os.chdir(depsDir)
if not os.path.exists(wxWidgetsDir):
    runCommand("svn checkout %s" % WXWIDGETS_28_SVN_DIR)

os.chdir(wxWidgetsDir)

revision = commands.getoutput("svnversion .")
revision = min(int(r) for r in revision.rstrip('MSP').split(':'))

if update or revision < MIN_WX_REVISION:
    runCommand("svn update")

if not os.path.exists(wxPythonDir):
    runCommand("svn checkout %s wxPython" % WXPYTHON_28_SVN_DIR)
    os.chdir("wxPython")
    #runCommand("patch -p0 < %s" % (os.path.join(scriptDir, "patches", "wxpy_popupwin.patch")))
    #runCommand("patch -p0 < %s" % (os.path.join(scriptDir, "patches", "build-wxpython.patch")))

os.chdir(wxPythonDir)

if update or revision < MIN_WX_REVISION:
    runCommand("svn update")

os.chdir(depsDir)

if not os.path.exists(wxWebKitDir):
    runCommand("svn checkout %s wxWebKit" % WXWEBKIT_SVN_DIR)
    os.chdir(wxWebKitDir)

os.chdir(wxWebKitDir)
if update:
    runCommand("svn update")


# Now let's do the build
homeDir = os.environ["HOME"]

if clean:
    os.chdir(wxPythonDir)
    runCommand("./build-wxpython.sh 25 clean")
    os.chdir(os.path.join(depsDir, "wxWebKit"))
    runCommand("export PATH=%s/wxpython-2.8/bin:${PATH}; WebKitTools/Scripts/build-webkit --wx --clean" % homeDir)
    os.chdir(digsbyDir)
    runCommand("/usr/bin/python ext/do_buildext.py clean")

    sys.exit(0)

os.chdir(os.path.join(wxWidgetsDir, "build/bakefiles"))

runCommand("bakefile_gen")

os.chdir(wxWidgetsDir)

# hack below is due to wxWidgets storing generated files in the tree. Since that tends
# to create huge diffs, they have a lot of special tricks which reduce the diffs by
# keeping certain files for certain versions of Bakefile, etc. in the tree. Since
# we don't use that Bakefile version, the hacks break our build system, and so we have to
# copy over the 'real' version of autoconf bakefile tools ourselves and then
# re-configure, making sure to touch configure.in to force the rebuild. Ick. :(

bakefilePrefix = commands.getoutput("which bakefile").replace("bin/bakefile", "")

runCommand("cp %sshare/aclocal/bakefile.m4 build/aclocal/" % bakefilePrefix)

runCommand("touch configure.in; make -f build/autogen.mk")

# end rebake hacks

os.chdir(wxPythonDir)

runCommand("./build-wxpython.sh 25 unicode")

if not os.path.exists(os.path.join(homeDir, "wxpython-2.8.4", "bin", "wx-config")):
    print "Error while building or installing wxWidgets."
    sys.exit(1)

os.chdir(os.path.join(depsDir, "wxWebKit"))

runCommand("export PATH=%s/wxpython-2.8.4/bin:${PATH}; WebKitTools/Scripts/build-webkit --wx wxgc wxpython" % homeDir)

os.chdir(digsbyDir)

runCommand("/usr/bin/python ext/do_buildext.py WX_CONFIG=%s/wxpython-2.8.4/bin/wx-config" % homeDir)

pythonPath="%s/wxpython-2.8.4/wxPython/wx-2.8-gtk-unicode:%s/dependencies/wxWebKit/WebKitBuild/Release" % (homeDir, scriptDir)

print "=========== BUILD COMPLETE ==========="
print ""

print "To run Digsby:"
print "- Set your PYTHONPATH to %s" % pythonPath
print "- Apply %s/digsbymac.patch (with unfinished Mac changes) if you haven't already." % os.path.join(scriptDir, "patches")
print "- Run Digsby.py"

