#include "WinTaskbar.h"

#ifdef WIN7_TASKBAR

#include <stdio.h>
#include <windows.h>
#include <dwmapi.h>

#include "WinUtils.h"
#include "cwindowfx.h"

static DLLLoader wxDWMAPI(wxT("dwmapi"));
static DLLLoader user32(wxT("user32"));

#define DWMWA_FORCE_ICONIC_REPRESENTAITON 7
#define DWMWA_HAS_ICONIC_BITMAP 10

#ifdef NDEBUG
#define DBG(x)
#else
#define DBG(x) x
#endif

void initializeTaskbar()
{
    static bool didInitializeTaskbar = false;
    if (didInitializeTaskbar)
        return;

    didInitializeTaskbar = true;

    typedef BOOL (WINAPI *ChangeWindowMessageFilter_t)(UINT message, DWORD dwFlag);
    static ChangeWindowMessageFilter_t pChangeWindowMessageFilter = (ChangeWindowMessageFilter_t)user32.GetSymbol(wxT("ChangeWindowMessageFilter"));
    if (pChangeWindowMessageFilter) {
        // Allow DWM messages to reach us even when running as administrator
        pChangeWindowMessageFilter(WM_DWMSENDICONICTHUMBNAIL, MSGFLT_ADD);
        pChangeWindowMessageFilter(WM_DWMSENDICONICLIVEPREVIEWBITMAP, MSGFLT_ADD);
    }
}

// load all dwmapi.dll functions lazily, so that cgui.pyd remains compatible
// with older versions of windows.
//
// TODO: let the linker do this for us with lazy DLL dependencies

typedef HRESULT (WINAPI *DwmSetIconicThumbnail_t)(HWND, HBITMAP, DWORD);
typedef HRESULT (WINAPI *DwmSetIconicLivePreviewBitmap_t)(HWND, HBITMAP, POINT*, DWORD);
typedef HRESULT (WINAPI *DwmSetWindowAttribute_t)(HWND, DWORD, LPCVOID, DWORD);
typedef HRESULT (WINAPI *DwmInvalidateIconicBitmaps_t)(HWND);

TabController::TabController()
{
    DBG(printf("TabController(%p)\n", this));
}

TabController::~TabController()
{
    DBG(printf("~TabController(%p)\n", this));
}

void* TabController::GetIconicHBITMAP(TaskbarWindow*, int, int)
{
    return 0;
}

wxBitmap TabController::GetIconicBitmap(TaskbarWindow* /*tab*/, int /*width*/, int /*height*/)
{
    return wxNullBitmap;
}

wxBitmap TabController::GetLivePreview(TabWindow* /*tab*/, const wxRect& /*clientSize*/)
{
    return wxNullBitmap;
}

wxIcon TabController::GetSmallIcon(TabWindow*)
{
    return wxNullIcon;
}

SimpleTabController::SimpleTabController()
{}

SimpleTabController::~SimpleTabController()
{}

void SimpleTabController::SetIconicBitmap(const wxBitmap& bitmap)
{
    m_bitmap = bitmap;
}

wxBitmap SimpleTabController::GetIconicBitmap(TaskbarWindow* /*window*/, int width, int height)
{
    wxImage img(m_bitmap.ConvertToImage());

    // TODO: why does this make the iconic bitmap not display
    //wxSize newSize(width, height);
    //wxPoint pastePos(width/2.0 - img.GetWidth()/2.0, height/2.0 - img.GetHeight()/2.0);
    //img.Resize(newSize, pastePos);
   
    img.Rescale(width, height);

    return wxBitmap(img);
}

bool TabNotebook::SetOverlayIcon(const wxBitmap& bitmap, const wxString& description)
{
    if (!initialized())
        return false;

    const static wxSize overlaySize(16, 16);

    // passing wxNullBitmap clears the icon
    if (bitmap.IsSameAs(wxNullBitmap))
        return SetOverlayIcon(static_cast<HICON>(0), description);

    wxIcon icon;
    if (bitmap.GetWidth() != overlaySize.x || bitmap.GetHeight() != overlaySize.y) {
        wxImage img(bitmap.ConvertToImage());
        img.Rescale(overlaySize.x, overlaySize.y);
        icon.CopyFromBitmap(wxBitmap(img));
    } else
        icon.CopyFromBitmap(bitmap);

    return SetOverlayIcon(icon, description);
}

