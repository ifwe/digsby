//
// alphaborder.h
//

#ifndef _ALPHABORDER_H_
#define _ALPHABORDER_H_

// NOTE: You should always include at least this first to set up wx defines.
#include <wx/defs.h>
#include <wx/frame.h>
#include "SplitImage4.h"
#include <vector>

using std::vector;

//
#if __WXMSW__
bool ApplyAlpha(wxWindow* window, wxBitmap& bitmap, unsigned char alpha /* = 255*/);
#endif

typedef std::vector<int> FrameSize;

class AlphaBorder : public wxFrame
{
public:
#if SWIG
    %pythonAppend AlphaBorder "self._setOORInfo(self)"
#else
    DECLARE_DYNAMIC_CLASS( AlphaBorder )
#endif
    AlphaBorder() {}
    AlphaBorder(wxWindow* parent, SplitImage4* border, const FrameSize& frameSize, int style = 0);
    virtual ~AlphaBorder();

    void SetBackground(SplitImage4* background);
    void UpdatePosition(const wxRect& r);
    void PaintAlphaBackground();

    SplitImage4* m_border;


    wxRect GetClipRect() const {
        wxRect clip(GetClientSize());
        clip.x += left;
        clip.width -= right + left;
        clip.y += top;
        clip.height -= top + bottom;
        return clip;
    }


    void SetFrameSize(const FrameSize& frameSize);
    void SetFrameSize(int left, int top, int right, int bottom);
    void SetAlpha(unsigned char alpha, bool refresh = false);
    int m_alpha;

    int left, top, right, bottom;


#ifndef SWIG
protected:
    wxBitmap cachedBitmap;
    wxSize   cachedSize;
    bool     cacheValid;

    void OnParentShown(wxShowEvent& e);
    void OnParentSizing(wxSizeEvent& e);
    void OnParentMoving(wxMoveEvent& e);
    void OnPaint(wxPaintEvent& e);
    void OnMouseEvents(wxMouseEvent& e);

    DECLARE_EVENT_TABLE()
#endif
};

//

class BorderedFrame : public wxFrame
{
public:
#if SWIG
    %pythonAppend BorderedFrame "self._setOORInfo(self)"
#else
    DECLARE_DYNAMIC_CLASS( BorderedFrame )
#endif

    BorderedFrame() {}
    BorderedFrame(wxWindow* parent, SplitImage4* background, SplitImage4* border, const FrameSize& frameSize, int style = 0);
    ~BorderedFrame();

    bool SetBackground(SplitImage4* background, const vector<int>& frameSize);
    void SetFrameSize(const FrameSize& frameSize);
    void SetRect(const wxRect& rect);


    virtual bool SetTransparent(wxByte alpha);
    bool SetTransparent(int alpha);
    int  GetAlpha() const;

    virtual bool SetCursor(const wxCursor& cursor);

    void PaintBackground(wxDC& dc);
    void OnPaint(wxPaintEvent& dc);

    SplitImage4* splitBg;
    AlphaBorder* alphaBorder;

#ifndef SWIG
protected:

    wxBitmap cachedBackground;
    wxSize   cachedSize;
    bool     cacheValid;

    DECLARE_EVENT_TABLE()
#endif
};

#endif
