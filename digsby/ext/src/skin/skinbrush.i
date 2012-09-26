
%{
#include "wx/wxPython/wxPython.h"
#include "wx/wxPython/pyclasses.h"
#include "wx/wxPython/pyistream.h"

#include <wx/dcbuffer.h>
#include <wx/metafile.h>
#include <wx/colour.h>

#include "skinbrush.h"
%}

%import typemaps.i
%import my_typemaps.i

%import core.i
%import windows.i
%import misc.i
%import _button.i
%import _dc.i
%import _colour.i

%pythoncode { wx = wx._core }
%pythoncode { __docfilter__ = wx.__DocFilter(globals()) }


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
