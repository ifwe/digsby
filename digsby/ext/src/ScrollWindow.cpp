#include "ScrollWindow.h"

#include <iostream>
using namespace std;

IMPLEMENT_CLASS(SkinScrollWindow, wxWindow);

BEGIN_EVENT_TABLE(SkinScrollWindow, wxWindow)
    EVT_SIZE(SkinScrollWindow::OnSize)
    EVT_SCROLLWIN(SkinScrollWindow::OnScroll)
    EVT_MOUSEWHEEL(SkinScrollWindow::OnMouseWheel)
END_EVENT_TABLE()

#define DEBUG(_x) ((void) 0)
//#define DEBUG(_x) _x


SkinScrollWindow::SkinScrollWindow(wxWindow* parent, wxWindowID id, int style)
    : wxWindow(parent, id, wxDefaultPosition, wxDefaultSize, style)
    , physicalScrolling(true)
    , smoothScroll(false)
{
}

SkinScrollWindow::~SkinScrollWindow()
{
}

void SkinScrollWindow::AdjustScrollbars(int x, int y)
{
    wxRect r(GetRect());
    wxRect virtualRect(GetVirtualSize());

    // x and y default to current position
    if (x == -1) x = GetScrollPos(wxHORIZONTAL);
    if (y == -1) y = GetScrollPos(wxVERTICAL);

    DEBUG(cout << "Setting scrollbars to (" << x << ", " << y << ")" << endl);
    SetScrollbar(wxHORIZONTAL, x, r.width,  virtualRect.width);
    SetScrollbar(wxVERTICAL,   y, r.height, virtualRect.height);
}

#ifdef __WXMSW__

inline ostream& operator<< (ostream& o, const RECT& r)
{
    o << "RECT(" << r.left << ", " << r.top << ", " << r.right << ", " << r.bottom << ")";
    return o;
}

void SkinScrollWindow::ScrollWindow(int dx, int dy, const wxRect* prect)
{
    if ( !smoothScroll )
    {
        return wxWindow::ScrollWindow(dx, dy, prect);
    }

    RECT *pr;
    pr = NULL;
    DEBUG(cout << "ScrollWindowEx " << dx << " " << dy << " " << "NULL");



    int res = ::ScrollWindowEx(GetHwnd(), dx, dy, pr, pr, NULL, NULL,
        SW_INVALIDATE);
        // MAKELONG(SW_SMOOTHSCROLL, 100));
    ::UpdateWindow(GetHwnd());

    switch(res)
    {
    case SIMPLEREGION:
        DEBUG(cout << "  -> SIMPLEREGION" << endl);
        break;
    case COMPLEXREGION:
        DEBUG(cout << "  -> COMPLEXREGION" << endl);
        break;
    case NULLREGION:
        DEBUG(cout << "  -> NULLREGION" << endl);
        break;
    case ERROR:
        DEBUG(cout << "  -> ERROR: " << GetLastError() << endl);
        break;
    };

}
#endif

#define EIF(type, str) if ( t == type ) return wxString(wxT(str));

void SkinScrollWindow::OnScroll(wxScrollWinEvent& e)
{
    OnHandleScroll(e);
}

