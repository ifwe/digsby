#!/usr/bin/env python
#__LICENSE_GOES_HERE__

from buildutil import *
from build_wxpy import *
from compiledeps import *

print "Digsby dir is: %s" % digsbyDir

import commands
import optparse
import os
import string
import sys
import types
from constants import WXWIDGETS_28_SVN_DIR, WXPYTHON_28_SVN_DIR, WXWIDGETS_TRUNK_SVN_DIR, WXPYTHON_TRUNK_SVN_DIR, WXWEBKIT_GIT_REPO

import config

build_wx = False
build_webkit = False
rebake = False

py_version = sys.version[:3]
is64bit = False

path_extras = []

option_dict = {
            "clean"     : (False, "Clean all files from build directories"),
            "debug"     : (False, "Build wxPython with debug symbols"),
            "rebake"    : (False, "Force regeneration of wx makefiles."),
            "swig"      : (False, "Use SWIG bindings instead of SIP"),
            "reswig"    : (False, "Re-generate the SWIG wrappers"),
            "update"    : (False, "Do an svn update on all dependencies."),
            "wx"        : (False, "Force wx build"),
            "webkit"    : (False, "Force wxWebKit build"),
            "wx_trunk"  : (False, "Build against latest wx trunk."),
            "python_deps": (False, "Compile Python dependencies."),
          }

parser = optparse.OptionParser(usage="usage: %prog [options]", version="%prog 1.0")

for opt in option_dict:
    default = option_dict[opt][0]

    action = "store"
    if type(default) == types.BooleanType:
        action = "store_true"
    parser.add_option("--" + opt, default=default, action=action, dest=opt, help=option_dict[opt][1])

options, arguments = parser.parse_args()

if options.wx or options.update:
    build_wx = True

if options.webkit or options.update:
    build_webkit = True

if options.rebake:
    rebake = True

if options.wx_trunk:
    wx_version = "2.9.0"
    WXWIDGETS_SVN_DIR = WXWIDGETS_TRUNK_SVN_DIR
    WXPYTHON_SVN_DIR = WXPYTHON_TRUNK_SVN_DIR
else:
    wx_version = "2.8"
    WXWIDGETS_SVN_DIR = WXWIDGETS_28_SVN_DIR
    WXPYTHON_SVN_DIR = WXPYTHON_28_SVN_DIR

# Automatically update if Digsby needs a revision of wx that is > what is currently
# in the tree.
MIN_WX_REVISION = 55272

if config.platformName == "win":
    # TODO: Can we just build the Windows side with this script too?
    print "On Windows, use the pre-compiled binaries in DPython instead of this script."
    sys.exit(1)

depsDir = os.path.join(homeDir, "digsby-deps", "py" + py_version + "-wx" + wx_version[:3])
buildDirs.initBuildDirs(depsDir)

checkForDeps(swig=options.swig)

if not os.path.exists(depsDir):
    os.makedirs(depsDir)

os.chdir(depsDir)

if sys.platform.startswith('darwin'):
    # use the 10.4 SDK to make sure the C/C++ libs we compile work on older systems
    os.environ['CC'] = 'gcc-4.0'
    os.environ['CXX'] = 'g++-4.0'

if not options.clean and options.python_deps:
    # TODO: Determine if we can get these via packages on Linux
    build_m2crypto()
    build_syck()
    build_pil()

    if sys.platform.startswith('darwin'):
        build_libxml2_mac()
        build_pyobjc()
    else:
        build_libxml2()

# download and build sip
sip()

sipPath = os.path.join(depsDir, "sip", "sipgen")
path_extras.append(sipPath)
os.environ["PATH"] = sipPath + os.pathsep + os.environ["PATH"]

# build boost
boost = tardep('http://mini/mirror/', 'boost_1_42_0', '.tar.gz', 40932853, dirname = buildDirs.boostDir)
#boost.get()

if not os.path.exists(buildDirs.wxWidgetsDir):
    run("svn checkout %s wxWidgets" % WXWIDGETS_SVN_DIR)
    build_wx = True

os.chdir(buildDirs.wxWidgetsDir)

# FIXME: write a wrapper for commands.getoutput that works on Windows
if not sys.platform.startswith("win"):
    revision = commands.getoutput("svnversion .")
    revision = min(int(r) for r in revision.rstrip('MSP').split(':'))

