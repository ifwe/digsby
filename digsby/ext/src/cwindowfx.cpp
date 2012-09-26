//
// cwindowfx.cpp
//

#include "cwindowfx.h"
#include "Python.h"
#include <math.h>

#include <wx/dynlib.h>
#include <wx/event.h>
#include <wx/display.h>
#include <wx/bitmap.h>
#include <wx/image.h>
#include <wx/icon.h>
#include <wx/rawbmp.h>

//2.8, in 2.9 this is a redirect to "wx/crt.h"
#include <wx/wxchar.h>

#define HAS_SHOW_NOACTIVATE 0

#ifdef __WXMSW__

#include <windows.h>
#include <shellapi.h>

// Visual Studio 2008: SetLayeredWindowAttributes is in windows.h
#if (_MSC_VER < 1500)
typedef DWORD (WINAPI *PSLWA)(HWND, DWORD, BYTE, DWORD);
static PSLWA SetLayeredWindowAttributes = NULL;
static bool slwa_initialized = false;
#endif
#endif // __WXMSW__

void redirectStderr(const wxString& filename) {
    wxFreopen(filename, L"w", stderr);
}

void printToStderr(const wxString& s)
{
    fprintf(stderr, "%ws", s.wc_str());
}

bool checkWindows(DWORD major, DWORD minor)
{
    bool isMatch = false;

#if __WXMSW__
    DWORD dwVersion = GetVersion();
    DWORD dwMajorVersion = (DWORD)(LOBYTE(LOWORD(dwVersion)));
    DWORD dwMinorVersion = (DWORD)(HIBYTE(LOWORD(dwVersion)));

    isMatch = dwMajorVersion > major || (dwMajorVersion == major && dwMinorVersion >= minor); 
#endif // __WXMSW__

    return isMatch;
}

bool isWin7OrHigher() { return checkWindows(6, 1); }
bool isVistaOrHigher() { return checkWindows(6, 0); }

#include <stdio.h>
#include <assert.h>
#include "ctextutil.h"
#include "pyutils.h"


using namespace std;

#define WS_EX_LAYERED 0x00080000

bool IsMainThread()
{
    return wxIsMainThread();
}

wxIconBundle createIconBundle(const wxBitmap& bitmap)
{
    return createIconBundle(bitmap.ConvertToImage());
}

wxIconBundle createIconBundle(const wxImage& image)
{
    // TODO: platforms where IconBundles might need other sizes?
    //       i.e., Mac 256px PNGs?

    // get system sizes
#ifdef __WXMAC__
    // Unfortunately Mac doesn't give proper values for the icon constants,
    // and PIL throwing MemoryErrors isn't fun, so just go back to the hardcoded
    // variants here.
    wxSize big(32, 32);
    wxSize sm(16, 16);
#else
    wxSize big(wxSystemSettings::GetMetric(wxSYS_ICON_X),
               wxSystemSettings::GetMetric(wxSYS_ICON_Y));

    wxSize sm(wxSystemSettings::GetMetric(wxSYS_SMALLICON_X),
              wxSystemSettings::GetMetric(wxSYS_SMALLICON_Y));
#endif

    // make bitmaps
    wxBitmap bigBitmap(image.Scale(big.x, big.y, wxIMAGE_QUALITY_HIGH));
    wxBitmap smallBitmap(image.Scale(sm.x, sm.y, wxIMAGE_QUALITY_HIGH));

    // make icons
    wxIcon bigIcon;
    wxIcon smallIcon;
    bigIcon.CopyFromBitmap(bigBitmap);
    smallIcon.CopyFromBitmap(smallBitmap);

    // add icons to bundles
    wxIconBundle bundle;
    bundle.AddIcon(bigIcon);
    bundle.AddIcon(smallIcon);
    return bundle;
}

void SetFrameIcon(wxTopLevelWindow* win, const wxImage& image)
{
    // set the frame icon
    win->SetIcons(createIconBundle(image));
}

wxFont ModifiedFont(const wxFont& font_, int weight, int pointSize, const wxString& faceName, int underline)
{
    wxFont font(font_);

    if (weight != -1)
        font.SetWeight(weight);
    if (pointSize != -1)
        font.SetPointSize(pointSize);
    if (faceName.length())
        font.SetFaceName(faceName);
    if (underline != -1)
        font.SetUnderlined(underline != 0);

    return font;
}

