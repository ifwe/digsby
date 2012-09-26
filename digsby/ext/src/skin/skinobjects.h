#ifndef _SKINOBJECTS_H_
#define _SKINOBJECTS_H_

#include "wx/wxprec.h"
#ifndef WX_PRECOMP
#include "wx/wx.h"
#include "wx/graphics.h"
#endif

#include <vector>

//
// The interface for all skin elements.
//
class SkinBase
{
public:
    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0) = 0;
    virtual wxBitmap GetBitmap(const wxSize& size, int n = 0);

    virtual ~SkinBase();
};


class SkinStack : public SkinBase
{
public:
    SkinStack(const std::vector<SkinBase*> skinregions);
    virtual ~SkinStack();

    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);
    const std::vector<SkinBase*> GetRegions() const { return regions; }

protected:
    std::vector<SkinBase*> regions;
};


class SkinRegion : public SkinBase
{
public:
    SkinRegion(const wxPen& borderPen);
    virtual ~SkinRegion();

    void SetOutline(const wxPen& pen, int rounded = 0, bool highlight = false, bool shadow = false);
    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);
    bool ytile;

    wxPen GetBorder() const { return border; }

protected:
    void Stroke(wxDC& dc, wxGraphicsContext* gc, const wxRect& rect, int n = 0);

    bool rounded;
    unsigned char radius;

    bool highlight;
    bool shadow;
    wxPen border;
    bool has_border;
};


class SkinColor : public wxColour, public SkinRegion
{
public:
    SkinColor(const wxColour& c);
    virtual ~SkinColor();

    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);

    bool IsOpaque() const { return m_opaque; }

protected:
    void Fill(wxDC& dc, const wxRect& rect);

    bool m_opaque;
};

struct BrushRect
{
    BrushRect(const wxGraphicsBrush& b, const wxRect2DDouble& r)
        : brush(b)
        , rect(r)
    {
    }

    wxGraphicsBrush brush;
    wxRect2DDouble rect;
};


class SkinGradient : public SkinRegion
{
public:
    SkinGradient(int dir, const std::vector<wxColour>& cols);
    virtual ~SkinGradient();

    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);

protected:
    void GenRects(wxGraphicsContext* gc, const wxRect& therect);
    void Fill(wxDC& dc, wxGraphicsContext* gc, const wxRect2DDouble& rect);



    std::vector<wxColour> colors;
    int direction;

    wxRect oldRect;
    std::vector<BrushRect> rects;
};

#endif