if options.update or (not sys.platform.startswith("win") and revision < MIN_WX_REVISION):
    run(["svn", "update"])

if options.swig:
    if not os.path.exists(buildDirs.wxPythonDir):
        run(["svn", "checkout", WXPYTHON_SVN_DIR, "wxPython"])
        build_wx = True

        if wx_version == "2.8":
            os.chdir("wxPython")
            run(["patch", "-p0", "<", os.path.join(scriptDir, "patches", "wxpy_popupwin.patch")])
            run(["patch", "-p0", "<", os.path.join(scriptDir, "patches", "build-wxpython.patch")])

    os.chdir(buildDirs.wxPythonDir)

    if options.update or (not sys.platform.startswith("win") and revision < MIN_WX_REVISION):
        run(["svn", "update"])

os.chdir(depsDir)
if not os.path.exists(buildDirs.wxWebKitDir):
    run(["git", "clone", WXWEBKIT_GIT_REPO, "wxWebKit"])
    build_webkit = True
    os.chdir(buildDirs.wxWebKitDir)
    run("git checkout -b digsby origin/digsby".split())
    run("git pull origin digsby".split())

os.chdir(buildDirs.wxWebKitDir)
if options.update:
    run("git pull origin digsby".split())

# Now let's do the build
if sys.platform.startswith("win"):
    homeDir = "C:"  # TODO: What would be a better option here?
else:
    homeDir = os.environ["HOME"]

installDir = "%s/wxpython-%s" % (homeDir, wx_version[:3])
os.environ["PATH"] = installDir + "/bin" + os.pathsep + os.environ["PATH"]

if options.clean:
    if options.swig:
        os.chdir(buildDirs.wxPythonDir)
        run([sys.executable] + "build-wxpython.py --clean".split())
        os.chdir(digsbyDir)
        run([sys.executable] + "ext/do_buildext.py clean".split(), env = os.environ)
    else:
        os.chdir(buildDirs.wxWidgetsDir)
        run([sys.executable] + "build/tools/build-wxwidgets.py --clean".split())

    os.chdir(buildDirs.wxWebKitDir)
    run("WebKitTools/Scripts/build-webkit --wx --clean".split())

    sys.exit(0)

os.chdir(buildDirs.wxWidgetsDir)
if rebake:
    os.chdir(os.path.join(buildDirs.wxWidgetsDir, "build/bakefiles"))

    run("bakefile_gen")

    # hack below is due to wxWidgets storing generated files in the tree. Since that tends
    # to create huge diffs, they have a lot of special tricks which reduce the diffs by
    # keeping certain files for certain versions of Bakefile, etc. in the tree. Since
    # we don't use that Bakefile version, the hacks break our build system, and so we have to
    # copy over the 'real' version of autoconf bakefile tools ourselves and then
    # re-configure, making sure to touch configure.in to force the rebuild. Ick. :(
    if not sys.platform.startswith("win"):
        bakefilePrefix = commands.getoutput("which bakefile").replace("/bin/bakefile", "")

        os.chdir(buildDirs.wxWidgetsDir)
        run(["cp", "%s/share/aclocal/bakefile.m4" % bakefilePrefix, "build/aclocal/"])

        run("touch configure.in; make -f build/autogen.mk".split())

    # end rebake hacks

pythonPath = ""

if build_wx:
    wx_options = []
    if options.debug:
        wx_options.append("--debug")

    if options.wx_trunk and sys.platform.startswith("darwin"):
        wx_options.append("--osx_cocoa")

    if options.swig:
        if options.reswig:
            wx_options.append("--reswig")

        os.chdir(buildDirs.wxPythonDir)
        run([sys.executable] + "build-wxpython.py --unicode --install".split() + wx_options)
        pythonPath = "%s/wxPython/lib/python%s/site-packages/wx-%s-%s-unicode" % (installDir, py_version, wx_version, platform)
        os.environ["PYTHONPATH"] = pythonPath
    else:
        wx_options.append('--prefix=%s' % installDir)
        if "--debug" in wx_options:
            configure_flags.remove("--enable-debug_flag")
            configure_flags.append("--disable-debug_flag")
            if sys.platform.startswith('darwin'):
                # 10.5 sends mouse motion events on inactive / non-focused windows, so we want that :)
                configure_flags.append("--with-macosx-version-min=10.5")
        wx_options.append('--features=%s' % string.join(configure_flags, " "))
        os.chdir(buildDirs.wxWidgetsDir)
        run([sys.executable] + "build/tools/build-wxwidgets.py --unicode --install".split() + wx_options)