void ModifyFont(wxWindow* ctrl, int weight, int pointSize, const wxString& faceName, int underline)
{
    ctrl->SetFont(ModifiedFont(ctrl->GetFont(), weight, pointSize, faceName, underline));
}

void SetBold(wxWindow* window, bool bold /* = true */)
{
    wxFont f(window->GetFont());
    f.SetWeight(bold ? wxFONTWEIGHT_BOLD : wxFONTWEIGHT_NORMAL);
    window->SetFont(f);
}

wxRect RectClamp(const wxRect& self, const wxRect& r2, int flags /*= wxALL */)
{
    wxRect r(r2);

    if ((flags & (wxLEFT | wxRIGHT)) && r.width > self.width) {
        r.width = self.width;
        r.x = self.x;
    } else {
        if (wxLEFT & flags)
            r.x = max(self.x, r.x);

        if (wxRIGHT & flags) {
            int dx = r.GetRight() - self.GetRight();
            if (dx > 0)
                r.x -= dx;
        }
    }

    if ((flags & (wxTOP | wxBOTTOM)) && r.height > self.height) {
        r.height = self.height;
        r.y = self.y;
    } else {
        if (wxTOP & flags)
            r.y = max(self.y, r.y);

        if (wxBOTTOM & flags) {
            int dy = r.GetBottom() - self.GetBottom();
            if (dy > 0)
                r.y -= dy;
        }
    }

    return r;
}

// returns the number of the primary display (which can be given to wxDisplay)
unsigned int GetPrimaryDisplay()
{
    for (unsigned int i = 0; i < wxDisplay::GetCount(); ++i)
        if (wxDisplay(i).IsPrimary())
            return i;

    return 0;
}

// ensures that window is visible in a monitor
void FitInMonitors(wxWindow* window, const wxPoint& defaultPosition)
{
    int display = wxDisplay::GetFromWindow(window);
    wxRect windowRect(window->GetRect());

    // if the window isn't on any visible monitor, place it in the primary
    if (display == wxNOT_FOUND) {
        display = GetPrimaryDisplay();
        wxPoint rescuePoint(wxDisplay(display).GetClientArea().GetTopLeft());

        // offset by defaultPosition if given
        if (defaultPosition != wxDefaultPosition)
            rescuePoint += defaultPosition;
        windowRect.SetPosition(rescuePoint);
    }

    // brin window in from the edges of the screen so that it's entirely visible
    wxRect clientArea(wxDisplay(display).GetClientArea());
    if (!clientArea.Contains(windowRect))
        windowRect = RectClamp(clientArea, windowRect);

    // move the window
    window->SetSize(windowRect);
}

wxPoint RectClampPoint(const wxRect& self, const wxPoint& pt, int /*flags = wxALL */)
{
    wxRect rect(pt.x, pt.y, 0, 0);
    return RectClamp(self, rect).GetPosition();
}

void Bitmap_Draw(const wxBitmap& bitmap, wxDC& dc, const wxRect& rect, int alignment)
{
    wxRect r(0, 0, bitmap.GetWidth(), bitmap.GetHeight());

    if ( alignment & wxALIGN_CENTER_HORIZONTAL )
        r = r.CenterIn(rect, wxHORIZONTAL);
    else
        r.x = RectPosPoint(rect, wxPoint((wxALIGN_RIGHT & alignment) ? -bitmap.GetWidth() : 0, 0)).x;

    if ( alignment & wxALIGN_CENTER_VERTICAL )
        r = r.CenterIn(rect, wxVERTICAL);
    else
        r.y = RectPosPoint(rect, wxPoint(0, (wxALIGN_BOTTOM & alignment) ? -bitmap.GetHeight() : 0)).y;

    dc.DrawBitmap(bitmap, r.x, r.y, true);
}



int getCacheKey(wxBitmap* bitmap)
{
    return (int)bitmap->GetRefData()
#ifdef __WXMSW__
    + (int)bitmap->GetResourceHandle();
#endif
    ;
}

unsigned long djb2_hash(unsigned char *str)
{
    // dumb hash. thanks interwebs
    unsigned long hash = 5381;
    int c;

    c = *str++;
    while (c) {
        hash = ((hash << 5) + hash) + c;
        c = *str++;
    }

    return hash;
}

