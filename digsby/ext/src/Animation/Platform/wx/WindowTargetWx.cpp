#include "Layer.h"
#include "WindowTarget.h"

#include <wx/dcclient.h>
#include <wx/gdicmn.h>

#include <wx/dcbuffer.h> // TODO: remove wxBufferedPaint usage

BEGIN_EVENT_TABLE(WindowTarget, wxWindow)
    EVT_PAINT(WindowTarget::OnPaint)
END_EVENT_TABLE()

WindowTarget::WindowTarget(wxWindow* parent, int id)
    : wxWindow(parent, id)
    , m_rootLayer(0)
{
    SetBackgroundStyle(wxBG_STYLE_CUSTOM);
}

void WindowTarget::invalidate(const Rect& rect)
{
    wxRect r(rect.m_x, rect.m_y, rect.m_width, rect.m_height);
    RefreshRect(r, false);
}

void WindowTarget::invalidate()
{
    Refresh(false);
}

void WindowTarget::setRootLayer(Layer* layer)
{
    ANIM_ASSERT(!layer->superlayer());
    m_rootLayer = layer;
}

void WindowTarget::OnPaint(wxPaintEvent& e)
{
    wxAutoBufferedPaintDC dc(this);
    dc.SetPen(*wxTRANSPARENT_PEN);
    dc.SetBrush(*wxWHITE_BRUSH);
    dc.DrawRectangle(GetClientRect());

    Layer* layer = rootLayer();
    if (layer) {
        wxGraphicsContext* gc = wxGraphicsContext::Create(dc);
        cairo_t* cr = (GraphicsContext*)gc->GetNativeContext();
        rootLayer()->drawInContext(cr);

        m_lastStatus = wxString::FromAscii(cairo_status_to_string(cairo_status(cr)));
    }
}

