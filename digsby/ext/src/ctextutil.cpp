#include "wx/wxprec.h"
#include "wx/string.h"
#include "wx/font.h"
#include <wx/fontutil.h>
#include "wx/dc.h"
#include <wx/dcbuffer.h>
#include <wx/dcmemory.h>
#include <wx/dcscreen.h>
#include <wx/gdicmn.h>
#include <wx/settings.h>
#include <wx/stattext.h>

#ifdef __WXMSW__
#include "wx/msw/private.h"
#endif //__WXMSW__

#ifndef WX_PRECOMP
#endif

#include "ctextutil.h"

#include <iostream>
using namespace std;

wxRect Subtract(const wxRect& rect, int left, int right, int up, int down)
{
    wxRect r(rect);
    r.Offset(left, up);
    r.SetSize(wxSize(r.width  - left - right,
                     r.height - up - down));
    return r;
}


bool GetFontHeight(short& lineHeight, wxFont* font, wxDC* dc, bool line_height, bool descent)
{
    bool needsDelete = false;
    if (!dc) {
        if (!font)
            return false;
        else {
            dc = new wxMemoryDC();
            needsDelete = true;
        }
    }

    static const wxString asciidigits = wxT("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789");
    int w, h, font_descent, externalLeading;
    dc->GetTextExtent(asciidigits, &w, &h, &font_descent, &externalLeading, font);

    if (line_height)
        lineHeight = h;
    else if (descent)
        lineHeight = descent;
    else
        lineHeight = h - descent + externalLeading;

    if (needsDelete)
        delete dc;

    return true;
}

wxPoint RectPosPoint(const wxRect& rect, const wxPoint& point)
{
    int x, y;
    int px = point.x;
    int py = point.y;

    if ( px < 0 )
        x = rect.x + rect.width + px;
    else
        x = rect.x + px;

    if ( py < 0 )
        y = rect.y + rect.height + py;
    else
        y = rect.y + py;

    return wxPoint(x, y);
}

wxRect RectAddMargins(const wxRect& rect, const wxRect& margins) {
    wxRect r(rect);
    r.x += margins.x;
    r.width -= margins.x;

    r.y      += margins.y;
    r.height -= margins.y;

    r.width  -= margins.width;
    r.height -= margins.height;

    return r;
}

#ifdef __WXMSW__
static int optionsForWxAlignment(int alignment)
{
    int options = 0;

    if (wxALIGN_LEFT & alignment)
        options |= DT_LEFT;
    if (wxALIGN_CENTER_HORIZONTAL & alignment)
        options |= DT_CENTER;
    if (wxALIGN_RIGHT & alignment)
        options |= DT_RIGHT;

    if (wxALIGN_TOP & alignment)
        options |= DT_TOP;
    if (wxALIGN_CENTER_VERTICAL & alignment)
        options |= DT_VCENTER;
    if (wxALIGN_BOTTOM & alignment)
        options |= DT_BOTTOM;

    return options;
}
#endif

void DrawTruncated(wxDC& dc,
                   const wxString& text,
                   const wxRect& rect,
                   int alignment,
                   bool drawAccels,
                   wxFont* font)
{
#ifdef __WXMSW__
    if (font)
        dc.SetFont(*font);


    HDC hdc = (HDC)dc.GetHDC();


    ::SetTextColor(hdc, dc.GetTextForeground().GetPixel());
    ::SetBkMode(hdc, TRANSPARENT);

    int textLen = text.Len();

    RECT r;
    r.left   = rect.x;
    r.top    = rect.y;
    r.right  = rect.x + rect.width;
    r.bottom = rect.y + rect.height;

    int format = optionsForWxAlignment(alignment);

    if (!drawAccels)
        format |= DT_NOPREFIX;

    format |= DT_END_ELLIPSIS | DT_NOCLIP;

    if (!DrawTextEx(hdc, (LPWSTR)text.wc_str(), textLen, &r, format, 0))
        fprintf(stderr, "DrawTextEx error %d\n", GetLastError());
#else

    wxFAIL_MSG(wxT("drawtruncated not implemented on this platform"));

#endif
}