bool TabNotebook::InvalidateThumbnails(wxWindow* window)
{
    if (!initialized())
        return false;

    if (TabWindow* tab = tabForWindow(window)) {
        static DwmInvalidateIconicBitmaps_t pDwmInvalidateIconicBitmaps = (DwmInvalidateIconicBitmaps_t)wxDWMAPI.GetSymbol(wxT("DwmInvalidateIconicBitmaps"));
        if (pDwmInvalidateIconicBitmaps)
            return SUCCEEDED(pDwmInvalidateIconicBitmaps(tab->hwnd()));
    }

    return false;
}

bool TabNotebook::SetOverlayIcon(const wxIcon& icon, const wxString& description)
{
    if (!icon.Ok())
        return false;

    HICON hicon = static_cast<HICON>(icon.GetHICON());
    
    return SetOverlayIcon(hicon, description);
}

bool TabNotebook::SetOverlayIcon(HICON hicon, const wxString& description)
{
    return m_taskbarList && SUCCEEDED(m_taskbarList->SetOverlayIcon(hwnd(), hicon, description.wc_str()));
}

TabNotebook::TabNotebook(wxWindow* window)
    : m_initialized(false)
    , m_taskbarList(NULL)
{
    _InitFromHwnd(static_cast<HWND>(window->GetHWND()));
    if (isWin7OrHigher() && m_initialized)
        window->Connect(-1, -1, wxEVT_DESTROY, wxWindowDestroyEventHandler(TabNotebook::OnWindowDestroyed));
}

TabNotebook::TabNotebook(HWND hwnd)
{
    _InitFromHwnd(hwnd);
}

void TabNotebook::_InitFromHwnd(HWND hwnd)
{
    m_hwnd = hwnd;

    if (isWin7OrHigher()) {
        initializeTaskbar();
        if (SUCCEEDED(CoCreateInstance(CLSID_TaskbarList, NULL, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&m_taskbarList))))
            m_initialized = SUCCEEDED(m_taskbarList->HrInit());
    }
}


void TabNotebook::OnWindowDestroyed(wxWindowDestroyEvent& e)
{
    e.Skip();
    if (e.GetWindow() && static_cast<HWND>(e.GetWindow()->GetHWND()) == m_hwnd) {
        DBG(printf("OnWindowDestroyed!\n"));
        Destroy();
    }
}

void TabNotebook::Destroy()
{
    DBG(printf("TabNotebook::Destroy(%p), size is %d\n", this, m_tabMap.empty()));

    while (!m_tabMap.empty()) {
        TabMap::iterator i = m_tabMap.begin();

        if (i != m_tabMap.end()) {
            wxWindow* window = i->first;
            DBG(printf("window: %p\n", window));
            bool result = DestroyTab(window);
            DBG(printf("result: %d\n", result));
            (void)result;
        }
    }
    if (m_taskbarList) {
        m_taskbarList->Release();
        m_taskbarList = NULL;
    }
}

TabNotebook::~TabNotebook()
{
    DBG(printf("~TabNotebook(%p)\n", this));
    Destroy();
}

TabWindow* TabNotebook::CreateTab(wxWindow* window, TabController* controller /*=NULL*/)
{
    if (initialized()) {
        TabWindow* tab = new TabWindow(this, window, controller);
        DBG(printf("CreateTab(%p)\n", window));
        m_tabMap[window] = tab;
        DBG(printf("  m_tabMap[%p] = %p", window, m_tabMap[window]));
        m_tabs.push_back(tab);
        return tab;
    }

    return NULL;
}

bool TabNotebook::RearrangeTab(wxWindow* tabWindow, wxWindow* beforeWindow)
{
    if (!initialized())
        return false;

    if (TabWindow* tab = tabForWindow(tabWindow)) {
        TabWindow* before = NULL;
        if (beforeWindow)
            before = tabForWindow(beforeWindow);
        
        HRESULT res = m_taskbarList->SetTabOrder(tab->hwnd(), before ? before->hwnd() : NULL);
        return SUCCEEDED(res);
    }

    return false;
}

TabWindow* TabNotebook::tabForWindow(wxWindow* window) const
{
    TabMap::const_iterator i = m_tabMap.find(window);
    if (i != m_tabMap.end())
        return i->second;
    else
        return NULL;
}

