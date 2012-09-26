%ModuleHeaderCode
#include "ExpandoTextCtrl.h"
%End

typedef int WXTYPE;

enum
{
    wxEVT_ETC_LAYOUT_NEEDED
};

class wxExpandEvent : wxCommandEvent
{
%ConvertToSubClassCode
wxClassInfo* c = sipCpp->GetClassInfo();

if(0) ;
#define C(clz) else if (c == CLASSINFO(clz)) sipClass = sipClass_ ## clz;
    C(wxExpandEvent)
else
    sipClass = NULL;
#undef C
%End

public:
    wxExpandEvent(WXTYPE commandEventType = 0, int id = 0);
    wxExpandEvent(const wxExpandEvent &event);

    int height;
    int numLines;
};

class ExpandoTextCtrl : InputBox
{
public:
    ExpandoTextCtrl(wxWindow *parent, wxWindowID id = wxID_ANY,
                    const wxString& value = wxEmptyString,
                    const wxPoint& pos = wxDefaultPosition,
                    const wxSize& size = wxDefaultSize,
                    long  style = 0,
                    const wxValidator& validator = wxDefaultValidator,
                    const wxString& name = wxTextCtrlNameStr);
    virtual ~ExpandoTextCtrl();

    bool SetStyle(long start, long end, const wxTextAttr& style);
    void SetMinHeight(const int& h);
    int  GetMinHeight() const;
    void SetMaxHeight(const int& h);
    int  GetMaxHeight() const;
    int  GetDecHeight() const;
    int  GetNatHeight() const;
    void RequestResize();
    void AdjustCtrl(long height);
};