int getCacheKey(wxImage* image)
{
    // warning: evil
    static unsigned char buf[11];
    memcpy(buf, image->GetRefData(), 10);
    buf[10] = 0;

    return djb2_hash((unsigned char*)&buf);
}

NotifyWindow::NotifyWindow(wxWindow* window, int id, const wxString& title, long style)
    : wxFrame(window, id, title, wxDefaultPosition, wxDefaultSize, style)
{
}

NotifyWindow::~NotifyWindow()
{
}

#ifdef __WXMSW__

wxRect GetNormalRect(wxTopLevelWindow* win)
{
    wxRect rect;

    if (win) {
        WINDOWPLACEMENT p = { sizeof(WINDOWPLACEMENT) };
        HWND hwnd = (HWND)win->GetHWND();
        if (!GetWindowPlacement(hwnd, &p))
            wxLogApiError(_T("GetWindowPlacement"), ::GetLastError());
        else {
            wxCopyRECTToRect(p.rcNormalPosition, rect);
            
            // rcNormalPosition is in coordinates relative to the client area of
            // the monitor the window is on--convert this to virtual screen coordinates
            HMONITOR hmonitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
            if (!hmonitor)
                wxLogApiError(_T("MonitorFromWindow"), ::GetLastError());
            else {
                MONITORINFO minfo = {sizeof(MONITORINFO)};
                if (!GetMonitorInfo(hmonitor, &minfo))
                    wxLogApiError(_T("GetMonitorInfo"), ::GetLastError());
                else
                    rect.Offset(minfo.rcMonitor.left + (minfo.rcWork.left - minfo.rcMonitor.left),
                                minfo.rcMonitor.top  + (minfo.rcWork.top  - minfo.rcMonitor.top));
            }
        }
    }

    return rect;
}


#if (_MSC_VER < 1500)
typedef struct tagWCRANGE
{
    WCHAR  wcLow;
    USHORT cGlyphs;
} WCRANGE, *PWCRANGE,FAR *LPWCRANGE;

typedef struct tagGLYPHSET
{
    DWORD    cbThis;
    DWORD    flAccel;
    DWORD    cGlyphsSupported;
    DWORD    cRanges;
    WCRANGE  ranges[1];
} GLYPHSET, *PGLYPHSET, FAR *LPGLYPHSET;
#endif



static bool gs_gfur = false;
typedef DWORD (WINAPI *PSGFUR)(HDC, GLYPHSET*);
PSGFUR GetFontUnicodeRangesWin32 = 0;
#endif

PyObject* PyGetFontUnicodeRanges(const wxFont& font)
{
#ifdef __WXMSW__
    if (!gs_gfur) {
        HMODULE hDLL = LoadLibrary(L"gdi32");
        GetFontUnicodeRangesWin32 = (PSGFUR)GetProcAddress(hDLL, "GetFontUnicodeRanges");
        gs_gfur = true;
    }

    if (!GetFontUnicodeRangesWin32) {
        PyErr_SetString(PyExc_WindowsError, "Cannot get function pointer to GetFontUnicodeRanges");
        return 0;
    }

    GLYPHSET* glyphs = 0;
    DWORD count = 0;
    PyObject* ranges = 0;

    HDC hdc = GetDC(0);
    HFONT prevFont = (HFONT)SelectObject(hdc, (HFONT)font.GetHFONT());

    count = GetFontUnicodeRangesWin32(hdc, 0);

    if (!count) {
        PyErr_SetString(PyExc_WindowsError, "Unspecified error calling GetFontUnicodeRangesWin32");
        return 0;
    }

    glyphs = (GLYPHSET*)alloca(count);

    if (count != GetFontUnicodeRangesWin32(hdc, glyphs)) {
        PyErr_SetString(PyExc_WindowsError, "GetFontUnicodeRanges returned inconsistent values");
        Py_DECREF(ranges);
        return 0;
    }

    // initialize the python list we will return
    ranges = PyList_New(glyphs->cRanges);

    if (glyphs->flAccel)
        for (count = 0; count < glyphs->cRanges; ++count)
            PyList_SET_ITEM(ranges, count, Py_BuildValue("ll", glyphs->ranges[count].wcLow & 0xff, glyphs->ranges[count].cGlyphs));
    else
        for (count = 0; count < glyphs->cRanges; ++count)
            PyList_SET_ITEM(ranges, count, Py_BuildValue("ll", glyphs->ranges[count].wcLow, glyphs->ranges[count].cGlyphs));

    SelectObject(hdc, prevFont);
    ReleaseDC(0, hdc);
    return ranges;
#else
    return 0;
#endif
}

