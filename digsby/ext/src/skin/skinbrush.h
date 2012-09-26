#ifndef _SKINBRUSH_H_
#define _SKINBRUSH_H_

#include <wx/dc.h>
#include <wx/gdicmn.h>
#include <wx/colour.h>

#include "wx/renderer.h"


class SkinBrush {
public:
	SkinBrush();
	virtual ~SkinBrush();

    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);
	virtual void SetBorder(const wxPen& borderPen);

protected:
	wxPen pen;
};

class SkinColor : public SkinBrush {
public:
	SkinColor(const wxColour& color);
	virtual ~SkinColor();

	virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);

protected:
	wxBrush brush;
};

#endif