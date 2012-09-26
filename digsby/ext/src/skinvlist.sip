%ModuleHeaderCode
#include "scrollwindow.h"
#include "skinvlist.h"
#include <vector>
%End

class SkinVList : SkinScrollWindow
{
public:
    SkinVList(wxWindow* parent /TransferThis/, wxWindowID id = wxID_ANY, int style = wxLB_SINGLE);
    virtual ~SkinVList();

    bool SetHeights(const std::vector<unsigned int>& newHeights);

    int  HitTest(wxCoord x, wxCoord y) const;
    int  HitTest(const wxPoint& pt) const;

    int  HitTestEx(wxCoord x, wxCoord y, float* percent) const;

    bool ScrollToLine(size_t line);

    void RefreshLine(size_t line);
    void RefreshLines(size_t a, size_t b);
    void RefreshAll();

    size_t GetRowCount() const;
    size_t GetItemCount() const;

    void SetSelection(int selection, bool keepVisible = true);
    bool HasMultipleSelection() const;
    int  GetSelection() const;
    bool IsSelected(size_t row) const;


    size_t GetFirstVisibleLine() const;
    size_t GetLastVisibleLine() const;
    bool   IsVisible(size_t i) const;
    wxRect GetItemRect(size_t i) const;
    int    GetItemY(size_t i) const;

    //void SetBackground(SkinRegion* background);
    //SIP_PYOBJECT GetBackground() const;

    void OnDrawItem(wxDC& dc, const wxRect& rect, int n);

    void SetBackground(SIP_PYOBJECT background);
    void SetDrawCallback(SIP_PYOBJECT drawCallback);
    void SetPaintCallback(SIP_PYOBJECT paintCallback);
    //SIP_PYOBJECT GetDrawCallback() const;
};