bool NotifyWindow::Show(bool show)
{
    if ( m_isShown == show )
        return false;
#ifdef __WXMSW__
    if ( show ) {
        HWND hwnd = (HWND)GetHWND();
        ShowWindow(hwnd, SW_SHOWNOACTIVATE);
        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOACTIVATE | SWP_NOSIZE | SWP_NOMOVE);
        m_isShown = true;
        return true;
    } else
#endif
    {
        return wxFrame::Show(false);
    }
}

void NotifyWindow::SetRect(const wxRect& rect)
{
#ifdef __WXMSW__
    int x = rect.GetX(),
        y = rect.GetY(),
        w = rect.GetWidth(),
        h = rect.GetHeight();

    SetWindowPos((HWND)GetHWND(), HWND_TOPMOST, x, y, w, h, SWP_NOACTIVATE);
#else
    SetRect(rect);
#endif
}





BEGIN_EVENT_TABLE(SimplePanel, wxPanel)
    EVT_ERASE_BACKGROUND(SimplePanel::OnEraseBackground)
END_EVENT_TABLE()

SimplePanel::SimplePanel(wxWindow* parent, int style)
    : wxPanel(parent, wxID_ANY, wxDefaultPosition, wxDefaultSize, style, wxT("Panel"))
{
    SetBackgroundStyle(wxBG_STYLE_CUSTOM);
}

SimplePanel::~SimplePanel() {}

void SimplePanel::OnEraseBackground(wxEraseEvent&)
{
    // do nothing.
}

void setalpha(wxTopLevelWindow* window, int alpha)
{
#ifdef __WXMSW__

#if (_MSC_VER < 1500)
    if (!slwa_initialized) {
        HMODULE hDLL = LoadLibrary(L"user32");
        SetLayeredWindowAttributes = (PSLWA)GetProcAddress(hDLL, "SetLayeredWindowAttributes");
        slwa_initialized = true;
    }
#endif

    HWND hwnd = (HWND)window->GetHWND();

    LONG_PTR style = GetWindowLongPtr(hwnd, GWL_EXSTYLE);
    LONG_PTR oldStyle = style;

    if (alpha == 255)
        style &= ~WS_EX_LAYERED;
     else
        style |=  WS_EX_LAYERED;

    if (alpha != 255 && SetLayeredWindowAttributes != NULL)
        SetLayeredWindowAttributes(hwnd, 0, alpha, 2);

    if (style != oldStyle)
        SetWindowLongPtr(hwnd, GWL_EXSTYLE, style);

    if (alpha > 0)
        window->Show(false);
#endif
}

Fader::Fader(wxTopLevelWindow* windowTarget, int fromAlpha, int toAlpha,
             unsigned int step,
             PyObject* onDone)
    : window(windowTarget)
    , to(toAlpha)
{

    //fprintf(stderr, "Fader<%p> created with window %p\n", this, window);

    PyGILState_STATE state = PyGILState_Ensure();
    Py_XINCREF(onDone);
    this->onDoneCallback = onDone;
    PyGILState_Release(state);

    // Listen for EVT_DESTROY from the window.
    windowTarget->Connect(-1, -1, wxEVT_DESTROY, wxWindowDestroyEventHandler(Fader::OnWindowDestroyed));

    this->step = step * (fromAlpha > toAlpha ? -1 : 1);
    const int tick = 8;

    value = fromAlpha;
    Start(tick, false);
}

void Fader::OnWindowDestroyed(wxWindowDestroyEvent& e)
{
    //fprintf(stderr, "Fader::OnWindowDestroyed(%p =? %p)...", e.GetEventObject(), window);

    if (window && e.GetEventObject() == window) {
        //fprintf(stderr, "stopping.\n");
        // window is destroying
        window = 0;
        Stop();
    }// else
        //fprintf(stderr, "ignore\n");

}

static bool inTopLevelWindowsList(wxTopLevelWindow* tlw)
{
    wxWindowList::compatibility_iterator node = wxTopLevelWindows.GetLast();
    while (node)
    {
        wxWindow* win = node->GetData();
        if (tlw == win)
            return true;
        node = node->GetPrevious();
    }

    return false;
}

