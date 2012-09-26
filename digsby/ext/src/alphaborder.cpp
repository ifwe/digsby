//
// alphaborder.cpp
//

#include "alphaborder.h"

#if __WXMSW__
#include "alphaborder_win.h"
#endif

#include <wx/wx.h>
#include <wx/dcmemory.h>
#include <wx/dcbuffer.h>

IMPLEMENT_DYNAMIC_CLASS(AlphaBorder, wxFrame);

BEGIN_EVENT_TABLE(AlphaBorder, wxFrame)
    EVT_PAINT(AlphaBorder::OnPaint)
    EVT_MOUSE_EVENTS(AlphaBorder::OnMouseEvents)
END_EVENT_TABLE()

AlphaBorder::AlphaBorder(wxWindow* parent, SplitImage4* border, const vector<int>& frameSize, int style)
    : wxFrame(parent, -1, _T(""), wxDefaultPosition, wxDefaultSize,
              wxNO_BORDER | wxFRAME_SHAPED | wxFRAME_NO_TASKBAR | style)
    , m_border(border)
    , m_alpha(255)
    , cacheValid(false)
{
    // fprintf(stderr, "AlphaBorder::m_border %d %d %d %d\n", border->left, border->top, border->right, border->bottom);

    SetFrameSize(frameSize);
    SetBackgroundStyle(wxBG_STYLE_CUSTOM);

    parent->Connect(wxEVT_SHOW, wxShowEventHandler(AlphaBorder::OnParentShown),  NULL, this);
}


void AlphaBorder::SetBackground(SplitImage4* background)
{
    m_border = background;
    cacheValid = false;
}

AlphaBorder::~AlphaBorder()
{
}

void AlphaBorder::OnParentShown(wxShowEvent& e)
{
    e.Skip();
    Show(e.GetShow());
}

void AlphaBorder::OnParentSizing(wxSizeEvent& e)
{
    e.Skip();
    cacheValid = false;
    UpdatePosition(wxRect(GetParent()->GetPosition(), e.GetSize()));
}

void AlphaBorder::OnParentMoving(wxMoveEvent& e)
{
    e.Skip();
    UpdatePosition(wxRect(e.GetPosition(), GetParent()->GetSize()));
}

void AlphaBorder::SetFrameSize(const vector<int>& frameSize)
{
    SetFrameSize(frameSize[0], frameSize[1], frameSize[2], frameSize[3]);
}

void AlphaBorder::SetFrameSize(int left, int top, int right, int bottom)
{
    this->left   = left;
    this->top    = top;
    this->right  = right;
    this->bottom = bottom;
    cacheValid = false;
}

void AlphaBorder::UpdatePosition(const wxRect& r)
{
    wxRect before(GetRect());

#if __WXMSW__
    SetWindowPos((HWND)GetHWND(),
                 (HWND)GetParent()->GetHWND(),
                 r.x - this->left,
                 r.y - this->top,
                 r.width + this->left + this->right,
                 r.height + this->top + this->bottom,
                 SWP_NOACTIVATE | SWP_NOOWNERZORDER);
#else
    Move(r.x - this->left, r.y - this->top);
    SetSize(r.width  + this->left + this->right, r.height + this->top  + this->bottom);
#endif
    if (GetRect() != before)
        PaintAlphaBackground();
}

void AlphaBorder::OnPaint(wxPaintEvent&)
{
    wxPaintDC dc(this);
    PaintAlphaBackground();
}


void AlphaBorder::PaintAlphaBackground()
{
    wxBitmap bmp;
    if ( cacheValid && cachedSize == GetClientSize() && cachedBitmap.IsOk() ) {
        bmp = cachedBitmap;
    } else {
        wxSize csize(GetClientSize());
        bmp = m_border->GetBitmap(csize);
        wxRect clip(GetClipRect());

        // clip out the framesize
        wxMemoryDC memdc(bmp);
        memdc.SetLogicalFunction(wxCLEAR);
        memdc.DrawRectangle(GetClipRect());

        cachedBitmap = bmp;
        cacheValid = true;
        cachedSize = csize;
    }

#if __WXMSW__
    ApplyAlpha(this, bmp, m_alpha);
#endif
}

void AlphaBorder::OnMouseEvents(wxMouseEvent& e)
{
    if ( GetClipRect().Contains(e.GetPosition()) ) {
        if (e.Moving())
            SetCursor(GetParent()->GetCursor());
        GetParent()->GetEventHandler()->ProcessEvent(e);
    } else {
        SetCursor(wxNullCursor);
    }
}

void AlphaBorder::SetAlpha(unsigned char alpha, bool refresh)
{
    m_alpha = alpha;
    if (refresh)
        PaintAlphaBackground();
}