os.environ["WXDIR"] = os.environ["WXWIN"] = buildDirs.wxWidgetsDir
os.environ["WXPYDIR"] = buildDirs.wxPythonDir
os.environ["PATH"] = installDir + "/bin" + os.pathsep + os.environ["PATH"]
platform = config.platformName
if options.wx_trunk and platform == "mac":
    platform = "osx_cocoa"

configDir = "Release"
if options.debug:
    configDir = "Debug"

configDir += ".digsby"

extra = ""
libPath = ""
if platform == "gtk":
    platform = "gtk2"
    libPath = "%s/wxpython-%s/lib:%s/wxWebKit/WebKitBuild/%s" % (depsDir, wx_version[:3], scriptDir, configDir)
    os.environ["LD_LIBRARY_PATH"] = libPath + os.pathsep + os.environ["LD_LIBRARY_PATH"]

if build_webkit:
    os.chdir(os.path.join(depsDir, "wxWebKit"))

    if options.debug:
        run(["WebKitTools/Scripts/set-webkit-configuration", "--wx", "--debug"])
    else:
        run(["WebKitTools/Scripts/set-webkit-configuration", "--wx", "--release"])

    run(["WebKitTools/Scripts/build-webkit", "--wx", "--makeargs=--macosx-version=10.5"], env = os.environ)

if not options.swig:
    os.chdir(depsDir)
    branch = "master"
    if options.wx_trunk:
        branch = "wx_trunk"
    wxpy(branch = branch)

os.chdir(digsbyDir)

pythonPath += os.pathsep + "%s/wxWebKit/WebKitBuild/%s" % (depsDir, configDir)
if not options.swig:
    pythonPath += os.pathsep + "%s/wxpy" % depsDir + os.pathsep + "%s/sip" % depsDir + os.pathsep + "%s/sip/siplib" % depsDir

os.environ["PYTHONPATH"] = pythonPath
if options.swig:
    run([sys.executable, "ext/do_buildext.py", "WX_CONFIG=%s/bin/wx-config" % installDir], env = os.environ)
else:
    os.chdir(os.path.join(digsbyDir, "ext"))
    run([sys.executable, 'buildbkl.py',
         '--wx=%s' % buildDirs.wxWidgetsDir,
         '--webkit=%s' % buildDirs.wxWebKitDir],
         env = os.environ)
    os.chdir(digsbyDir)

bits = '32'
if is64bit:
    bits = '64'

pythonPath += os.pathsep + os.path.join(digsbyDir, "build", "platlib_" + config.platformName + bits + "_" + py_version.replace(".", ""))

ext = ""
if sys.platform.startswith("win"):
    ext = ".bat"
scriptPath = os.path.join(digsbyDir, "denv" + ext)
script = open(scriptPath, "w")
if sys.platform.startswith("win"):
    script.write('set DIGSBY_DIR="%s"\r\n' % digsbyDir)
    script.write('set PYTHONPATH="$DIGSBY_DIR/lib;%s:$DIGSBY_DIR/src;$DIGSBY_DIR;$DIGSBY_DIR/ext/%s;$DIGSBY_DIR/build/deps\r\n' % (pythonPath, config.platformName))
else:
    script.write("export DIGSBY_DIR=%s\n" % digsbyDir)
    script.write("export LD_LIBRARY_PATH=%s\n" % libPath)
    script.write("export PYTHONPATH=$DIGSBY_DIR/lib:%s:$DIGSBY_DIR/src:$DIGSBY_DIR:$DIGSBY_DIR/ext/%s:$DIGSBY_DIR/build/deps\n" % (pythonPath, config.platformName))

script.close()

print "=========== BUILD COMPLETE ==========="
print ""

print "To run Digsby:"
print "- run . denv to setup the environment for Digsby"
print "- Run Digsby.py"

