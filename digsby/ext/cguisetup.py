'''
defines all the sources necessary for building cgui.pyd
'''
import os

BUILD_BUDDYLIST_GUI = False
thisdir = os.path.dirname(os.path.abspath(__file__))

sources = '''
    src/ctextutil.cpp
    src/SplitImage4.cpp
    src/ScrollWindow.cpp
    src/skinvlist.cpp
    src/pyutils.cpp
    src/cwindowfx.cpp
    src/SkinSplitter.cpp
    src/alphaborder.cpp

    src/skin/skinobjects.cpp
    src/skin/SkinBitmap.cpp

    src/LoginWindow.cpp
    src/DragMixin.cpp
    src/MiscUI.cpp

    src/SelectionEvent.cpp
    src/InputBox.cpp
    src/ExpandoTextCtrl.cpp
    src/ExpandEvent.cpp
    src/GettextPython.cpp
'''.split()


include_dirs = '''
    src
    src/skin
    src/Animation
    src/Animation/Platform
    src/Animation/Platform/wx
    src/BuddyList
'''.split()

boost_env_dir = os.getenv('BOOST_DIR')
if boost_env_dir is not None:
    include_dirs.append(boost_env_dir)

# rtf
rtf_files = \
'''
DebugUtil.cpp
HTMLEncoder.cpp
MSIMEncoder.cpp
MSNEncoder.cpp
RTFToX.cpp
StyleDesc.cpp
StringUtil.cpp
XHTMLEncoder.cpp
YahooEncoder.cpp
'''.split()

sources.extend('src/RTFToX/%s' % s for s in rtf_files)
include_dirs.append('src/RTFToX')

import sys
if sys.platform == 'win32':
    sources.extend('''
        src/alphaborder_win.cpp
        src/win/PlatformMessagesWin.cpp

        src/win/WindowSnapperWin.cpp
        src/WindowSnapper.cpp

        src/win/FullscreenWin.cpp
        src/win/WinUtils.cpp
        src/win/WinTaskbar.cpp
        src/win/WinJumpList.cpp

        src/win/RichEditUtils.cpp

        src/TransparentFrame.cpp
        src/Statistics.cpp

        src/IconUtils.cpp
'''.split())

    include_dirs.extend([
        'src/win',
    ])

if BUILD_BUDDYLIST_GUI:
    sources.extend('''
    src/TreeList.cpp
    src/BuddyList.cpp
'''.split())