void Fader::Notify()
{
    if (!IsRunning())
    {
        fprintf(stderr, "Fader::Notify() was called but !IsRunning()\n");
        return;
    }

    //fprintf(stderr, "Fader<%p>::Notify()\n", this);
    bool done = false;
    if (window) {
        if (!inTopLevelWindowsList(window)) {
            fprintf(stderr, "warning: fader window %p is not in TLW list\n", window);
            done = true;
        } else {
            value += step;

            if (step > 0) {
                if (value >= to) {
                    value = to;
                    done = true;
                }
            } else if (step < 0) {
                if (value <= to) {
                    value = to;
                    done = true;
                }
            } else
                done = true;

            window->SetTransparent(value);
        }
    } else
        done = true;

    if (done)
        Stop();
}

void Fader::Stop(bool runStopCallback /* = true */)
{
    //fprintf(stderr, "Fader<%p>::Stop()\n", this);
    bool isRunning = IsRunning();
    wxTimer::Stop();
    wxASSERT(!IsRunning());
    if (!isRunning)
        return;

    // notify the Python callback
    PyGILState_STATE state = PyGILState_Ensure();
    if (runStopCallback && onDoneCallback) {
        if ( PyCallable_Check( onDoneCallback ) ) {
            PyObject* result = PyObject_CallObject(onDoneCallback, NULL);
            if (!result && PyErr_Occurred()) {
                fprintf(stderr, "an error occurred\n");
                PyErr_Print();
            } else
                Py_DECREF(result);
        } else
            fprintf(stderr, "error: onDoneCallback was not callable\n");

        Py_CLEAR(onDoneCallback);
    }
    PyGILState_Release(state);
}

Fader::~Fader()
{
    //fprintf(stderr, "~Fader<%p>\n", this);
    window = 0;
    Stop();

    PyGILState_STATE state = PyGILState_Ensure();
    Py_CLEAR(onDoneCallback);
    PyGILState_Release(state);
}


Fader* fadein(wxTopLevelWindow* window, int fromAlpha, int toAlpha, unsigned int step, PyObject* onDone)
{
    window->SetTransparent(fromAlpha);
#if wxCHECK_VERSION(2, 9, 1)
    window->ShowWithoutActivating();
#elif defined(__WXMSW__) && HAS_SHOW_NOACTIVATE
    window->Show(true, false);
#else
    window->Show(true);
#endif

    return new Fader(window, fromAlpha, toAlpha, step, onDone);
}

/**
 * Returns the alpha transparency of a top level window, as an int from 0-255.
 */
int GetTransparent(wxTopLevelWindow* tlw)
{
#ifdef __WXMSW__
    HWND hwnd = (HWND)tlw->GetHWND();

    // without the WS_EX_LAYERED bit, the window cannot be transparent
    if ((GetWindowLongPtr(hwnd, GWL_EXSTYLE) & WS_EX_LAYERED) == 0)
        return 255;

    // grab GetLayeredWindowAttributes from user32.dll
    typedef BOOL (WINAPI *PGETLAYEREDWINDOWATTR)(HWND, COLORREF*, BYTE*, DWORD*);
    static PGETLAYEREDWINDOWATTR pGetLayeredWindowAttributes = 0;
    static bool getLayeredInit = false;

    if (!getLayeredInit) {
        getLayeredInit = true;
        wxDynamicLibrary dllUser32(_T("user32.dll"));
        pGetLayeredWindowAttributes = (PGETLAYEREDWINDOWATTR)
            dllUser32.GetSymbol(wxT("GetLayeredWindowAttributes"));
    }

    if (pGetLayeredWindowAttributes) {
        BYTE alpha;
        if (pGetLayeredWindowAttributes(hwnd, 0, &alpha, 0))
            return static_cast<int>(alpha);
    }
#endif
    return 255;
}

Fader* fadeout(wxTopLevelWindow* window, int fromAlpha, int toAlpha, unsigned int step, PyObject* onDone)
{
    // -1 means "the window's current opacity"
    if (fromAlpha == -1)
        fromAlpha = GetTransparent(window);

    return new Fader(window, fromAlpha, toAlpha, step, onDone);
}

#if defined(__WXMAC__) || defined(__WXGTK__)
wxRect GetTrayRect()
{
    return wxRect();
}

wxBitmap* getScreenBitmap(const wxRect& rect)
{
    return new wxBitmap(1,1);
}