/**
  Truncates the given text to a specified width, in pixels.

  The string is truncated so that "thepostfix" can be appended at the end
  (by default "...")

  If a font is not given the DC's current font is used.
*/
wxString truncateText(wxString& text,
                      int size,
                      wxFont* font /* = NULL */,
                      wxDC* dc /* = NULL */,
                      const wxString& thepostfix /* = wxT("...") */)
{
    // unconstify
    wxString postfix(thepostfix);

    bool destroy = false;
    if ( dc == NULL ) {
#ifdef __WXMAC__
        dc = new wxScreenDC();
#else
        dc = new wxMemoryDC();
#endif
        destroy = true;
    }

    wxFont dcFont(dc->GetFont());
    if (font == NULL)
        font = &dcFont;

    // Early exit if the string is small enough to fit.
    int textSize, _y;
    dc->GetTextExtent(text, &textSize, &_y, NULL, NULL, font);
    if (textSize <= size)
    {
        if (destroy && dc)
            delete dc;
        
        return text;
    }

    // Now make sure that our postfix string fits.
    int postfixSize;
    dc->GetTextExtent(postfix, &postfixSize, &_y, NULL, NULL, font);

    while (postfixSize > size) {
        postfix.Truncate(postfix.Len() - 1);
        dc->GetTextExtent(postfix, &postfixSize, &_y, NULL, NULL, font);
        if (postfixSize < size || postfix.Len() == 0)
            return postfix;
    }

    size -= postfixSize;


    wxString substr;
    int low = 0, high = text.Len(), mid = 0;
    int oldMid;
    int tempWidth;
    substr = text(low, high);

    // Do a binary search to find the best number of characters that will fit
    // in the desired space.
    if (textSize > size) {
        while (textSize > size) {
            oldMid = mid;
            mid    = (low + high) / 2;
            substr = text(0, mid);

            if (oldMid == mid) {
                text = substr;
                break;
            }

            dc->GetTextExtent(substr, &tempWidth, &_y, NULL, NULL, font);

            if (tempWidth > size)
                high = mid - 1;
            else
                low = mid + 1;
        }
    }

    // clean up the wxMemoryDC
    if (destroy && dc)
        delete dc;

    return text + postfix;
}

void TextWrapper::DoWrap(wxDC *dc, wxFont* font, const wxString& text, int widthMax, int maxlines)
{
    bool needsDelete = false;

    if (!dc) {
#ifdef __WXMAC__
        dc = new wxScreenDC();
#else
        dc = new wxMemoryDC();
#endif
        needsDelete = true;
    }

    if (font)
        dc->SetFont(*font);

    if (!maxlines)
        maxlines = 32767;

    const wxChar *lastSpace = NULL;
    wxString line;

    const wxChar *lineStart = text.c_str();
    for ( const wxChar *p = lineStart; ; ++p )
    {
        if ( IsStartOfNewLine() )
        {
            OnNewLine();

            lastSpace = NULL;
            line.clear();
            lineStart = p;
        }

        if ( *p == _T('\n') || *p == _T('\0') )
        {
            DoOutputLine(line);

            if ( *p == _T('\0') )
                break;
        }
        else // not EOL
        {
            if ( *p == _T(' ') )
                lastSpace = p;

            line += *p;

            if ( widthMax >= 0 && lastSpace )
            {
                int width;
                dc->GetTextExtent(line, &width, NULL);

                if ( width > widthMax )
                {
                    // remove the last word from this line
                    line.erase(lastSpace - lineStart, p + 1 - lineStart);
                    DoOutputLine(line);
                    if (m_linecount > maxlines)
                        break;

                    // go back to the last word of this line which we didn't
                    // output yet
                    p = lastSpace;
                }
            }
            //else: no wrapping at all or impossible to wrap
        }
    }

    if (needsDelete)
        delete dc;
}