void SkinScrollWindow::OnHandleScroll(wxScrollWinEvent& e)
{
    DEBUG(cout << "OnHandleScroll " << GetEventTypeString(e.GetEventType()).mb_str() << endl);

    e.Skip();
    wxPoint lineSize(10, 10); // TODO: make accessor

    wxRect clientRect(GetClientRect());
    wxRect virtualRect(GetVirtualSize());
    wxEventType scrollType(e.GetEventType());
    int orientation = e.GetOrientation();
    bool h = orientation == wxHORIZONTAL;

    int x = GetScrollPos(wxHORIZONTAL),
        y = GetScrollPos(wxVERTICAL);

    wxPoint newPos(x, y);
    wxPoint pageSize(clientRect.width, clientRect.height);

    // THUMBTRACK: dragging the scroll thumb
    if ( scrollType == wxEVT_SCROLLWIN_THUMBTRACK ) {
        if (h) newPos.x = e.GetPosition();
        else   newPos.y = e.GetPosition();

    // THUMBRELEASE: mouse up on the thumb
    } else if ( scrollType == wxEVT_SCROLLWIN_THUMBRELEASE ) {
        if (h) newPos.x = e.GetPosition();
        else   newPos.y = e.GetPosition();

    // LINEDOWN: clicking the down arrow
    } else if ( scrollType == wxEVT_SCROLLWIN_LINEDOWN ) {
        if (h) newPos.x += lineSize.x;
        else   newPos.y += lineSize.y;

    // LINEUP: clicking the up arrow
    } else if ( scrollType == wxEVT_SCROLLWIN_LINEUP ) {
        if (h) newPos.x -= lineSize.x;
        else   newPos.y -= lineSize.y;

    // PAGEDOWN: clicking below the scroll thumb
    } else if ( scrollType == wxEVT_SCROLLWIN_PAGEDOWN ) {
        // self.RefreshRect() // why is this necessary?
        if (h) newPos.x += pageSize.x;
        else   newPos.y += pageSize.y;

    // PAGEUP: clicking above the scroll thumb
    } else if ( scrollType == wxEVT_SCROLLWIN_PAGEUP ) {
        // self.Refresh()
        if (h) newPos.x -= pageSize.x;
        else   newPos.y -= pageSize.y;
    }

    // keep scroll position within bounds
    int maxx = virtualRect.width - clientRect.width,
        maxy = virtualRect.height - clientRect.height;

    if (newPos.x < 0) newPos.x = 0;
    else if (newPos.x > maxx) newPos.x = maxx;

    if (newPos.y < 0) newPos.y = 0;
    else if (newPos.y > maxy) newPos.y = maxy;

    if ( physicalScrolling )
        SkinScrollWindow::ScrollWindow(-(newPos.x - x), -(newPos.y - y));
    else
        Refresh();

    // readjust scrollbars
    AdjustScrollbars(newPos.x, newPos.y);
}

void SkinScrollWindow::Scroll(int x, int y)
{
    DEBUG(cout << "SkinScrollWindow::Scroll(" << x << ", " << y << ")" << endl);

    int oldx = GetScrollPos(wxHORIZONTAL);
    int oldy = GetScrollPos(wxVERTICAL);

    wxPoint oldPos(oldx, oldy);

    // -1 for either argument means no change in that direction
    wxPoint newPos((x < 0 ? oldx : x), (y < 0 ? oldy : y));

    if ( newPos != oldPos ) {
        if ( physicalScrolling ) {
            wxPoint relative(oldPos - newPos);
            ScrollWindow(relative.x, relative.y);
        } else {
            Refresh();
        }

        // readjust scrollbars
        AdjustScrollbars(newPos.x, newPos.y);
    }

}

void SkinScrollWindow::OnMouseWheel(wxMouseEvent& event)
{
    int wheelRotation = 0;
    wheelRotation += event.GetWheelRotation();
    int lines = wheelRotation / event.GetWheelDelta();
    wheelRotation -= lines * event.GetWheelDelta();

    if (!lines)
        return;

    wxScrollWinEvent newEvent(0, 0, wxVERTICAL);
    newEvent.SetEventObject(this);

    if (event.IsPageScroll()) {
        newEvent.SetEventType(lines > 0 ? wxEVT_SCROLLWIN_PAGEUP : wxEVT_SCROLLWIN_PAGEDOWN);
        GetEventHandler()->ProcessEvent(newEvent);
    } else {
        lines *= event.GetLinesPerAction();
        newEvent.SetEventType(lines > 0 ? wxEVT_SCROLLWIN_LINEUP : wxEVT_SCROLLWIN_LINEDOWN);

        for (int times = abs(lines); times > 0; --times)
            GetEventHandler()->ProcessEvent(newEvent);
    }
}

void SkinScrollWindow::EnablePhysicalScrolling(bool enable)
{
    physicalScrolling = enable;
}

void SkinScrollWindow::PrepareDC(wxDC& dc)
{
    wxPoint pt(dc.GetDeviceOrigin());
    int x = GetScrollPos(wxHORIZONTAL),
        y = GetScrollPos(wxVERTICAL);

    dc.SetDeviceOrigin(pt.x - x, pt.y - y);
}

// override SetVirtualSize so we can AdjustScrollbars
void SkinScrollWindow::SetVirtualSize(int width, int height)
{
    wxWindow::SetVirtualSize(width, height);
    AdjustScrollbars();
    Refresh();
}

void SkinScrollWindow::SetVirtualSize(const wxSize& size)
{
    SetVirtualSize(size.x, size.y);
}

void SkinScrollWindow::OnSize(wxSizeEvent& event)
{
    event.Skip();
    AdjustScrollbars();
}

int SkinScrollWindow::GetViewStart() const
{
    return GetScrollPos(wxVERTICAL);
}

wxRect SkinScrollWindow::GetViewRect() const
{
    int y = GetViewStart();
    wxRect rect(GetClientRect());
    rect.Offset(0, y);

    return rect;
}
