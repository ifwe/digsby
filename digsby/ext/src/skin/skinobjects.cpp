#include "skinobjects.h"
#include <iostream>
using namespace std;

#include <wx/graphics.h>
#include <wx/gdicmn.h>

//
// SkinBase
//

wxBitmap SkinBase::GetBitmap(const wxSize& size, int /*n*/)
{
  // TODO
  return wxBitmap(size.x, size.y);
}

SkinBase::~SkinBase() {}

//
// SkinStack
//

SkinStack::SkinStack(const vector<SkinBase*> skinregions)
  : regions(skinregions)
{

}

SkinStack::~SkinStack()
{
}

void SkinStack::Draw(wxDC& dc, const wxRect& rect, int n)
{
    for (size_t i = 0; i < regions.size(); ++i)
        regions[i]->Draw(dc, rect, n);
}

//
// SkinRegion
//

SkinRegion::SkinRegion(const wxPen& borderPen)
      : ytile(true)
      , rounded(false)
      , radius(3)
      , highlight(false)
      , shadow(false)
      , border(borderPen)
{
    has_border = borderPen != *wxTRANSPARENT_PEN;
}

SkinRegion::~SkinRegion()
{
}

void SkinRegion::SetOutline(const wxPen& pen, int rounded, bool highlight, bool shadow)
{
    this->border = pen;
    this->has_border = pen != *wxTRANSPARENT_PEN;
    this->rounded = rounded != 0;
    this->highlight = highlight;
    this->shadow = shadow;
}

void SkinRegion::Stroke(wxDC& dc, wxGraphicsContext* gc, const wxRect& rect, int /*n*/)
{
    if (!has_border)
        return;

    int penw = border.GetWidth() / 2.0f;

    wxRect r(rect);
    r.Deflate(penw, penw);
    //border.SetCap(wxCAP_PROJECTING);

    if (rounded) {
        bool needsDelete = false;
        if (!gc) {
           gc = wxGraphicsContext::Create((wxWindowDC&)dc);
           needsDelete = true;
        }

        gc->SetBrush(*wxTRANSPARENT_BRUSH);
        gc->SetPen(border);
        gc->DrawRoundedRectangle(rect.x, rect.y, rect.width, rect.height, rounded * .97);

        rect.Inflate(penw, penw);

        if (needsDelete)
            delete gc;
    } else {
        dc.SetPen(border);

        int offset = (int)(border.GetWidth() % 2 == 0);
        wxPoint x(offset, 0);
        wxPoint y(0, offset);

        dc.DrawLine(rect.GetTopLeft(), rect.GetBottomLeft() + y);
        dc.DrawLine(rect.GetBottomLeft() + y, rect.GetBottomRight() + y + x);
        dc.DrawLine(rect.GetBottomRight() + y + x, rect.GetTopRight() + x);
        dc.DrawLine(rect.GetTopRight() + x, rect.GetTopLeft());
    }
}

void SkinRegion::Draw(wxDC& /*dc*/, const wxRect& /*rect*/, int /*n*/)
{

}


//
// SkinColor
//

SkinColor::SkinColor(const wxColour& c)
  : wxColour(c)
  , SkinRegion(*wxTRANSPARENT_PEN)
{
    m_opaque = c.Alpha() == 255;
}

SkinColor::~SkinColor()
{
}

void SkinColor::Draw(wxDC& dc, const wxRect& rect, int n)
{
    dc.SetBrush(wxBrush(*this));
    dc.SetPen(*wxTRANSPARENT_PEN);

    Fill(dc, rect);
    Stroke(dc, 0, rect, n);
}

void SkinColor::Fill(wxDC& dc, const wxRect& rect)
{
    if (IsOpaque()) {
        if (rounded)
            dc.DrawRoundedRectangle(rect.x, rect.y, rect.width, rect.height, rounded);
        else
            dc.DrawRectangle(rect);
    } else {
#if __WXMSW__
        wxGraphicsContext* gc = wxGraphicsContext::Create(dc);
        gc->SetBrush(dc.GetBrush());
        gc->SetPen(*wxTRANSPARENT_PEN);
        if (rounded)
            gc->DrawRoundedRectangle(rect.x, rect.y, rect.width, rect.height, rounded);
        else
            gc->DrawRectangle(rect.x, rect.y, rect.width, rect.height);

        delete gc;
#endif
    }

}

//
// SkinGradient
//

SkinGradient::SkinGradient(int dir, const vector<wxColour>& cols)
      : SkinRegion(*wxTRANSPARENT_PEN)
      , direction(dir)
      , colors(cols)
{
    wxASSERT_MSG(dir == wxHORIZONTAL || dir == wxVERTICAL,
                 _T("SkinGradient's direction argument must be wxHORIZONTAL or wxVERTICAL") );

    ytile = direction == wxHORIZONTAL;
}

SkinGradient::~SkinGradient()
{
}

void SkinGradient::GenRects(wxGraphicsContext* gc, const wxRect& therect)
{
    if (0 && therect == oldRect) {
        // use already cached rectangles.
        //
        // TODO: this caching falls down with scrolling, since the position of each
        // incoming rectangle is different.
        return;
    }

    float x   = therect.x, y = therect.y;
    float w   = therect.width;
    float h   = therect.height;
    bool vert = direction == wxVERTICAL;

    float p1  = vert? therect.GetTop() : therect.GetLeft();

    size_t lc = colors.size() - 1;
    float dx  = (vert ? h : w) / float(lc);

    rects.clear();
    for (size_t i = 0; i < lc; ++i) {
        wxColour c1(colors[i]);
        wxColour c2(colors[i+1]);

        float delta = i == 0 || i == lc ? 1.0 : 0.0;
        if (vert)
            rects.push_back(BrushRect(
                    gc->CreateLinearGradientBrush(x, p1 - delta, x, p1 + dx + delta*2, c1, c2),
                    wxRect2DDouble(x, p1, w, dx + delta - 1)));
        else
            rects.push_back(BrushRect(
                    gc->CreateLinearGradientBrush(p1 - delta, y, p1 + dx + delta*2, y, c1, c2),
                    wxRect2DDouble(p1, y, dx + delta, h)));
        p1 += dx;
    }

    oldRect = therect;
}

void SkinGradient::Draw(wxDC& dc, const wxRect& rect, int n)
{
    wxGraphicsContext* gc = wxGraphicsContext::Create((wxWindowDC&)dc);
    gc->SetPen(*wxTRANSPARENT_PEN);
    gc->Clip(rect);

    GenRects(gc, rect);

    for (size_t i = 0; i < rects.size(); ++i) {
        gc->SetBrush(rects[i].brush);
        Fill(dc, gc, rects[i].rect);
    }

    Stroke(dc, gc, rect, n);

    delete gc;
}

void SkinGradient::Fill(wxDC& /*dc*/, wxGraphicsContext* gc, const wxRect2DDouble& rect)
{
    if (rounded)
        gc->DrawRoundedRectangle(rect.m_x, rect.m_y, rect.m_width, rect.m_height, radius);
    else
        gc->DrawRectangle(rect.m_x, rect.m_y, rect.m_width, rect.m_height);
}