IMPLEMENT_DYNAMIC_CLASS(BorderedFrame, wxFrame);

BEGIN_EVENT_TABLE(BorderedFrame, wxFrame)
    EVT_PAINT(BorderedFrame::OnPaint)
END_EVENT_TABLE()

BorderedFrame::BorderedFrame(wxWindow* parent, SplitImage4* background, SplitImage4* border, const vector<int>& frameSize, int style)

    : wxFrame(parent, wxID_ANY, _T(""),
              wxDefaultPosition, wxSize(200,200),
// FIXME: Why is wxFRAME_SHAPED causing the frame not to display on Mac?
#ifndef __WXMAC__
              wxFRAME_SHAPED |
#endif
              wxNO_BORDER | wxFRAME_NO_TASKBAR | style)
    , splitBg(background)
    , cacheValid(false)
{
    //splitBg = new SplitImage4(background);

    SetBackgroundStyle(wxBG_STYLE_CUSTOM);
#if __WXMSW__
    alphaBorder = new AlphaBorder(this, border, frameSize, style);
#else
    alphaBorder = NULL;
#endif
}

bool BorderedFrame::SetBackground(SplitImage4* background, const vector<int>& frameSize)
{
    cacheValid = false;

    if (splitBg == background)
        return false;

    splitBg = background;
#if __WXMSW__
    alphaBorder->SetBackground(background);
    alphaBorder->SetFrameSize(frameSize);

    alphaBorder->UpdatePosition(GetScreenRect());
#endif
    Refresh();
    return true;
}

bool BorderedFrame::SetTransparent(int alpha)
{
    return SetTransparent((wxByte)alpha);
}

bool BorderedFrame::SetTransparent(wxByte alpha)
{
#if __WXMSW__
    alphaBorder->SetAlpha(alpha, true);
#endif
    return wxFrame::SetTransparent(alpha);
}

int BorderedFrame::GetAlpha() const
{
#if __WXMSW__
    return alphaBorder->m_alpha;
#else
    return 0;
#endif
}

BorderedFrame::~BorderedFrame()
{
    // all resources belong to the skin tree
}

void BorderedFrame::PaintBackground(wxDC& dc)
{
    wxSize csize(GetClientSize());

    if (!cacheValid || cachedSize != csize || !cachedBackground.Ok())
    {
        wxImage img = splitBg->splitimage.center->image.Scale(csize.x, csize.y);
        cachedBackground = wxBitmap(img);
        cachedSize = csize;
        cacheValid = true;
    }

    dc.DrawBitmap(cachedBackground, 0, 0, true);
}

void BorderedFrame::SetRect(const wxRect& rect)
{
#if __WXMSW__
      // this code uses DeferWindowPos, which allows you to move several
      // windows to new positions all at the same time, as part of a
      // "transaction" -- this is to keep the semi transparent border
      // exactly around the inner content window

      HDWP hdwp = BeginDeferWindowPos(2);

      if (hdwp)
          hdwp = DeferWindowPos(hdwp,
                  (HWND)GetHWND(),
                  0,
                  rect.x,
                  rect.y,
                  rect.width,
                  rect.height,
                  SWP_NOACTIVATE | SWP_NOOWNERZORDER | SWP_NOZORDER);
      else
          fprintf(stderr, "error beginning begindefer\n");

      if (hdwp)
          hdwp = DeferWindowPos(hdwp,
              (HWND)alphaBorder->GetHWND(),
              (HWND)GetHWND(),
              rect.x - alphaBorder->left,
              rect.y - alphaBorder->top,
              rect.width + alphaBorder->left + alphaBorder->right,
              rect.height + alphaBorder->top + alphaBorder->bottom,
              SWP_NOACTIVATE | SWP_NOOWNERZORDER | SWP_NOCOPYBITS | SWP_NOREDRAW);
      else
          fprintf(stderr, "error positioning middle\n");

      if (hdwp) {
          EndDeferWindowPos(hdwp);
          alphaBorder->PaintAlphaBackground();
      } else
          fprintf(stderr, "error positioning border\n");
#else
      SetSize(rect);
#endif
}

void BorderedFrame::OnPaint(wxPaintEvent&)
{
    wxAutoBufferedPaintDC pdc(this);
    PaintBackground(pdc);
}


void BorderedFrame::SetFrameSize(const vector<int>& frameSize)
{
#if __WXMSW__
    alphaBorder->SetFrameSize(frameSize);
#endif
}

bool BorderedFrame::SetCursor(const wxCursor& cursor)
{
    return wxFrame::SetCursor(cursor);
}
