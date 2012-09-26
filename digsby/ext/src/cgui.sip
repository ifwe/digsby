%Module cgui

%Import wx.sip

%ModuleHeaderCode
#include <wx/wx.h>
%End

%Include ctextutil.sip
%Include splitimage4.sip
%Include cwindowfx.sip
%Include scrollwindow.sip
%Include skinvlist.sip
%Include alphaborder.sip
%Include skinsplitter.sip
%Include expando.sip

%Include sip/InputBox.sip
%Include sip/rtf.sip
%Include sip/SelectionEvent.sip

// skin 
%Include skin/skinobjects.sip
%Include skin/SkinBitmap.sip

%If (WXMSW)
%Include cgui_win.sip
%Include sip/PlatformMessages.sip
%Include sip/WindowSnapper.sip
%Include sip/Fullscreen.sip
%Include sip/win/WinUtils.sip
%Include sip/win/RichEditUtils.sip
%Include sip/MiscUI.sip
%Include sip/TransparentFrame.sip
%Include sip/Statistics.sip
%Include sip/win/WinTaskbar.sip
%Include sip/win/WinJumpList.sip
%Include sip/IconUtils.sip
%End

%Include sip/LoginWindow.sip
