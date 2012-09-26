#ifndef __WINTASKBAR_H__
#define __WINTASKBAR_H__

#define WIN7_TASKBAR

#include <shobjidl.h>

#include "PlatformMessages.h"
#include <wx/window.h>

#include <vector>
#include <map>
#include <algorithm>
using std::map;
using std::vector;

class TabWindow;
class TaskbarWindow;

class TabController
{
public:
    TabController();
    virtual ~TabController();

    virtual void* GetIconicHBITMAP(TaskbarWindow* window, int width, int height);
    virtual wxBitmap GetIconicBitmap(TaskbarWindow* window, int width, int height);
    virtual wxBitmap GetLivePreview(TabWindow* window, const wxRect& clientSize);
    virtual wxIcon GetSmallIcon(TabWindow* window);

    virtual void OnTabActivated(TaskbarWindow* window);
    virtual void OnTabClosed(TaskbarWindow* window);
};

class SimpleTabController : public TabController
{
public:
    SimpleTabController();
    virtual ~SimpleTabController();

    virtual wxBitmap GetIconicBitmap(TaskbarWindow* window, int width, int height);
    void SetIconicBitmap(const wxBitmap& bitmap);

protected:
    wxBitmap m_bitmap;
};

class TabNotebook : public wxEvtHandler
{
public:
    TabNotebook(wxWindow* window);
    TabNotebook(HWND);
    virtual ~TabNotebook();

    TabWindow* CreateTab(wxWindow* window, TabController* controller = NULL);
    bool DestroyTab(wxWindow*);
    bool RearrangeTab(wxWindow* tabWindow, wxWindow* before);

    bool SetOverlayIcon(const wxBitmap& bitmap, const wxString& description = wxEmptyString);
    bool SetOverlayIcon(const wxIcon& icon, const wxString& description = wxEmptyString);
    bool SetOverlayIcon(HICON icon, const wxString& description = wxEmptyString);

    HWND GetTabHWND(wxWindow* window) const;

    bool SetTabTitle(wxWindow* window, const wxString& title);
    bool SetTabActive(wxWindow* window);
    bool SetTabIcon(wxWindow* window, const wxIconBundle& bundle);
    bool SetTabIcon(wxWindow* window, const wxBitmap& bundle);
    TabWindow* tabForWindow(wxWindow* window) const;

    bool SetProgressValue(unsigned long long completed, unsigned long long total);
    bool SetProgressState(int flags);

    void RegisterTab(TabWindow*);
    bool UnregisterTab(TabWindow*);
    bool UnregisterTab(wxWindow* win);

    bool InvalidateThumbnails(wxWindow* window);

    bool initialized() const { return m_initialized; }
    HWND hwnd() const { return m_hwnd; }

protected:
    void _InitFromHwnd(HWND hwnd);

    void Destroy();
    void OnWindowDestroyed(wxWindowDestroyEvent&);

    HWND m_hwnd;
    bool m_initialized;
    ITaskbarList4* m_taskbarList;

    typedef map<wxWindow*, TabWindow*> TabMap;
    TabMap m_tabMap;

    typedef vector<TabWindow*> TabVector;
    TabVector m_tabs;

private:
    TabNotebook(const TabNotebook&);
};

class TaskbarWindow
{
public:
    TaskbarWindow(TabController* controller);
    TabController* controller() const { return m_controller; }
    virtual wxWindow* GetWindow() const { return NULL; }
    HWND hwnd() const { return m_hwnd; }

protected:
    void _SendIconicThumbnail(int width, int height);
    TabController* m_controller;
    HWND m_hwnd;
};

class TabWindow : public TaskbarWindow
{
public:
    TabWindow(TabNotebook* notebook, wxWindow* win, TabController* controller = NULL);
    virtual ~TabWindow();
    virtual wxWindow* GetWindow() const { return m_window; }
    bool SetTitle(const wxString& title);

protected:
    friend LRESULT CALLBACK TabPreviewWndProc(HWND, UINT, WPARAM, LPARAM);
    LRESULT WndProc(UINT message, WPARAM wParam, LPARAM lParam);

    void _SendLivePreviewBitmap();

    TabNotebook* m_notebook;
    wxWindow* m_window;
    wxIcon m_smallIcon;
};

LRESULT CALLBACK HiddenTabControlWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);

class HiddenTabControlWindow : public TaskbarWindow
{
public:
    HiddenTabControlWindow(const wxString& title, const wxIconBundle& bundle, TabController* controller = 0);
    void Show(bool show=true);
    void Hide() { Show(false); }
    void Destroy();
    void SetIconFile(const wxString&);

protected:
    ~HiddenTabControlWindow();
    friend LRESULT CALLBACK HiddenTabControlWindowProc(HWND, UINT, WPARAM, LPARAM);
    LRESULT WndProc(UINT message, WPARAM wParam, LPARAM lParam);
    wxIconBundle m_bundle;
};

HBITMAP getBuddyPreview(const wxSize& size, const wxBitmap& icon, const wxBitmap& highlight);

#endif // __WINTASKBAR_H__