wxString Wrap(const wxString& line, int width, wxFont* font, wxDC* dc, int maxlines)
{
    return TextWrapper().Wrap(dc, font, line, width, maxlines);
}


#ifdef __WXMSW__

static inline void wxRectToRECT(const wxRect& wxrect, RECT* rect)
{
    rect->left = wxrect.x;
    rect->top = wxrect.y;
    rect->right = wxrect.GetRight();
    rect->bottom = wxrect.GetBottom();
}

//Fits a given string, in a given font, into a givin rectangle returning the new font.  useWidth determins if the rectangles width is ignored or not
//original code blatently coppied from http://www.codeguru.com/forum/showthread.php?t=379565
//thanks Pravin Kumar 
//Aaron added the useWidth logics
//Kevin converted it to return a wxFont instead of drawing the text itself
static wxFont FitFontToRectWin(HFONT hFont, LPRECT lprect, LPWSTR lpstr, BOOL useWidth = TRUE)
{
    // Gets LOGFONT structure corresponding to current font
    LOGFONT LogFont;
    if (GetObject(hFont, sizeof(LOGFONT), &LogFont) == 0)
        return wxNullFont;

    // Calculates span of the string sets rough font width and height
    int Len = wcslen(lpstr);
    int Width = 0xfffffff;

    MemoryHDC hdc;

    if (useWidth) {
        Width = lprect->right - lprect->left;
        LogFont.lfWidth = -MulDiv(Width / Len, GetDeviceCaps(hdc, LOGPIXELSX), 72);
    } else {
        LogFont.lfWidth = 0;
    }

    int Height = lprect->bottom - lprect->top;
    LogFont.lfHeight = -MulDiv(Height, GetDeviceCaps(hdc, LOGPIXELSY), 72);

    // Creates and sets font to device context
    hFont = CreateFontIndirect(&LogFont);
    HFONT hOldFont = (HFONT) SelectObject(hdc, hFont);

    // Gets the string span and text metrics with current font
    SIZE Size;
    GetTextExtentExPoint(hdc, lpstr, Len, Width, NULL, NULL, &Size);
    TEXTMETRIC TextMetric;
    GetTextMetrics(hdc, &TextMetric);
    int RowSpace = TextMetric.tmExternalLeading;

    // Deselects and deletes rough font
    SelectObject(hdc, hOldFont);
    DeleteObject(hFont);

    // Updates font width and height with new information of string span
    LogFont.lfWidth = useWidth ? MulDiv(LogFont.lfWidth, Width, Size.cx) : 0;
    LogFont.lfHeight = MulDiv(LogFont.lfHeight, Height, Size.cy - RowSpace);

    // Creates and selects font of actual span filling the rectangle
    hFont = CreateFontIndirect(&LogFont);

    DeleteObject(hOldFont);

    // create a wxFont
    wxNativeFontInfo info;
    info.lf = LogFont;
    return wxFont(info, (WXHFONT)hFont);
}

//
// returns the best fitting wxFont that can fit in the given
// rectangle. if useWidth is false, only the height is used.
//
wxFont FitFontToRect(const wxFont& font, const wxRect& rect, const wxString& str, bool useWidth /*= true*/)
{
    RECT winrect;
    wxRectToRECT(rect, &winrect);
    wxWCharBuffer buf(str.wc_str());
    return FitFontToRectWin((HFONT)font.GetHFONT(), &winrect, buf.data(), useWidth);
}

bool
IsRTLLang(HKL langID){

    int plid = (int)langID & 0xFF;

    switch(plid){
        // TODO: this cannot possibly cover all the possible RTL cases.
        //
        // find out if there's a Windows function to get this info?
        // also, ICU can provide this information:
        // http://icu-project.org/apiref/icu4c/uloc_8h.html#badccaf9f7e7221cd2366c02f78bf5a9
        case LANG_ARABIC:
        case LANG_HEBREW:
        case LANG_SYRIAC:
        case LANG_URDU:
            return true;
        default:
            return false;
    
    }
}

#endif // __WXMSW__

