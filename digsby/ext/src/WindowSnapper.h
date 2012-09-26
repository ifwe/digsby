#ifndef _WINDOWSNAPPER_H__
#define _WINDOWSNAPPER_H__

#include "PlatformMessages.h"
#include <wx/gdicmn.h>
#include <vector>
using std::vector;

enum WindowOp
{
    Moving,
    Sizing
};

enum RectArea
{
    Inside,
    Outside
};

struct SnapRect
{
    SnapRect(RectArea a, const wxRect& r)
        : area(a)
        , rect(r)
    {}

    RectArea area;
    wxRect rect;
};

// must be implemented by the platform
wxRect GetMonitorClientArea(wxWindow* win);

/**
 * Provides a "snapping" behavior when dragging a window.
 *
 * The window will stick to other windows in this application, and to the edges of the screen.
 */
#ifdef __WXMSW__
class WindowSnapper : public NativeMsgHandler
#else
class WindowSnapper
#endif
{
public:
    WindowSnapper(wxWindow* win, int snapMargin = 12, bool enable = true);
    virtual ~WindowSnapper();

    bool SetEnabled(bool enable);
    bool IsEnabled() const { return enabled; }

    int GetSnapMargin() const { return snap_margin; }
    void SetSnapMargin(int snapMargin) { snap_margin = snapMargin; }

    bool GetSnapToScreen() const { return snap_to_screen; }
    void SetSnapToScreen(bool snapToScreen) { snap_to_screen = snapToScreen; }

    void SetDocked(bool docked) { m_docked = docked; }

    vector<SnapRect> WindowSnapper::GetSnapRects() const;

protected: // these methods must be implemented by the platform:
#if __WXMSW__
    virtual LRESULT handleMessage(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam);
#endif
    void PlatformSetEnabled(bool enable);

protected: 

    void HandleMoveOrSize(wxRect& rect, WindowOp op);
    void HandleMoveStart();
    void CapturePosition();
    
    void OnWindowDestroyed();

    void Init(wxWindow* win, int snapMargin, bool enable);

    int snap_margin;
    bool enabled;
    bool snap_to_screen;
    bool m_docked;

    wxWindow* win;
    PlatformMessageBinder* binder;

    int cx;
    int cy;
    wxSize cs;
    bool capturePositionOnNextMove;
};


#endif // _WINDOWSNAPPER_H__
