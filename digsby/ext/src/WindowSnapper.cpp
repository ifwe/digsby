#include "WindowSnapper.h"

#if 0
#define DBG(x) x
#else
#define DBG(x)
#endif

WindowSnapper::WindowSnapper(wxWindow* win, int snapMargin, bool enable)
{
    DBG(fprintf(stderr, "WindowSnapper(%p, snapMargin = %d, enable = %d)\n", win, snapMargin, enable));
    Init(win, snapMargin, enable);
}

WindowSnapper::~WindowSnapper()
{
    DBG(fprintf(stderr, "~WindowSnapper(%p)\n", this));
    wxASSERT_MSG(wxIsMainThread(), wxT("WindowSnapper must be destroyed on the main thread"));

    if (win) {
        SetEnabled(false);
        win = 0;
    }
}

void WindowSnapper::Init(wxWindow* win, int snapMargin, bool enable)
{
    snap_margin = snapMargin;

    this->win = win;
    this->binder = 0;
    this->snap_to_screen = true;
    m_docked = false;

    cx = cy = 0;
    cs = wxSize(0, 0);

    capturePositionOnNextMove = false;

    SetEnabled(enable);
}

// catches EVT_DESTROY and unbinds from window messages
void WindowSnapper::OnWindowDestroyed()
{
    DBG(fprintf(stderr, "WindowSnapper::OnWindowDestroyed(this=%p, win=%p, GetWindow()=%p)\n", this, win));
    SetEnabled(false);
    win = 0;

    delete this;
}

bool WindowSnapper::SetEnabled(bool enable)
{
    if (enabled == enable)
        return false;

    enabled = enable;
    PlatformSetEnabled(enable);
    return true;
}

static inline bool insideIntervalX(const wxRect& rect, const wxRect& bound)
{
    return (rect.x >= bound.x && rect.x < bound.GetRight())
        || (bound.x >= rect.x && bound.x < rect.GetRight());
}

static inline bool insideIntervalY(const wxRect& rect, const wxRect& bound)
{
    return (rect.y >= bound.y && rect.y < bound.GetBottom())
        || (bound.y >= rect.y && bound.y < rect.GetBottom());
}

void WindowSnapper::HandleMoveOrSize(wxRect& rect, WindowOp op)
{
    DBG(fprintf(stderr, "HandleMoveOrSize (%d, %d, %d, %d) %s\n", rect.x, rect.y, rect.width, rect.height, op == Sizing ? "Sizing" : "Moving"));

    vector<SnapRect> snap_rects = GetSnapRects();
    int margin = snap_margin;

#define isClose(a, b) (abs((a) - (b)) < margin)

    if (capturePositionOnNextMove) {
        capturePositionOnNextMove = false;
        CapturePosition();
    }

    if (op == Moving) {
        wxPoint mouse(wxGetMousePosition());
        rect.Offset(mouse.x - (rect.x + cx), mouse.y - (rect.y + cy));
    }
    
    // shift ignores snapping behavior
    if (wxGetKeyState(WXK_SHIFT))
        return;

    // Loop through all the possible rectangles we could snap to, and determine
    // if we should modify rect's position.
    for (size_t i = 0; i < snap_rects.size(); ++i) {
        SnapRect snap_rect = snap_rects[i];
        wxRect bound = snap_rect.rect;

        if (snap_rect.area == Inside) {
            if (isClose(rect.x, bound.x)) {
                int right = rect.GetRight();
                rect.x = bound.x;
                if (op == Sizing) rect.SetRight(right);
            }
            else if (isClose(bound.GetRight(), rect.GetRight() + 1)) {
                if (op == Sizing)
                    rect.width += bound.GetRight() - rect.GetRight();
                else
                    rect.x = bound.GetRight() - rect.width + 1;
            }

            if (isClose(rect.y, bound.y)) {
                int bottom = rect.GetBottom();
                rect.y = bound.y;
                if (op == Sizing) rect.SetBottom(bottom);
            } else if (isClose(bound.GetBottom(), rect.GetBottom() + 1)) {
                if (op == Sizing)
                    rect.height += bound.GetBottom() - rect.GetBottom();
                else
                    rect.y = bound.GetBottom() - rect.height + 1;
            }
        } else { // snap_rect.area == Outside
            if (insideIntervalY(rect, bound)) {
                if (isClose(rect.x, bound.GetRight() + 1)) {
                    int right = rect.GetRight();
                    rect.x = bound.GetRight() + 1;
                    if (op == Sizing) rect.SetRight(right);
                } else if (isClose(bound.x - 1, rect.GetRight())) {
                    if (op == Sizing)
                        rect.width += bound.x - 1 - rect.GetRight();
                    else
                        rect.x += bound.x - 1 - rect.GetRight();
                }
            }
            if (insideIntervalX(rect, bound)) {
                if (isClose(rect.y, bound.GetBottom() + 1)) {
                    int bottom = rect.GetBottom();
                    rect.y =  bound.GetBottom() + 1;
                    if (op == Sizing) rect.SetBottom(bottom);
                } else if (isClose(bound.y - 1, rect.GetBottom())) {
                    if (op == Sizing)
                        rect.height += bound.y - 1 - rect.GetBottom();
                    else
                        rect.y += bound.y - 1 - rect.GetBottom();
                }
            }
        }
    }
}

void WindowSnapper::CapturePosition()
{
    wxRect window(win->GetRect());
    wxPoint mouse(wxGetMousePosition());

    cx = mouse.x - window.x;
    cy = mouse.y - window.y;
}

// when starting a move, marks the initial position at (cx, cy) and the size at cs
void WindowSnapper::HandleMoveStart()
{
    DBG(fprintf(stderr, "HandleMoveStart()\n"));

    CapturePosition();
    cs = win->GetRect().GetSize();
}

// returns the rectangles that our window will snap to
vector<SnapRect> WindowSnapper::GetSnapRects() const
{
    vector<SnapRect> rects;

    // if snap_to_screen is true, then include the rectangle of the monitor
    // the window is on.
    if (snap_to_screen)
        rects.push_back(SnapRect(Inside, GetMonitorClientArea(win)));

    // append a rect for each top level window
    for ( wxWindowList::const_iterator i = wxTopLevelWindows.begin(),
                                     end = wxTopLevelWindows.end();
          i != end;
          ++i )
    {
        wxTopLevelWindow * const tlw = wx_static_cast(wxTopLevelWindow *, *i);
        if (win != tlw && tlw->IsShown() && !(tlw->GetWindowStyle() & wxFRAME_SHAPED))
            rects.push_back(SnapRect(Outside, tlw->GetRect()));
    }

    return rects;
}

