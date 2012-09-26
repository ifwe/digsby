#include "TransparentFrame.h"
#include "alphaborder_win.h"
#include "cwindowfx.h"

#include <wx/dcmemory.h>

IMPLEMENT_CLASS(TransparentFrame, wxFrame);

BEGIN_EVENT_TABLE(TransparentFrame, wxFrame)
    EVT_PAINT(TransparentFrame::OnPaint)
END_EVENT_TABLE()

#define DEFAULT_TRANSPARENTFRAME_STYLE \
    (wxNO_BORDER | wxFRAME_SHAPED | wxFRAME_NO_TASKBAR)
TransparentFrame::TransparentFrame(wxWindow* parent)
    : wxFrame(parent, wxID_ANY, _T(""), wxDefaultPosition, wxDefaultSize,
              DEFAULT_TRANSPARENTFRAME_STYLE)
    , m_alpha(255)
{
}

TransparentFrame::~TransparentFrame()
{
}

void TransparentFrame::OnPaint(wxPaintEvent& e)
{
    wxPaintDC dc(this);
    dc.Clear();
    wxBitmap bmp(GetBitmap());
    Unpremultiply(bmp);
    ApplyAlpha(this, bmp, m_alpha);
}

wxBitmap TransparentFrame::GetBitmap()
{
    wxBitmap bmp(GetClientSize().x, GetClientSize().y, 32);

    wxMemoryDC dc;
    dc.SelectObject(bmp);
    dc.SetBrush(*wxRED_BRUSH);
    dc.DrawRectangle(20, 20, 50, 50);
    dc.SelectObject(wxNullBitmap);

    return bmp;
}

