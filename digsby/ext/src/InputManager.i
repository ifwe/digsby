// not a %module

%{
#include "wx/wxPython/wxPython.h"
#include "inputmanager.h"
#include "wx/wxPython/pyclasses.h"
#include "wx/wxPython/pseudodc.h"

#include <wx/event.h>
%}

%import core.i
%import gdi.i
%import _window.i
%import _gdicmn.i
%import _statctrls.i
%import _pseudodc.i
%import _effects.i

// %include "inputmanager.h"
