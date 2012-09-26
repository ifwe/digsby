// not a %module

%{
#include "wx/wxPython/wxPython.h"
#include "alphaborder.h"
#include "wx/wxPython/pyclasses.h"
#include "wx/wxPython/pseudodc.h"

#include <wx/event.h>
%}

%include "std_vector.i"
namespace std
{
    %template(FrameSize) vector<int>;
}

%import core.i
%import windows.i

%include "alphaborder.h"
