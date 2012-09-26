#!/usr/bin/python
#__LICENSE_GOES_HERE__
"""
To run, use:

build-appbundle.py py2app --no-strip (we probably shouldn't strip until we have it working everywhere)
"""

from distutils.core import setup
import py2app
import glob
import os
import shutil
import sys
import py_compile

myplist = dict(
    CFBundleIdentifier='com.dotsintax.digsby',
    CFBundleDisplayName="Digsby",
    CFBundleVersion="0.1" # FIXME: Get the version from Digsby
    )

rootdir = os.path.abspath(os.path.join(sys.path[0], "../.."))

distDir = os.path.join(rootdir, "dist")
bundleRoot = os.path.join(distDir, "Digsby.app")

# building a new bundle over an old one sometimes causes weird problems
if os.path.exists(distDir):
    shutil.rmtree(distDir)

os.system("rm -rf %s" % os.path.join(rootdir, "build", "bdist.macosx*"))

sys.path += [rootdir]

from config import *

sys.path += [rootdir + '/src', rootdir + '/ext/' + platformName, rootdir + '/lib', rootdir + '/platlib/' + platformName, rootdir + '/thirdparty']

import AutoUpdate.AutoUpdate as update

py2app_options = dict(
    iconfile=os.path.join(rootdir, "res/digsby.icns"),
    argv_emulation=True,
    plist=myplist,
    #optimize=1,
    # these modules need included because py2app doesn't find dynamically loaded
    # modules
    includes =  [
                    "AppKit",
                    "Authorization",
                    "common.AchievementMixin",
                    "common.asynchttp",
                    "common.asynchttp.server",
                    "common.oauth_util",
                    "decimal",
                    "email.iterators",
                    "email.generator",
                    "feedparser",
                    "Foundation",
                    "gtalk",
                    "gtalk.gtalk",
                    "gtalk.gtalkStream",
                    "gui.autocomplete",
                    "gui.browser.webkit.imageloader",
                    "gui.native.mac",
                    "gui.native.mac.macdocking",
                    "gui.native.mac.maceffects",
                    "gui.native.mac.macextensions",
                    "gui.native.mac.machelpers",
                    "gui.native.mac.macpaths",
                    "gui.native.mac.macsysinfo",
                    "gui.native.mac.toplevel",
                    "gui.pref.*",
                    "jabber",
                    "jabber.objects.gmail",
                    "lxml._elementpath",
                    "lxml.objectify",
                    "mail.*",
                    "mail.hotmail",
                    "msn",
                    "msn.p8",
                    "msn.p9",
                    "msn.p10",
                    "msn.p11",
                    "msn.p12",
                    "msn.p13",
                    "msn.p14",
                    "msn.p15",
                    "msn.SOAP",
                    "oauth",
                    "oauth.oauth",
                    "objc",
                    "oscar",
                    "svnrev",
                    "util.hook_util",
                    "util.httptools",
                    "yahoo",

                ],
)

def get_svn_rev():
    appbundle_dir, __ = os.path.split(__file__)
    f = open(os.path.join(appbundle_dir, '.svn', 'entries'))
    rev = 'XXXX'
    seen_dir = False
    for line in f:
        if not seen_dir:
            if 'dir' in line:
                seen_dir = True
            else:
                continue
        else:
            try:
                rev = int(line)
            except Exception:
                continue
            else:
                break

    f.close()
    return rev

f = open('svnrev.py', 'w')
f.write('REVISION = %d' % get_svn_rev())
f.close()

py_compile.compile("lib/AutoUpdate/mac_updater.py")

setup(
    name="Digsby",
    install_requires=["pyobjc"],
    app=[os.path.join(rootdir,'Digsby.py')],
    data_files = [
        ('', ['res']),
        ('lib/python2.6/site-packages', [os.path.join(rootdir, 'src/plugins')]
                + [os.path.join(rootdir, "lib/AutoUpdate/mac_updater.pyc")]
        ),
    ],
    options=dict(py2app=py2app_options)
)

# Now we get to undo a lot of what py2app did...
resourceDir = os.path.join(bundleRoot, "Contents", "Resources")
sitePackageDir = os.path.join(resourceDir, "lib", "python2.6")

os.chdir(sitePackageDir)
os.system("unzip -d site-packages site-packages.zip")

os.remove("site-packages.zip")

# excludes do not seem to work as well as includes do :(
if os.path.exists("site-packages/devmode.pyc"):
    os.remove("site-packages/devmode.pyc")

# Something is pulling in Tk and Tcl. I tried setting tkinter in the exclude modules,
# but it didn't make a difference. (well, I don't think tkinter itself is included,
# just the C++ libs. So we will remove Tk and Tcl ourselves...

frameworksDir = os.path.join(bundleRoot, "Contents", "Frameworks")
tclDir = os.path.join(frameworksDir, "Tcl.framework")
if os.path.exists(tclDir):
    shutil.rmtree(tclDir)

tkDir = os.path.join(frameworksDir, "Tk.framework")
if os.path.exists(tkDir):
    shutil.rmtree(tkDir)

# The wx libs get messed up, so we have to fix them manually...
os.chdir(frameworksDir)
files = glob.glob("libwx*2.9.dylib")

for afile in files:
    base = afile.replace("2.9.dylib", "")
    libs = glob.glob(base + "*")
    if len(libs) == 2:
        os.remove(afile)
        reallib = glob.glob(base + "*")[0]
        os.symlink(reallib, afile)


# clean up files we don't want in the package
ignorePatterns = [".svn", ".git"]
for ignore in ignorePatterns:
    os.system("find %s -name %s -exec rm -rf {} \;" % (os.path.join(rootdir, "dist", "Digsby.app"), ignore))

for root, subFolders, files in os.walk(os.path.join(rootdir, "dist")):
     for file in files:
         add = True
         fullpath = os.path.join(root, file)
         if file.startswith("."):
             print "removing %s" % fullpath
             os.remove(fullpath)
         elif root.find("plugins") != -1 and file.endswith(".py"):
            py_compile.compile(fullpath)
            os.remove(fullpath)


manifest = update.generate_manifest(os.path.join(rootdir, "dist", "Digsby.app"))
manifestFile = os.path.join(rootdir, "dist", "manifest.mac")
f = open(manifestFile, "w")
f.write(manifest.encode('utf8'))
f.close()

shutil.copyfile(manifestFile, os.path.join(resourceDir, "manifest.mac"))

