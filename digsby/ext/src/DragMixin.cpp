#include <wx/window.h>

#include "cwindowfx.h"
#include "DragMixin.h"

BEGIN_EVENT_TABLE(DragMixin, wxEvtHandler)
    EVT_LEFT_DOWN(DragMixin::OnLeftDown)
    EVT_LEFT_UP(DragMixin::OnLeftUp)
    EVT_MOTION(DragMixin::OnMotion)
    EVT_MOUSE_CAPTURE_LOST(DragMixin::OnCaptureLost)
END_EVENT_TABLE()

DragMixin::DragMixin(wxWindow* window)
    : win(window)
{
}

DragMixin::~DragMixin()
{
    win = 0;
}

void DragMixin::OnLeftDown(wxMouseEvent& e)
{
    e.Skip();
    if (!win->HasCapture())
        win->CaptureMouse();

    // track where the mouse is when you left click
    origin = FindTopLevelWindow(win)->GetScreenPosition() - wxGetMousePosition();
}

void DragMixin::OnLeftUp(wxMouseEvent& e)
{
    e.Skip();
    while (win->HasCapture())
        win->ReleaseMouse();
}

void DragMixin::OnMotion(wxMouseEvent& e)
{
    e.Skip();
    if (win->HasCapture())
        FindTopLevelWindow(win)->Move(origin + win->ClientToScreen(e.GetPosition()));
}

void DragMixin::OnCaptureLost(wxMouseCaptureLostEvent&)
{
    // do nothing
}
