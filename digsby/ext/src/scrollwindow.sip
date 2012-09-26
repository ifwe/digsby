%ModuleHeaderCode
#include "scrollwindow.h"
%End
class SkinScrollWindow : wxWindow
{
public:
    SkinScrollWindow(wxWindow* parent /TransferThis/, wxWindowID = -1, int style = wxBORDER_NONE);
    virtual ~SkinScrollWindow();

    void AdjustScrollbars(int x = -1, int y = -1);
    void PrepareDC(wxDC& dc);

    void Scroll(int x, int y);
    void EnablePhysicalScrolling(bool enable);
    bool IsPhysicalScrollingEnabled() const;

    void SetVirtualSize(const wxSize& size);
    void SetVirtualSize(int width, int height);

    int GetViewStart() const;
    wxRect GetViewRect() const;

    bool CanSmoothScroll() const;
    bool SetSmoothScrolling(bool useSmooth);

%If (WXMSW)
    void ScrollWindow(int dx, int dy, const wxRect* prect = NULL);
%End

};