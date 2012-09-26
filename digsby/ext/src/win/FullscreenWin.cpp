
#include <windows.h>
#include <wx/dynlib.h>

/* SHQueryUserNotificationState() return values */
#if (WINVER < 0x0600) 
// windows.h on less than vista doesn't have QUERY_USER_NOTIFICATION_STATE
typedef enum {
    QUNS_NOT_PRESENT                = 1,
    QUNS_BUSY                       = 2,
    QUNS_RUNNING_D3D_FULL_SCREEN    = 3,
    QUNS_PRESENTATION_MODE          = 4,
    QUNS_ACCEPTS_NOTIFICATIONS      = 5
} QUERY_USER_NOTIFICATION_STATE;
#endif

typedef HRESULT (WINAPI *qunFunc)(QUERY_USER_NOTIFICATION_STATE*);

class wxOnceOnlyDLLLoader
{
public:
    // ctor argument must be a literal string as we don't make a copy of it!
    wxOnceOnlyDLLLoader(const wxChar *dllName)
        : m_dllName(dllName)
    {}

    // return the symbol with the given name or NULL if the DLL not loaded
    // or symbol not present
    void *GetSymbol(const wxChar *name) {
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

private:
    wxDynamicLibrary m_dll;
    const wxChar *m_dllName;
};

static wxOnceOnlyDLLLoader wxSHELL32DLL(_T("shell32"));


// returns the HWND of any foreground app taking the full area of the primary
// monitor
long FullscreenAppHWND()
{
    HWND fg = GetForegroundWindow();

    // GetForegroundWindow can return 0
    if (!fg)
        return 0;

    HWND desktop = GetDesktopWindow();
    HWND shell = GetShellWindow();

    // the desktop or shell windows cannot be fullscreen
    if (fg == desktop || fg == shell) {
        return 0;
    }

    RECT rect;
    if (!GetClientRect(fg, &rect)) {
        return 0;
    }

    // match the window's client size with the size of the primary monitor.
    if ((rect.right - rect.left == GetSystemMetrics(SM_CXSCREEN)) &&
        (rect.bottom - rect.top == GetSystemMetrics(SM_CYSCREEN))) {

        // the size matches--make sure that it's the primary monitor
        HMONITOR hMonitor = MonitorFromWindow(fg, MONITOR_DEFAULTTONULL);
        if (hMonitor) {
            MONITORINFO mInfo = { sizeof(MONITORINFO) };
            if (GetMonitorInfo(hMonitor, &mInfo))
                if (mInfo.dwFlags & MONITORINFOF_PRIMARY)
                    return (long)fg;
        }
    }

    return 0;
}

// returns true if the foreground application is taking the entire screen
bool FullscreenApp()
{
    // SHQueryUserNotificationState is Vista only
    static qunFunc qun = (qunFunc)wxSHELL32DLL.GetSymbol(wxT("SHQueryUserNotificationState"));
    if (qun) {
        QUERY_USER_NOTIFICATION_STATE state;
        if (qun(&state) == S_OK)
            return state == QUNS_NOT_PRESENT ||
                   state == QUNS_BUSY ||
                   state == QUNS_RUNNING_D3D_FULL_SCREEN ||
                   state == QUNS_PRESENTATION_MODE;
    }

    return FullscreenAppHWND() != 0;
}

