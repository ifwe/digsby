#include "skinbrush.h"

SkinBrush::SkinBrush() {}
SkinBrush::~SkinBrush() {}

void SkinBrush::SetBorder(const wxPen& borderPen) {
	pen = borderPen;
}

void SkinBrush::Draw(wxDC& dc, const wxRect& rect, int n)
{

}

SkinColor::SkinColor(const wxColour& color)
    : brush(wxBrush(color))
{
}

SkinColor::~SkinColor() {}

void SkinColor::Draw(wxDC& dc, const wxRect& rect, int n) {
	dc.SetBrush(brush);
	dc.SetPen(pen);
	dc.DrawRectangle(rect);
}