HWND TabNotebook::GetTabHWND(wxWindow* window) const
{
    if (initialized())
        if (TabWindow* tab = tabForWindow(window))
            return tab->hwnd();

    return 0;
}

bool TabNotebook::SetTabTitle(wxWindow* window, const wxString& title)
{
    if (initialized())
        if (TabWindow* tab = tabForWindow(window))
            return tab->SetTitle(title);

    return false;
}

bool TabNotebook::SetTabActive(wxWindow* window)
{
    if (initialized())
        if (TabWindow* tab = tabForWindow(window))
            return SUCCEEDED(m_taskbarList->SetTabActive(tab->hwnd(), hwnd(), 0));

    return false;
}

bool _setIcon(HWND hwnd, const wxIconBundle& bundle, int smX, int smY, int iconType)
{
    const wxSize size(::GetSystemMetrics(smX), ::GetSystemMetrics(smY));
    const wxIcon icon = bundle.GetIcon(size);
    if (icon.Ok() && icon.GetWidth() == size.x && icon.GetHeight() == size.y) {
        DBG(printf("WM_SETICON %p %d\n", hwnd, iconType));
        ::SendMessage(hwnd, WM_SETICON, iconType, (LPARAM)GetHiconOf(icon));
        return true;
    }

    return false;
}

bool TabNotebook::SetTabIcon(wxWindow* window, const wxBitmap& bitmap)
{
    return SetTabIcon(window, createIconBundle(bitmap));
}

bool TabNotebook::SetTabIcon(wxWindow* window, const wxIconBundle& bundle)
{
    if (initialized()) {
        if (TabWindow* tab = tabForWindow(window)) {
            bool success = true;
            success &= _setIcon(tab->hwnd(), bundle, SM_CXSMICON, SM_CYSMICON, ICON_SMALL);
            success &= _setIcon(tab->hwnd(), bundle, SM_CXICON, SM_CYICON, ICON_BIG);
            return success;
        }
    }

    return false;
}


bool TabNotebook::SetProgressValue(unsigned long long completed, unsigned long long total)
{
    if (m_taskbarList)
        return SUCCEEDED(m_taskbarList->SetProgressValue(hwnd(), completed, total));

    return false;
}

bool TabNotebook::SetProgressState(int flags)
{
    if (m_taskbarList)
        return SUCCEEDED(m_taskbarList->SetProgressState(hwnd(), static_cast<TBPFLAG>(flags)));

    return false;
}

void TabController::OnTabActivated(TaskbarWindow* /*window*/)
{
}

void TabController::OnTabClosed(TaskbarWindow* /*window*/)
{
}

static bool MyDwmSetWindowAttribute(HWND hwnd, DWORD attrib, LPCVOID val, DWORD valSize)
{
    static DwmSetWindowAttribute_t pDwmSetWindowAttribute = (DwmSetWindowAttribute_t)wxDWMAPI.GetSymbol(wxT("DwmSetWindowAttribute"));
    return pDwmSetWindowAttribute && SUCCEEDED(pDwmSetWindowAttribute(hwnd, attrib, val, valSize));
}

// Calls the DwmSetWindowAttribute function for attributes which take a BOOL.
static bool SetDwmBool(HWND hwnd, DWORD attrib, bool value)
{
    BOOL val = value;
    return MyDwmSetWindowAttribute(hwnd, attrib, &val, sizeof(val));
}

void TabNotebook::RegisterTab(TabWindow* tab)
{
    if (m_taskbarList) {
        m_taskbarList->RegisterTab(tab->hwnd(), hwnd());
        m_taskbarList->SetTabOrder(tab->hwnd(), NULL);
        SetDwmBool(hwnd(), DWMWA_DISALLOW_PEEK, true);
    }
}

bool TabNotebook::UnregisterTab(TabWindow* tab)
{
    DBG(printf("UnregisterTab(%p)\n", tab));
    return m_taskbarList && SUCCEEDED(m_taskbarList->UnregisterTab(tab->hwnd()));
}

bool TabNotebook::UnregisterTab(wxWindow* win)
{
    HWND hwnd = static_cast<HWND>(win->GetHWND());
    return m_taskbarList && SUCCEEDED(m_taskbarList->UnregisterTab(hwnd));
}

