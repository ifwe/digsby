%module cgui

%include splitimage4.i
%include ctextutil.i
%include cskin.i
%include cwindowfx.i
%include skinsplitter.i
%include alphaborder.i

%include LoginWindow.h
%{
#include "LoginWindow.h"
%}

#if __WXMSW__
%include win/win32.i
#endif
