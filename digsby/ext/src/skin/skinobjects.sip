%ModuleHeaderCode
#include "skinobjects.h"
%End

class SkinBase
{
private:
    SkinBase();
    SkinBase(const SkinBase&);
public:
    virtual ~SkinBase();

    void Draw(wxDC& dc, const wxRect& rect, int n = 0) = 0;
    wxBitmap GetBitmap(const wxSize& size, int n = 0);
};


class SkinStack : SkinBase
{
private:
    SkinStack();
    SkinStack(const SkinStack&);
public:
    //SkinStack(const std::vector<SkinBase*> skinregions);
    virtual ~SkinStack();

    void Draw(wxDC& dc, const wxRect& rect, int n = 0);
    //const std::vector<SkinBase*> GetRegions() const;
};


class SkinRegion : SkinBase
{
private:
    SkinRegion(const SkinRegion&);
    SkinRegion();

public:
    SkinRegion(const wxPen& borderPen);
    virtual ~SkinRegion();

    void SetOutline(const wxPen& pen, int rounded = 0, bool highlight = false, bool shadow = false);
    void Draw(wxDC& dc, const wxRect& rect, int n = 0);
    bool ytile;
    wxPen GetBorder() const;
};


class SkinColor : SkinRegion, wxColour
{
private:
    SkinColor();
    SkinColor(const SkinColor&);
public:
    SkinColor(const wxColour& c);
    virtual ~SkinColor();

    void Draw(wxDC& dc, const wxRect& rect, int n = 0);
    bool IsOpaque() const;

    int __getitem__(int i);
%MethodCode
    switch (a0) {
        case 0: sipRes = sipCpp->Red();   break;
        case 1: sipRes = sipCpp->Green(); break;
        case 2: sipRes = sipCpp->Blue();  break;
        case 3: sipRes = sipCpp->Alpha(); break;
        default:
            PyErr_Format(PyExc_IndexError, "index out of range: %d", a0);
            sipIsErr = 1;
    }
%End
};


class SkinGradient : SkinRegion
{
private:
    SkinGradient();
    SkinGradient(const SkinGradient&);
public:
    SkinGradient(int dir, const std::vector<wxColour>& cols);
    virtual ~SkinGradient();

    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);
};
