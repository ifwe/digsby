#include "WinUtils.h"

#include <wx/window.h>
#include <windows.h>

DLLLoader::DLLLoader(const wxChar *dllName)
    : m_dllName(dllName)
{}

// return the symbol with the given name or NULL if the DLL not loaded
// or symbol not present
void *DLLLoader::GetSymbol(const wxChar *name)
{
    // we're prepared to handle errors here
    wxLogNull noLog;

    if (m_dllName) {
        m_dll.Load(m_dllName);

        // reset the name whether we succeeded or failed so that we don't
        // try again the next time
        m_dllName = NULL;
    }

    return m_dll.IsLoaded() ? m_dll.GetSymbol(name) : NULL;
}

// vista only desktop window manager API
static DLLLoader wxDWMAPI(wxT("dwmapi"));

typedef struct _MARGINS {
    int cxLeftWidth;
    int cxRightWidth;
    int cyTopHeight;
    int cyBottomHeight;
} MARGINS, *PMARGINS;

typedef HRESULT (CALLBACK *DwmIsCompositionEnabled_t)(BOOL *);
typedef HRESULT (CALLBACK *DwmExtendFrameIntoClientArea_t)(HWND, PMARGINS);

bool isGlassEnabled()
{
    static DwmIsCompositionEnabled_t
        pfnDwmIsCompositionEnabled = (DwmIsCompositionEnabled_t)wxDWMAPI.GetSymbol(wxT("DwmIsCompositionEnabled"));

    if (pfnDwmIsCompositionEnabled) {
        BOOL enabled;
        HRESULT hr = pfnDwmIsCompositionEnabled(&enabled);
        if (FAILED(hr))
            wxLogApiError(wxT("DwmIsCompositionEnabled"), hr);
        else
            return enabled == TRUE;
    }

    return false;
}

bool glassExtendInto(wxWindow* win, int left, int right, int top, int bottom)
{
    static DwmExtendFrameIntoClientArea_t
        pfnDwmExtendFrameIntoClientArea = (DwmExtendFrameIntoClientArea_t)wxDWMAPI.GetSymbol(wxT("DwmExtendFrameIntoClientArea"));

    if (pfnDwmExtendFrameIntoClientArea) {
        MARGINS margins = {left, right, top, bottom};
        HWND hwnd = (HWND)win->GetHWND();
        HRESULT hr = pfnDwmExtendFrameIntoClientArea(hwnd, &margins);
        if (FAILED(hr))
            wxLogApiError(wxT("DwmExtendFrameIntoClientArea"), hr);
        else
            return true;
    }

    return false;
}


typedef struct tagTHREADNAME_INFO
{
   DWORD dwType; // must be 0x1000
   LPCSTR szName; // pointer to name (in user addr space)
   DWORD dwThreadID; // thread ID (-1=caller thread)
   DWORD dwFlags; // reserved for future use, must be zero
} THREADNAME_INFO;

//
// sets the thread name; visible in the debugger. if dwThreadId is 0,
// sets the current thread name
//
void setThreadName(unsigned long dwThreadID, const wxString& threadName)
{
    if (dwThreadID == 0)
        dwThreadID = ::GetCurrentThreadId();

    THREADNAME_INFO info;
    info.dwType = 0x1000;
    wxCharBuffer buf(threadName.ToAscii());
    info.szName = buf.data();
    info.dwThreadID = dwThreadID;
    info.dwFlags = 0;

    // secret MSDN voodoo to set thread names: 
    //   http://msdn.microsoft.com/en-us/library/xcb2z8hs(vs.71).aspx
    __try {
       ::RaiseException(0x406D1388, 0, sizeof(info)/sizeof(DWORD), (DWORD*)&info );
    }
    __except(EXCEPTION_CONTINUE_EXECUTION)
    {
    }
}

// clears the windows console
void cls()
{
    HANDLE hConsole;
    if (!(hConsole = GetStdHandle(STD_OUTPUT_HANDLE)))
        return;

    CONSOLE_SCREEN_BUFFER_INFO csbi;
    if (!GetConsoleScreenBufferInfo(hConsole, &csbi))
        return;

    COORD coordScreen = {0, 0};
    DWORD dwConSize = csbi.dwSize.X * csbi.dwSize.Y;
    DWORD cCharsWritten;
    FillConsoleOutputCharacter(hConsole, (TCHAR) ' ', dwConSize, coordScreen, &cCharsWritten);
    GetConsoleScreenBufferInfo(hConsole, &csbi);
    FillConsoleOutputAttribute(hConsole, csbi.wAttributes, dwConSize, coordScreen, &cCharsWritten);
    SetConsoleCursorPosition(hConsole, coordScreen);
}
