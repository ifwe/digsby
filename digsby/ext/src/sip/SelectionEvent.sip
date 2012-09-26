%ModuleHeaderCode
#include "SelectionEvent.h"
%End

enum
{
    wxEVT_SELECTION_CHANGED
};

class wxSelectionEvent : wxCommandEvent
{

%ConvertToSubClassCode
wxClassInfo* c = sipCpp->GetClassInfo();

if(0) ;
#define C(clz) else if (c == CLASSINFO(clz)) sipClass = sipClass_ ## clz;
    C(wxSelectionEvent)
else
    sipClass = NULL;
#undef C
%End

public:
    wxSelectionEvent(int commandEventType = 0, int id = 0, long selectionStart = 0, long selectionEnd = -1);
    wxSelectionEvent(const wxSelectionEvent &event);

    long selectionStart;
    long selectionEnd;
};