bool TabNotebook::DestroyTab(wxWindow* window)
{
    if (!initialized())
        return false;

    DBG(printf("TabNotebook::DestroyTab(%p)\n", window));

    if (const TabWindow* tab = tabForWindow(window)) {
        m_tabs.erase(std::remove(m_tabs.begin(), m_tabs.end(), tab), m_tabs.end());
        m_tabMap.erase(window);
        delete tab;
        return true;
    }

    return false;
}

LRESULT CALLBACK TabPreviewWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    TabWindow* wnd = reinterpret_cast<TabWindow*>(::GetWindowLongPtr(hwnd, GWLP_USERDATA));

    LRESULT result = 0;
    if (!wnd && msg == WM_NCCREATE) {
        LPCREATESTRUCT lpcs = (LPCREATESTRUCT)lParam;
        wnd = static_cast<TabWindow*>(lpcs->lpCreateParams);
        wnd->m_hwnd = hwnd;
        ::SetWindowLongPtr(hwnd, GWLP_USERDATA, (LONG_PTR)wnd);
        result = ::DefWindowProc(hwnd, msg, wParam, lParam);
    } else if (wnd)
        result = wnd->WndProc(msg, wParam, lParam);
    else
        result = ::DefWindowProc(hwnd, msg, wParam, lParam);

    return result;
}

static WCHAR const windowClassName[] = L"TabPreviewWindow";

static void registerClass(WNDPROC wndProc, LPCWSTR className)
{
    WNDCLASSEX wcex = {0};
    wcex.cbSize = sizeof(wcex);
    wcex.lpfnWndProc = wndProc;
    wcex.hInstance = wxGetInstance();
    wcex.hCursor = LoadCursor(NULL, IDC_ARROW);
    wcex.lpszClassName = className;

    ::RegisterClassEx(&wcex);
}

static void registerClassOnce()
{
    // creates the window class we'll use for offscreen hidden windows that
    // provide tab thumbnail previews
    static bool didRegisterClass = false;
    if (didRegisterClass) return;
    didRegisterClass = true;

    registerClass(TabPreviewWndProc, windowClassName);
}

TaskbarWindow::TaskbarWindow(TabController* controller)
    : m_controller(controller)
{
}

TabWindow::TabWindow(TabNotebook* notebook, wxWindow* window, TabController* controller)
    : TaskbarWindow(controller)
    , m_notebook(notebook)
    , m_window(window)
{
    DBG(printf("TabWindow::TabWindow(%p)\n", this));
    registerClassOnce();

    ::CreateWindowEx(
        WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        windowClassName,
        window->GetName(),
        WS_POPUP | WS_BORDER | WS_SYSMENU | WS_CAPTION,
        -32000,
        -32000,
        10,
        10,
        NULL,
        NULL,
        wxGetInstance(),
        (LPVOID)this);
}

TabWindow::~TabWindow()
{
    if (m_controller)
        delete m_controller;

    if (!m_hwnd) return;

    m_notebook->UnregisterTab(this);

    SetWindowLongPtr(m_hwnd, GWLP_USERDATA, 0);
    HWND hwnd = m_hwnd;
    m_hwnd = NULL;

    DBG(printf("~TabWindow(%p) calling DestroyWindow(%p)\n", hwnd));
    ::DestroyWindow(hwnd);
}

bool TabWindow::SetTitle(const wxString& title)
{
    return ::SetWindowText(hwnd(), title.c_str()) != 0;
}

