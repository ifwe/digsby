/*
%ModuleHeaderCode
#include "WinTaskbar.h"
%End

*/

class TabController /Supertype=sip.wrapper/
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

class SimpleTabController : TabController
{
public:
    SimpleTabController();
    virtual ~SimpleTabController();

    wxBitmap GetIconicBitmap(TabWindow* window, int width, int height);

    void SetIconicBitmap(const wxBitmap& bitmap);
};

typedef unsigned long HWND;

class TabNotebook /Supertype=sip.wrapper/
{
%TypeHeaderCode
#include "WinTaskbar.h"
%End

public:
    TabNotebook(wxWindow* window);
    TabNotebook(HWND);
    virtual ~TabNotebook();

    void CreateTab(wxWindow* window, TabController* controller /Transfer/);
    bool DestroyTab(wxWindow* window);
    bool RearrangeTab(wxWindow* tabWindow, wxWindow* before);
    unsigned long GetTabHWND(wxWindow* window /NotNone/) const;
%MethodCode
        sipRes = (unsigned long)sipCpp->GetTabHWND(a0);
%End

    bool SetTabTitle(wxWindow* window, const wxString& title);
    bool SetTabActive(wxWindow* window);
    bool SetTabIcon(wxWindow* window, const wxIconBundle& bundle);
    bool SetTabIcon(wxWindow* window, const wxBitmap& bundle);
    bool SetOverlayIcon(const wxBitmap& bitmap, const wxString& description = wxEmptyString);
    bool UnregisterTab(wxWindow*);
    bool InvalidateThumbnails(wxWindow* window);

    bool SetProgressValue(int completed, int total);
%MethodCode
        sipRes = sipCpp->SetProgressValue((unsigned long long)a0, (unsigned long long)a1);
%End

    bool SetProgressValue(unsigned long long completed, unsigned long long total);
    bool SetProgressState(int flags);

private:
    TabNotebook(const TabNotebook&);
};

class TaskbarWindow /Supertype=sip.wrapper, NoDefaultCtors/
{
%TypeHeaderCode
#include "WinTaskbar.h"
%End
public:
    wxWindow* GetWindow() const;
};

class TabWindow : TaskbarWindow /NoDefaultCtors/
{
public:
%TypeHeaderCode
#include "WinTaskbar.h"
%End

    wxWindow* GetWindow() const;
};

class HiddenTabControlWindow /Supertype=sip.wrapper/
{
%TypeHeaderCode
#include "WinTaskbar.h"
%End

public:
    HiddenTabControlWindow(const wxString& title, const wxIconBundle& bundle, TabController* controller /Transfer/ = 0) /Transfer/;
    void Show(bool show=true);
    void Hide();
    void Destroy();
    void SetIconFile(const wxString&);

    size_t hwnd();
%MethodCode
        sipRes = (size_t)sipCpp->hwnd();
%End
private:
    HiddenTabControlWindow();
    ~HiddenTabControlWindow();
    HiddenTabControlWindow(const HiddenTabControlWindow&);
};

void* getBuddyPreview(const wxSize& size, const wxBitmap& icon, const wxBitmap& highlight);

