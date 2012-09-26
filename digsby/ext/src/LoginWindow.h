#ifndef _CGUI_LOGIN_WINDOW_H_
#define _CGUI_LOGIN_WINDOW_H_

#include <wx/frame.h>
#include <wx/bitmap.h>
#include <wx/hyperlink.h>
#include <wx/event.h>

#include <vector>

class wxButton;
class wxCheckBox;
class wxStaticText;
class wxStaticBitmap;
class wxChoice;
class DragMixin;
class BubbleWindow;

struct LoginWindowBitmaps
{
    wxBitmap logo;
    wxBitmap help;
    wxBitmap settings;
    wxBitmap language;
};

class LoginWindow : public wxFrame
{
public:
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

    LoginWindow(wxWindow* window, const wxPoint& pos, LoginWindowBitmaps& bitmaps, const wxString& revision, bool showLanguages);
    LoginWindow();

    bool Create(wxWindow *parent, const wxPoint& pos, LoginWindowBitmaps& bitmaps, const wxString& revision, bool showLanguages);
#ifndef SWIG
    virtual ~LoginWindow();
#endif

    wxChoice* GetLanguageChoice() const { return languageChoice; }
    void UpdateUIStrings();

    void SetStatus(const wxString& status, const wxString& windowTitle = wxEmptyString);
    void EnableControls(bool enable, const wxString& label, int buttonEnable = -1);

    void setShowRevision(bool show, bool repaint = true);
    bool showRevision() const { return m_showRevision; }

    void SetUsername(const wxString&);
    wxString GetUsername() const;
    void SetPassword(const wxString&);
    wxString GetPassword() const;
    bool GetSaveInfo() const;
    void SetSaveInfo(bool);
    bool GetAutoLogin() const;
    void SetAutoLogin(bool);

protected:
    void OnPaint(wxPaintEvent&);
    void OnDoubleClick(wxMouseEvent&);
    void OnCloseLink(wxHyperlinkEvent& evt);

    void OnClickSettings(wxMouseEvent&);
    void OnClickHelp(wxMouseEvent&);
    void HideBubble();

    void OnButtonHover(wxMouseEvent&);
    void OnButtonLeave(wxMouseEvent&);

    void DrawRevision(wxDC& dc, const wxRect& rect);

    wxSizer* createComponents(bool);
    bool useGlass() const { return m_useGlass; }
    void setupGlass();

    BubbleWindow* GetBubble();

    wxBitmap m_logoBitmap;
    wxBitmap m_helpBitmap;
    wxBitmap m_settingsBitmap;
    wxBitmap m_languageBitmap;

    wxString revisionString;
    int glassMarginTop;

    bool m_showRevision;
    bool m_useGlass;
    bool m_helpHover;

    wxPanel* panel;
    wxStaticText* usernameLabel;
    wxTextCtrl* usernameTextbox;
    wxStaticText* passwordLabel;
    wxTextCtrl* passwordTextbox;
    wxButton* saveButton;
    wxCheckBox* saveCheck;
    wxCheckBox* autoLoginCheck;
    wxStaticText* statusLabel;
    wxChoice* languageChoice;

    wxHyperlinkCtrl *forgetPasswordLink;
    wxHyperlinkCtrl *noAccountLink;

    DragMixin* dragMixin;
    BubbleWindow* m_bubble;
    wxStaticBitmap* settingsButton;

    void makeTooltipButton(wxControl* ctrl);

private:
#ifndef SWIG
    DECLARE_DYNAMIC_CLASS(LoginWindow)
    DECLARE_EVENT_TABLE()
#endif

};

#endif // _CGUI_LOGIN_WINDOW_H_