LRESULT TabWindow::WndProc(UINT message, WPARAM wParam, LPARAM lParam)
{
    LRESULT result = 0;

    switch (message) {
        case WM_CREATE: {
            SetDwmBool(m_hwnd, DWMWA_FORCE_ICONIC_REPRESENTAITON, true);
            SetDwmBool(m_hwnd, DWMWA_HAS_ICONIC_BITMAP, true);
            m_notebook->RegisterTab(this);
            break;
        }
        
        case WM_ACTIVATE:
            if (LOWORD(wParam) == WA_ACTIVE)
                if (TabController* ctrl = controller())
                    ctrl->OnTabActivated(this);
            break;

        case WM_SYSCOMMAND:
            // All syscommands except for close will be passed along to the tab window
            // outer frame. This allows functions such as move/size to occur properly.
            if (wParam != SC_CLOSE)
                result = SendMessage(m_notebook->hwnd(), WM_SYSCOMMAND, wParam, lParam);
            else
                result = ::DefWindowProc(m_hwnd, message, wParam, lParam);
            break;

        case WM_CLOSE:
            if (TabController* ctrl = controller())
                ctrl->OnTabClosed(this);
            else
                m_notebook->DestroyTab(this->GetWindow());
            break;

        case WM_DWMSENDICONICTHUMBNAIL:
            _SendIconicThumbnail(HIWORD(lParam), LOWORD(lParam));
            break;
 
        case WM_DWMSENDICONICLIVEPREVIEWBITMAP:
            _SendLivePreviewBitmap();
            break;

        case WM_GETICON:
            if (wParam == ICON_SMALL) {
                if (TabController* ctrl = controller()) {
                    // hold a reference to the icon data in a member variable
                    // so the shell has a chance to copy the data before it is
                    // destroyed.
                    m_smallIcon = ctrl->GetSmallIcon(this);
                    if (m_smallIcon.IsOk()) {
                        static wxSize expected(::GetSystemMetrics(SM_CXSMICON), ::GetSystemMetrics(SM_CYSMICON));
                        if (m_smallIcon.GetWidth() != expected.x || m_smallIcon.GetHeight() != expected.y)
                            fprintf(stderr, "WARNING: icon doesn't match expected size: (%d, %d)\n", expected.x, expected.y);

                        result = reinterpret_cast<LRESULT>(m_smallIcon.GetHICON());
                        break;
                    }
                }
            }

            // fallthrough

        default:
            result = ::DefWindowProc(m_hwnd, message, wParam, lParam);
            break;
    }

    return result;
}

void TaskbarWindow::_SendIconicThumbnail(int width, int height)
{
    static DwmSetIconicThumbnail_t pDwmSetIconicThumbnail = (DwmSetIconicThumbnail_t)wxDWMAPI.GetSymbol(wxT("DwmSetIconicThumbnail"));
    if (!pDwmSetIconicThumbnail)
        return;

    if (TabController* ctrl = controller()) {
        HBITMAP hbitmap = 0;

        bool needsDelete = true;
        if (!(hbitmap = static_cast<HBITMAP>(ctrl->GetIconicHBITMAP(this, width, height)))) {
            needsDelete = false;
            wxBitmap bitmap(ctrl->GetIconicBitmap(this, width, height));
            hbitmap = static_cast<HBITMAP>(bitmap.GetHBITMAP());
        }

        if (FAILED(pDwmSetIconicThumbnail(m_hwnd, hbitmap, 0)))
            fprintf(stderr, "error calling DwmSetIconicThumbnail\n");

        if (needsDelete)
            ::DeleteObject(hbitmap);
    }
}

static void GetClientArea(HWND hwndTabFrame, RECT* rcClient);

void TabWindow::_SendLivePreviewBitmap()
{
    static DwmSetIconicLivePreviewBitmap_t pDwmSetIconicLivePreviewBitmap = (DwmSetIconicLivePreviewBitmap_t)wxDWMAPI.GetSymbol(wxT("DwmSetIconicLivePreviewBitmap"));
    if (!pDwmSetIconicLivePreviewBitmap)
        return;

    if (TabController* ctrl = controller()) {
        RECT r;
        GetClientArea(m_notebook->hwnd(), &r);
        wxRect clientRect;
        wxCopyRECTToRect(r, clientRect);
        wxBitmap bitmap(ctrl->GetLivePreview(this, clientRect));
        POINT p = {0, 0};
        if (FAILED(pDwmSetIconicLivePreviewBitmap(m_hwnd, static_cast<HBITMAP>(bitmap.GetHBITMAP()), &p, 0)))
            fprintf(stderr, "error calling DwmSetIconicLivePreviewBitmap\n");
    }
}

static void GetClientArea(HWND hwndTabFrame, RECT* rcClient)
{
    DWORD dwStyle = GetWindowLong(hwndTabFrame, GWL_STYLE);
    DWORD dwStyleEx = GetWindowLong(hwndTabFrame, GWL_EXSTYLE);

    // Compute the actual size the thumbnail will occupy on-screen in order to
    // render the live preview bitmap. We use the tab window outer frame window
    // to compute this. In case that window is minimized, we use GetWindowPlacement
    // to give the correct information.
    RECT rcNCA = {};
    WINDOWPLACEMENT wp;
    if (AdjustWindowRectEx(&rcNCA, dwStyle, FALSE, dwStyleEx) != 0 &&
        GetWindowPlacement(hwndTabFrame, &wp) != 0)
    {
        if (wp.flags & WPF_RESTORETOMAXIMIZED)
        {
            HMONITOR hmon = MonitorFromRect(&wp.rcNormalPosition, MONITOR_DEFAULTTONULL);
            if (hmon)
            {
                MONITORINFO monitorInfo;
                monitorInfo.cbSize = sizeof(MONITORINFO);
                if (GetMonitorInfo(hmon, &monitorInfo))
                {
                    *rcClient = monitorInfo.rcWork;
                }
            }
        }
        else
        {
            CopyRect(rcClient, &wp.rcNormalPosition);
        }

        rcClient->right -= (-rcNCA.left + rcNCA.right);
        rcClient->bottom -= (-rcNCA.top + rcNCA.bottom);
    }

}

