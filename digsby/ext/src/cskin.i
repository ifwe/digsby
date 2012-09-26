%{
#include "wx/wxPython/wxPython.h"
#include "wx/wxPython/pyclasses.h"

#include "skinobjects.h"
#include "skinvlist.h"
#include "scrollwindow.h"
#include <wx/wx.h>
%}

%include "std_vector.i"
%import windows.i
%include "typemaps.i"

namespace std {
    %template(ColorList) vector<wxColour>;
    %template(UintList) vector<unsigned int>;
}

%include "scrollwindow.h"
%include "skinvlist.h"
%include "skinobjects.h"