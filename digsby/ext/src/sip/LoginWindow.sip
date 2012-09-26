%ModuleHeaderCode
#include "LoginWindow.h"
%End

class DragMixin : wxEvtHandler
{
%TypeHeaderCode
#include "DragMixin.h"
%End
public:
    DragMixin(wxWindow* win);
    virtual ~DragMixin();
private:
    DragMixin(const DragMixin&);    
};

class LoginWindowBitmaps
{
public:
    LoginWindowBitmaps();
    ~LoginWindowBitmaps();

    wxBitmap logo;
    wxBitmap help;
    wxBitmap settings;
    wxBitmap language;
};

class LoginWindow : wxDialog
{
%TypeHeaderCode
#include "LoginWindow.h"
%End
public:
    LoginWindow(wxWindow* window, const wxPoint& pos, LoginWindowBitmaps& bitmaps, const wxString& revision, bool showLanguages);
    virtual ~LoginWindow();

%ConvertToSubClassCode
wxClassInfo* c = sipCpp->GetClassInfo();

if(0) {}
#define C(clz) else if (c == CLASSINFO(clz)) { sipClass = sipClass_ ## clz; }
    C(LoginWindow)
else
    sipClass = NULL;
#undef C
%End

    enum {
        SAVEPASSWORD,
        AUTOLOGIN,
        FORGOTPASSWORD,
        NOACCOUNT,
        CONNSETTINGS,
        CLOSE,
        USERNAME,
        PASSWORD,
        HELPBUTTON,
        LANGUAGE,
    };

    wxChoice* GetLanguageChoice() const;

    void EnableControls(bool enable, const wxString& label, int buttonEnable = -1);
    void UpdateUIStrings();
    void SetStatus(const wxString& status, const wxString& windowTitle = wxEmptyString);

    void SetUsername(const wxString&);
    wxString GetUsername() const;
    void SetPassword(const wxString&);
    wxString GetPassword() const;
    bool GetSaveInfo() const;
    void SetSaveInfo(bool);
    bool GetAutoLogin() const;
    void SetAutoLogin(bool);

    void setShowRevision(bool show, bool repaint = true);
    bool showRevision() const;
};