static WCHAR const hiddenTabControlName[] = L"HiddenTabControlWindow";
static WCHAR const hiddenParentName[] = L"HiddenTabControlParent";

HiddenTabControlWindow::HiddenTabControlWindow(const wxString& title, const wxIconBundle& bundle, TabController* controller /* = 0*/)
    : TaskbarWindow(controller)
    , m_bundle(bundle)
{
    static bool registered = false;
    if (!registered) {
        registered = true;
        registerClass(HiddenTabControlWindowProc, hiddenTabControlName);
    }
    
    ::CreateWindowEx(
        0x00000100,
        hiddenTabControlName,
        title.c_str(),
        0x1cc00000,
        -32000,
        -32000,
        10,
        10,
        NULL,
        NULL,
        wxGetInstance(),
        (LPVOID)this);
}

void HiddenTabControlWindow::Destroy()
{
    if (m_hwnd)
        ::DestroyWindow(m_hwnd);

    delete this;
}

HiddenTabControlWindow::~HiddenTabControlWindow() 
{}



LRESULT HiddenTabControlWindow::WndProc(UINT message, WPARAM wParam, LPARAM lParam)
{
    LRESULT result = 0;
    switch (message) {
        case WM_DWMSENDICONICTHUMBNAIL:
            _SendIconicThumbnail(HIWORD(lParam), LOWORD(lParam));
            break;

        case WM_SYSCOMMAND:
            if (wParam == SC_CLOSE)
                if (TabController* ctrl = controller())
                    ctrl->OnTabClosed(this);

        case WM_GETICON: {
            wxSize size;
            if (wParam == ICON_BIG)
                size = wxSize(::GetSystemMetrics(SM_CXICON), ::GetSystemMetrics(SM_CYICON));
            else
                size = wxSize(::GetSystemMetrics(SM_CXSMICON), ::GetSystemMetrics(SM_CYSMICON));

            result = reinterpret_cast<LRESULT>(m_bundle.GetIcon(size).GetHICON());
            break;
        }

        case WM_ACTIVATE:
            if (LOWORD(wParam) == WA_ACTIVE)
                if (TabController* ctrl = controller())
                    ctrl->OnTabActivated(this);
            break;

        default:
            result = ::DefWindowProc(m_hwnd, message, wParam, lParam);
            break;
    }
    return result;
}

void HiddenTabControlWindow::Show(bool show /*=true*/)
{
    ::ShowWindow(m_hwnd, show ? SW_SHOWNOACTIVATE : SW_HIDE);
}

void HiddenTabControlWindow::SetIconFile(const wxString& iconFilename)
{
    wxIconBundle bundle(iconFilename, wxBITMAP_TYPE_ICO);
    _setIcon(hwnd(), bundle, SM_CXSMICON, SM_CYSMICON, ICON_SMALL);
    _setIcon(hwnd(), bundle, SM_CXICON, SM_CYICON, ICON_BIG);
}

static void setHiddenControlDwmAttribs(HWND hwnd)
{
    SetDwmBool(hwnd, DWMWA_HAS_ICONIC_BITMAP, true);
    SetDwmBool(hwnd, DWMWA_FORCE_ICONIC_REPRESENTAITON, true);
    SetDwmBool(hwnd, DWMWA_DISALLOW_PEEK, true);

    // Disable this window in Windows+Tab Aero Peek.
    DWMFLIP3DWINDOWPOLICY flipPolicy = DWMFLIP3D_EXCLUDEBELOW;
    MyDwmSetWindowAttribute(hwnd, DWMWA_FLIP3D_POLICY, &flipPolicy, sizeof(flipPolicy));
}

