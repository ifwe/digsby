#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wx/wx.h>

#include "WindowSnapper.h"
#include "cwindowfx.h"

static bool GetMonitorClientArea(HWND hwnd, RECT* rect)
{
    HMONITOR hMonitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);

    MONITORINFO mInfo = { sizeof(MONITORINFO), 0, 0, 0 };

    if (!GetMonitorInfo(hMonitor, &mInfo))
        return false;

    *rect = mInfo.rcWork;
    return true;
}

// returns the client area of the monitor that the specified window is on.
wxRect GetMonitorClientArea(wxWindow* win)
{
    RECT rcWork;
    if (!GetMonitorClientArea(static_cast<HWND>(win->GetHWND()), &rcWork))
        return wxRect();

    return wxRect(rcWork.left, rcWork.top,
                  rcWork.right - rcWork.left,
                  rcWork.bottom - rcWork.top);
}

// in charge of platform specific setup
void WindowSnapper::PlatformSetEnabled(bool enable)
{
    if (!binder)
        if (!enable)
            return;
        else
            binder = PlatformMessageBinder::ForWindow(win);

    if (enable) {
        binder->BindNative(WM_DESTROY, this);
        binder->BindNative(WM_MOVING, this);
        binder->BindNative(WM_SIZING, this);
        binder->BindNative(WM_ENTERSIZEMOVE, this);
    } else {
        binder->UnbindNative(WM_DESTROY, this);
        binder->UnbindNative(WM_MOVING, this);
        binder->UnbindNative(WM_SIZING, this);
        binder->UnbindNative(WM_ENTERSIZEMOVE, this);
    }
}

static bool aeroSnapped(HWND hwnd)
{
    // No Windows 7, no Aero Snap.
    if (!isWin7OrHigher())
        return false;

    // Win7's "Aero Snap" feature sends WM_ENTERSIZEMOVE while maximized--
    // don't snap to that position.
    if (::IsZoomed(hwnd))
        return true;

    // Otherwise we might be snapped to the edge of a monitor.
    RECT rect, monitor;
    if (::GetWindowRect(hwnd, &rect) && GetMonitorClientArea(hwnd, &monitor)) {
        if (rect.top == monitor.top &&
            rect.bottom == monitor.bottom)
            return true;
    }

    return false;
}

// responds to Win32 messages, calling HandleMoveStart and HandleMoveOrSize as necessary
LRESULT WindowSnapper::handleMessage(HWND hwnd, UINT message, WPARAM /* wParam */, LPARAM lParam)
{
    switch (message) {
    case WM_ENTERSIZEMOVE:
        if (m_docked || !aeroSnapped(hwnd))
            HandleMoveStart();
        else
            capturePositionOnNextMove = true;
        break;
    case WM_SIZING:
    case WM_MOVING: {
        RECT* r = (LPRECT)lParam;
        wxRect rect(r->left, r->top, r->right - r->left, r->bottom - r->top);

        // allow HandleMoveOrSize to modify the rectangle
        HandleMoveOrSize(rect, message == WM_SIZING ? Sizing : Moving);

        // now copy the necessary values back into the RECT at lParam
        r->left = rect.x;
        r->top = rect.y;

        if (message == WM_MOVING) {
            // when moving the window, always maintain the same size
            if (cs.x > 0 || cs.y > 0) {
                r->right = rect.x + cs.x;
                r->bottom = rect.y + cs.y;
            }
        } else {
            // when sizing the window, use the new size given in rect
            r->right = rect.GetRight() + 1;
            r->bottom = rect.GetBottom() + 1;
        }
        break;
        }
    case WM_DESTROY:
        OnWindowDestroyed();
        break;
    }

    return 0;
}

