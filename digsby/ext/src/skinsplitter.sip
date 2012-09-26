%ModuleHeaderCode
#include "skinsplitter.h"
%End

enum SplitterStates
{
    NORMAL = 0,
    ACTIVE = 1,
    HOVER  = 2
};

class SkinSplitter : wxSplitterWindow
{
public:
    SkinSplitter(wxWindow* parent /TransferThis/, long style = wxSP_LIVE_UPDATE | wxNO_BORDER);
    virtual ~SkinSplitter();
    void SetSplitterColors(const wxColour& normal, const wxColour& active, const wxColour& hover);
    void SetNative(bool native);
    bool GetNative() const;
};