bool WindowVisible(wxTopLevelWindow* win)
{
    return true;
}
#endif



#ifdef __WXMSW__

#define DEFAULT_RECT_WIDTH 150
#define DEFAULT_RECT_HEIGHT 30

static wxRect RectFromRECT(RECT r) {
    return wxRect(r.left, r.top, r.right - r.left, r.bottom - r.top);
}

bool GetTaskBarAutoHide()
{
    static APPBARDATA appbardata = { sizeof(APPBARDATA) };
    return (SHAppBarMessage(ABM_GETSTATE, &appbardata) & ABS_AUTOHIDE) != 0;
}

wxRect GetTaskbarRect()
{
    wxRect wxrect;
    RECT rect;

    HWND trayHwnd = ::FindWindowEx(0, 0, wxT("Shell_TrayWnd"), 0);
    if (trayHwnd && ::GetWindowRect(trayHwnd, &rect))
        wxrect = RectFromRECT(rect);

    return wxrect;
}

wxRect GetTrayRect()
{
    RECT rect;
    LPRECT lpTrayRect = &rect;

    // lookup by name
    HWND hShellTrayWnd = FindWindowEx(NULL, NULL, TEXT("Shell_TrayWnd"), NULL);
    if (hShellTrayWnd)
    {
        HWND hTrayNotifyWnd = FindWindowEx(hShellTrayWnd, NULL, TEXT("TrayNotifyWnd"), NULL);
        if(hTrayNotifyWnd && GetWindowRect(hTrayNotifyWnd, lpTrayRect))
            return RectFromRECT(rect);
    }

    // try the APPBARDATA api instead
    APPBARDATA appBarData;
    appBarData.cbSize = sizeof(appBarData);

    if (SHAppBarMessage(ABM_GETTASKBARPOS, &appBarData)) {

        // We know the edge the taskbar is connected to, so guess the rect of the
        // system tray. Use various fudge factor to make it look good
        switch(appBarData.uEdge)
        {
        case ABE_LEFT:
        case ABE_RIGHT:
            // We want to minimize to the bottom of the taskbar
            rect.top=appBarData.rc.bottom-100;
            rect.bottom=appBarData.rc.bottom-16;
            rect.left=appBarData.rc.left;
            rect.right=appBarData.rc.right;
            break;

        case ABE_TOP:
        case ABE_BOTTOM:
            // We want to minimize to the right of the taskbar
            rect.top=appBarData.rc.top;
            rect.bottom=appBarData.rc.bottom;
            rect.left=appBarData.rc.right-100;
            rect.right=appBarData.rc.right-16;
            break;
        }

        return RectFromRECT(rect);
    }

    hShellTrayWnd = FindWindowEx(NULL, NULL, TEXT("Shell_TrayWnd"), NULL);

    if (hShellTrayWnd && GetWindowRect(hShellTrayWnd, lpTrayRect)) {
        if(lpTrayRect->right-rect.left > DEFAULT_RECT_WIDTH)
            lpTrayRect->left=rect.right - DEFAULT_RECT_WIDTH;
        if(lpTrayRect->bottom-rect.top > DEFAULT_RECT_HEIGHT)
            lpTrayRect->top=rect.bottom - DEFAULT_RECT_HEIGHT;

        return RectFromRECT(rect);
    }

    // OK. Haven't found a thing. Provide a default rect based on the current work
    // area
    SystemParametersInfo(SPI_GETWORKAREA, 0, lpTrayRect, 0);
    lpTrayRect->left = lpTrayRect->right-DEFAULT_RECT_WIDTH;
    lpTrayRect->top  = lpTrayRect->bottom-DEFAULT_RECT_HEIGHT;
    return RectFromRECT(rect);
}

#include <wx/bitmap.h>

wxBitmap* getScreenBitmap(const wxRect& rect)
{
    wxBitmap* bmp = 0;

    HDC mainWinDC = GetDC(GetDesktopWindow());
    HDC memDC = CreateCompatibleDC(mainWinDC);

    HBITMAP bitmap = CreateCompatibleBitmap(mainWinDC, rect.width, rect.height);

    if (bitmap) {
        HGDIOBJ hOld = SelectObject(memDC,bitmap);
        BitBlt(memDC, 0, 0, rect.width, rect.height, mainWinDC, rect.x, rect.y, SRCCOPY);
        SelectObject(memDC, hOld);
        DeleteDC(memDC);
        ReleaseDC(GetDesktopWindow(), mainWinDC);
        bmp = new wxBitmap(rect.width, rect.height, 32);
        bmp->SetHBITMAP((WXHBITMAP)bitmap);
    }

    return bmp;
}

