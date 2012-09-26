//
// alphaborder_win.cpp
//

#include <wx/dcmemory.h>
#include <wx/msw/private.h>

#include <windows.h>

#ifndef WS_EX_LAYERED
#define WS_EX_LAYERED 0x80000
#endif

#ifndef ULW_ALPHA
#define ULW_ALPHA 0x00000002
#endif

typedef BOOL (WINAPI *lpfnUpdateLayeredWindow)(HWND, HDC, POINT *, SIZE *, HDC, POINT *, COLORREF, BLENDFUNCTION *, DWORD);

#include "alphaborder_win.h"

bool SetLayered(HWND hwnd, bool layered)
{
    LONG style = GetWindowLong(hwnd, GWL_EXSTYLE);
    bool oldLayered = (WS_EX_LAYERED & style) != 0;

    if (layered == oldLayered)
        return false;

    if (layered)
        style |= WS_EX_LAYERED;
    else
        style &= ~WS_EX_LAYERED;

    return SetWindowLong(hwnd, GWL_EXSTYLE, style) != 0;
}

bool SetLayered(wxWindow* window, bool layered)
{
    return SetLayered((HWND)window->GetHWND(), layered);
}

bool ApplyAlpha(wxWindow* window, wxBitmap& bitmap, unsigned char alpha /* = 255*/)
{
    static lpfnUpdateLayeredWindow UpdateLayeredWindow = 0;
    if (UpdateLayeredWindow == 0)
    {
        HMODULE hUser32 = GetModuleHandle(_T("USER32.DLL"));
        UpdateLayeredWindow = (lpfnUpdateLayeredWindow)GetProcAddress(hUser32, "UpdateLayeredWindow");
    }

    SetLayered(window, true);

    wxRect r(window->GetRect());

    POINT pos = {r.x, r.y};
    SIZE size = {r.width, r.height};
    POINT imgpos = {0, 0};

    BLENDFUNCTION blendFunc;
    blendFunc.BlendOp = AC_SRC_OVER;
    blendFunc.BlendFlags = 0;
    blendFunc.SourceConstantAlpha = alpha;
    blendFunc.AlphaFormat = AC_SRC_ALPHA;

    MemoryHDC dcSrc;
    SelectInHDC selectInDC(dcSrc, bitmap.GetHBITMAP());

    if (!UpdateLayeredWindow((HWND)window->GetHWND(),
                             ScreenHDC(),
                             &pos,
                             &size,
                             dcSrc,
                             &imgpos,
                             0,
                             &blendFunc,
                             ULW_ALPHA))
    {
        wxLogApiError(wxT("UpdateLayeredWindow failed"), ::GetLastError());
        return false;
    }

    return true;
}

#ifndef NDEBUG
DbgGuiLeak::DbgGuiLeak(const char* funcname, const char* file, int line)
    : _funcname(funcname)
    , _file(file)
    , _line(line)
{
    _guiResCount = ::GetGuiResources (::GetCurrentProcess(), GR_GDIOBJECTS);
}

DbgGuiLeak::~DbgGuiLeak()
{
    int leaks = ::GetGuiResources (::GetCurrentProcess(), GR_GDIOBJECTS) - _guiResCount;
    if (leaks != 0)
        fprintf(stderr, "GDI leak %d object in %s (%s:%d)\n", leaks, _funcname, _file, _line);
}
#endif

