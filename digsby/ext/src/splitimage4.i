// not a %module

%{
#include "wx/wxPython/wxPython.h"
#include "wx/wxPython/pyclasses.h"
#include "wx/wxPython/pyistream.h"

#include "SplitImage4.h"
#include <wx/dcbuffer.h>
#include <wx/metafile.h>
%}

%import typemaps.i
%import my_typemaps.i

%import core.i
%import windows.i
%import misc.i

%include SplitImage4.h
