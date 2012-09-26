// not a %module

%{
#include "wx/wxPython/wxPython.h"
#include "wx/wxPython/pyclasses.h"
#include "wx/wxPython/pyistream.h"
#include <wx/panel.h>
#include <wx/timer.h>
#include <wx/gdicmn.h>
#include <wx/image.h>
#include <wx/bitmap.h>


#include "cwindowfx.h"
%}

%import typemaps.i
%import my_typemaps.i

%import core.i
%import windows.i
%import misc.i


%include cwindowfx.h
