#ifndef _CTEXTUTIL_H_
#define _CTEXTUTIL_H_

#include "wx/defs.h"
#include <wx/string.h>
#include "wx/dc.h"
#include <wx/dcbuffer.h>
#include <wx/dcmemory.h>
#include <wx/dcscreen.h>
#include <wx/metafile.h>
#include <wx/gdicmn.h>

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

wxPoint RectPosPoint(const wxRect& rect, const wxPoint& point);

wxRect RectAddMargins(const wxRect& r, const wxRect& margins);

bool GetFontHeight(short& lineHeight, wxFont* font = 0, wxDC* dc = 0, bool line_height = false, bool descent = false);



class TextWrapper
{
public:
    TextWrapper()
        : m_eol(false)
        , m_linecount(0)
    {}

    wxString Wrap(wxDC *dc, wxFont* font, const wxString& text, int widthMax, int maxlines = -1)
    {
        m_text.clear();
        DoWrap(dc, font, text, widthMax, maxlines);
        return m_text;
    }

    // win is used for getting the font, text is the text to wrap, width is the
    // max line width or -1 to disable wrapping
    void DoWrap(wxDC *win, wxFont* font, const wxString& text, int widthMax, int maxlines);

    // we don't need it, but just to avoid compiler warnings
    virtual ~TextWrapper() { }

protected:
    // line may be empty
    virtual void OnOutputLine(const wxString& line)
    {
        m_text += line;
    }

    // called at the start of every new line (except the very first one)
    virtual void OnNewLine()
    {
        m_text += _T('\n');
    }

private:
    // call OnOutputLine() and set m_eol to true
    void DoOutputLine(const wxString& line)
    {
        OnOutputLine(line);

        ++m_linecount;
        m_eol = true;
    }

    // this function is a destructive inspector: when it returns true it also
    // resets the flag to false so calling it again woulnd't return true any
    // more
    bool IsStartOfNewLine()
    {
        if ( !m_eol )
            return false;

        m_eol = false;

        return true;
    }


    bool m_eol;
    int m_linecount;


private:
    wxString m_text;
};

wxString Wrap(const wxString& line, int width, wxFont* font = 0, wxDC* dc = 0, int maxlines = 0);

#ifdef __WXMSW__
wxFont FitFontToRect(const wxFont& font, const wxRect& rect, const wxString& str, bool useWidth = true);
bool IsRTLLang(HKL langID);
#endif


#endif
