%ModuleHeaderCode
#include "ctextutil.h"
%End

wxRect Subtract(const wxRect& r, int left = 0, int right = 0, int up = 0, int down = 0);

void DrawTruncated(wxDC& dc,
                   const wxString& text,
                   const wxRect& rect,
                   int alignment = wxALIGN_LEFT | wxALIGN_TOP,
                   bool drawAccels = false,
                   wxFont* font = 0);


wxString truncateText(wxString& text,
                  int size,
                  wxFont* font = NULL,
                  wxDC* dc = NULL,
                  const wxString& thepostfix = wxT("..."));

//SIP_PYOBJECT RectPos(const wxRect& rect, const wxPoint& point);
wxPoint RectPosPoint(const wxRect& rect, const wxPoint& point);

wxRect RectAddMargins(const wxRect& r, const wxRect& margins);

wxString Wrap(const wxString& line, int width, wxFont* font = 0, wxDC* dc = 0, int maxlines = 0);

%If (WXMSW)
wxFont FitFontToRect(const wxFont& font, const wxRect& rect, const wxString& str, bool useWidth = true);
%End