LRESULT CALLBACK HiddenTabControlWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    HiddenTabControlWindow* wnd = reinterpret_cast<HiddenTabControlWindow*>(::GetWindowLongPtr(hwnd, GWLP_USERDATA));

    LRESULT result = 0;
    if (!wnd && msg == WM_NCCREATE) {
        LPCREATESTRUCT lpcs = (LPCREATESTRUCT)lParam;
        wnd = static_cast<HiddenTabControlWindow*>(lpcs->lpCreateParams);
        wnd->m_hwnd = hwnd;
        ::SetWindowLongPtr(hwnd, GWLP_USERDATA, (LONG_PTR)wnd);

        setHiddenControlDwmAttribs(hwnd);

        result = ::DefWindowProc(hwnd, msg, wParam, lParam);
    } else if (wnd)
        result = wnd->WndProc(msg, wParam, lParam);
    else
        result = ::DefWindowProc(hwnd, msg, wParam, lParam);

    return result;
}

static HBITMAP CreateDIBSection32(HDC hdc, int width, int height, void*& pb)
{
    BITMAPINFO bi;
    ::ZeroMemory(&bi.bmiHeader, sizeof bi.bmiHeader);
    bi.bmiHeader.biSize = sizeof bi.bmiHeader;
    bi.bmiHeader.biWidth = width;
    bi.bmiHeader.biHeight = -height;
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    HBITMAP hbitmap = CreateDIBSection(hdc, &bi, DIB_RGB_COLORS, &pb, 0, 0);
    if (hbitmap)
        ::ZeroMemory(pb, 4 * width * height);
    return hbitmap;
}

typedef BOOL (WINAPI *AlphaBlend_t)(HDC,int,int,int,int,
                                    HDC,int,int,int,int,
                                    BLENDFUNCTION);

static DLLLoader MSIMG32DLL(wxT("msimg32"));

static const AlphaBlend_t getAlphaBlendFunc()
{
    static AlphaBlend_t
        pfnAlphaBlend = (AlphaBlend_t)MSIMG32DLL.GetSymbol(_T("AlphaBlend"));
    return pfnAlphaBlend;
}

static HBRUSH brushFromColor(const wxColor& c)
{
    return ::CreateSolidBrush(RGB(c.Red(), c.Green(), c.Blue()));
}

bool AlphaBlend(HDC hdc, int xoriginDest, int yoriginDest, int wDest, int hDest,
                HDC hdcSrc, int xoriginSrc, int yoriginSrc, int wSrc, int hSrc)
{
    static BLENDFUNCTION bf = {AC_SRC_OVER, 0, 255, AC_SRC_ALPHA};

    if (AlphaBlend_t AlphaBlendFunc = getAlphaBlendFunc())
        return TRUE == AlphaBlendFunc(hdc, xoriginDest, yoriginDest, wDest, hDest,
                                      hdcSrc, xoriginSrc, yoriginSrc, wSrc, hSrc,
                                      bf);

    return false;
}

static bool blitBitmap(HDC hdc, const wxBitmap& bitmap, int x, int y, int destWidth=-1, int destHeight=-1)
{
    HDC bitmapHdc = ::CreateCompatibleDC(hdc);
    ::SelectObject(bitmapHdc, static_cast<HBITMAP>(bitmap.GetHBITMAP()));

    if (destWidth == -1)
        destWidth = bitmap.GetWidth();
    if (destHeight == -1)
        destHeight = bitmap.GetHeight();

    bool result = AlphaBlend(hdc, x, y, destWidth, destHeight,
                             bitmapHdc, 0, 0, bitmap.GetWidth(), bitmap.GetHeight());

    ::DeleteDC(bitmapHdc);

    return result;
}
                
HBITMAP getBuddyPreview(const wxSize& size, const wxBitmap& icon, const wxBitmap& highlight)
{
    HDC hdc = ::CreateCompatibleDC(0);
    void* bits;

    HBITMAP destBitmap = ::CreateDIBSection32(hdc, size.x, size.y, bits);
    ::SelectObject(hdc, destBitmap);

    if (highlight.Ok())
        blitBitmap(hdc, highlight, 0, 0, size.x, size.y);

    if (icon.Ok())
        blitBitmap(hdc, icon, size.x/2-icon.GetWidth()/2, size.y/2-icon.GetHeight()/2);

    ::DeleteDC(hdc);

    return destBitmap;
}

#endif // WIN7_TASKBAR