static bool win32ontop(HWND hwnd)
{
    return (GetWindowLongPtr(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST) != 0;
}

bool WindowVisible(wxTopLevelWindow* win)
{
    if (!win->IsShown() || win->IsIconized())
        return false;

    HWND winhandle = (HWND)win->GetHWND();
    bool winontop  = win32ontop(winhandle);
    wxRect winrect(win->GetPosition(), win->GetSize());
    RECT r;

    HWND hwnd = GetTopWindow(0);

    while (hwnd) {
        if (!GetWindowRect(hwnd, &r)) {
            fprintf(stderr, "GetWindowRect retuned error\n");
            break;
        }

        if (hwnd == winhandle)
            // if we're down to our window, return True--its visible
            return true;

        // check:
        //   1) that the window's "on top" state is the same as ours
        //   2) that the window is visible
        // if these are true and the window's rect intsects ours, return False
        if (win32ontop(hwnd) == winontop && IsWindowVisible(hwnd) && wxRect(r.left, r.top, r.right - r.left, r.bottom - r.top).Intersects(winrect))
            return false;

        hwnd = GetWindow(hwnd, GW_HWNDNEXT);
    }

    return true;
}

void ApplySmokeAndMirrors(wxWindow* win, const wxBitmap& shape, int ox /*= 0*/, int oy /*= 0*/)
{

    if (!shape.IsOk())
        PyErr_SetString(PyExc_AssertionError, "shape bitmap is not OK");
    else {
        wxBitmap regionBitmap = shape;

        // if the bitmap doesn't already have a mask, create one by clamping
        // the alpha values
        if (!shape.GetMask()) {
            wxImage img(shape.ConvertToImage());
            img.ConvertAlphaToMask(200);
            regionBitmap = wxBitmap(img);
        }

        wxRegion region(regionBitmap);
        if ((ox || oy) && !region.Offset(ox, oy)) {
            PyErr_SetString(PyExc_AssertionError, "could not offset region");
            return;
        }

        ApplySmokeAndMirrors(win, region);
    }
}

// shape is a wxRegion object
void ApplySmokeAndMirrors(wxWindow* win, const wxRegion& shape)
{
    ApplySmokeAndMirrors(win, (long)shape.GetHRGN());
}

// shape is just an HRGN (a handle to a windows region object)
void ApplySmokeAndMirrors(wxWindow* win, long shape /* = 0*/)
{
    if (shape) {
        HRGN hrgn = (HRGN)shape;

        // have to make a copy of the region
        DWORD numbytes = ::GetRegionData(hrgn, 0, NULL);
        if (!numbytes) {
            PyErr_SetFromWindowsErr(0);
            return;
        }

        RGNDATA *rgnData = (RGNDATA*) alloca(numbytes);
        ::GetRegionData(hrgn, numbytes, rgnData);
        shape = (long)::ExtCreateRegion(NULL, numbytes, rgnData);

        if (!shape) {
            PyErr_SetString(PyExc_AssertionError, "could not copy region");
            return;
        }
    }

    if (!::SetWindowRgn((HWND)win->GetHWND(), (HRGN)shape, true))
        PyErr_SetFromWindowsErr(0);
}

#endif // __WXMSW__

bool LeftDown()
{
    return wxGetMouseState().LeftDown();
}

// returns the topmost parent of the given window
wxWindow* FindTopLevelWindow(wxWindow* window)
{
    wxWindow* top = window;
    wxWindow* parent;

    while(top) {
        if (top->IsTopLevel())
            break;
        else {
            parent = top->GetParent();
            if (parent)
                top = parent;
            else
                break;
        }
    }
    
    return top;
}

#define wxPy_premultiply(p, a)   ((p) * (a) / 0xff)
#define wxPy_unpremultiply(p, a) ((a) ? ((p) * 0xff / (a)) : (p))    

void Premultiply(wxBitmap& bmp)
{
    int w = bmp.GetWidth();
    int h = bmp.GetHeight();
    wxAlphaPixelData pixData(bmp, wxPoint(0, 0), wxSize(w, h));

    wxAlphaPixelData::Iterator p(pixData);
    for (int y = 0; y < h; ++y) {
        wxAlphaPixelData::Iterator rowStart = p;
        for (int x = 0; x < w; ++x) {
            unsigned char a = p.Alpha();
            p.Red()   = wxPy_premultiply(p.Red(), a);
            p.Green() = wxPy_premultiply(p.Green(), a);
            p.Blue()  = wxPy_premultiply(p.Blue(), a);
            ++p;
        }

        p = rowStart;
        p.OffsetY(pixData, 1);
    }
}

void Unpremultiply(wxBitmap& bmp)
{
    int w = bmp.GetWidth();
    int h = bmp.GetHeight();
    wxAlphaPixelData pixData(bmp, wxPoint(0, 0), wxSize(w, h));

    wxAlphaPixelData::Iterator p(pixData);
    for (int y = 0; y < h; ++y) {
        wxAlphaPixelData::Iterator rowStart = p;
        for (int x = 0; x < w; ++x) {
            unsigned char a = p.Alpha();
            p.Red()   = wxPy_unpremultiply(p.Red(), a);
            p.Green() = wxPy_unpremultiply(p.Green(), a);
            p.Blue()  = wxPy_unpremultiply(p.Blue(), a);
            //p.Alpha() = a;
            ++p;
        }

        p = rowStart;
        p.OffsetY(pixData, 1);
    }
}

PyObject* RectPos(const wxRect& rect, const wxPoint& point)
{
    wxPoint p(RectPosPoint(rect, point));

    PyObject* tup = PyTuple_New(2);
    PyTuple_SET_ITEM(tup, 0, PyInt_FromLong(p.x));
    PyTuple_SET_ITEM(tup, 1, PyInt_FromLong(p.y));
    return tup;
}

/*
IMPLEMENT_DYNAMIC_CLASS(Animation, wxWindow)

BEGIN_EVENT_TABLE(Animation, wxWindow)
    EVT_PAINT(Animation::OnPaint)
END_EVENT_TABLE()


Animation::Animation()
{
    timer = new AnimationTimer(this);
}

Animation::Animation(wxWindow* parent, int id, const AnimationFrameVector& frames, bool repeating)
    : wxWindow(parent, id)
    , playing(true)
    , currentFrame(0)
{
    timer = new AnimationTimer(this);
    SetFrames(frames, repeating);
}

Animation::~Animation()
{
    timer->Stop();
    delete timer;
}

void Animation::SetFrames(const AnimationFrameVector& frames, bool repeating)
{
    wxASSERT(frames.size() > 0);
    this->frames = frames;
    repeating = repeating;
    CalcMinSize();
}



void Animation::OnPaint(wxPaintEvent& e)
{
    wxAutoBufferedPaintDC dc(this);

    if (repeating && !timer->IsRunning())
        timer->Start(GetFrameDuration(GetCurrentFrame()), true);

    // draw background
    dc.SetPen(*wxTRANSPARENT_PEN);
    dc.SetBrush(wxBrush(GetBackgroundColour()));
    dc.DrawRectangle(GetClientRect());

    // draw the bitmap
    dc.DrawBitmap(GetFrameBitmap(GetCurrentFrame()), 0, 0, true);
}

void Animation::OnTimer()
{
    NextFrame();
    Refresh();
}

void Animation::NextFrame()
{
    if (repeating) {
        currentFrame = (currentFrame + 1) % frames.size();
        timer->Start(GetFrameDuration(GetCurrentFrame()), true);
    } else {
        currentFrame += 1;
        if (currentFrame >= frames.size()) {
            timer->Stop();
            currentFrame = frames.size() - 1;
        } else
            timer->Start(GetFrameDuration(GetCurrentFrame()), true);
    }
}

void Animation::CalcMinSize()
{
    wxBitmap firstFrame = GetFrameBitmap(0);
    wxSize minSize(firstFrame.GetWidth(), firstFrame.GetHeight());

    for (size_t i = 1; i < frames.size(); ++i) {
        wxBitmap b = GetFrameBitmap(i);
        minSize.x = max(b.GetWidth(), minSize.x);
        minSize.y = max(b.GetHeight(), minSize.y);
    }

    SetMinSize(minSize);
    SetSize(minSize);
}

void AnimationTimer::Notify()
{
    if (animation)
        animation->OnTimer();
}
*/
