
%{
#include "wx/wxPython/wxPython.h"
#include "wx/wxPython/pyclasses.h"
#include "wx/wxPython/pyistream.h"

#include <wx/splitter.h>
#include <wx/metafile.h>
#include <wx/dcbuffer.h>
#include <wx/brush.h>
#include "skinsplitter.h"
%}

%import typemaps.i
%import my_typemaps.i

%import core.i
%import windows.i
%import misc.i


%include skinsplitter.h