#include <wx/button.h>
#include <wx/checkbox.h>
#include <wx/dcbuffer.h>
#include <wx/sizer.h>
#include <wx/stattext.h>
#include <wx/textctrl.h>
#include <wx/choice.h>
#include <wx/statbmp.h>

#include "cwindowfx.h"
#include "DragMixin.h"
#include "LoginWindow.h"

#if __WXMSW__
#include "WinUtils.h"
#endif

#include <vector>
using std::vector;

IMPLEMENT_DYNAMIC_CLASS(LoginWindow, wxFrame)

BEGIN_EVENT_TABLE(LoginWindow, wxFrame)
    EVT_HYPERLINK(wxID_CLOSE, LoginWindow::OnCloseLink)
END_EVENT_TABLE()

#include "GettextPython.h"

static void setVistaFont(wxWindow* ctrl)
{
    if (!isVistaOrHigher())
        return;
    
    wxFont font(9, wxFONTFAMILY_DEFAULT, wxFONTSTYLE_NORMAL, wxFONTWEIGHT_NORMAL, false, wxT("Segoe UI"));
    ctrl->SetFont(font);
}

static wxRegion GetPolyRegion(vector<wxPoint>& points, int w, int h, int border=1)
{
    wxImage i(w + border, h + border);
    wxBitmap b(i, -1);
    {
        wxMemoryDC m(b);

        m.Clear();
        m.SetBrush(*wxBLACK_BRUSH);
        m.SetPen(*wxBLACK_PEN);
        //ceil(border/2)?
        m.DrawRectangle(0, 0, w + border, h + border);
        m.SetBrush(*wxWHITE_BRUSH);
        m.SetPen(*wxWHITE_PEN);
        m.DrawPolygon(points.size(), &points[0]);
        m.SelectObject(wxNullBitmap);
    }

    b.SetMask(new wxMask(b, *wxBLACK));
    return wxRegion(b);
}

class BubbleWindow : public wxFrame
{
public:
    BubbleWindow() {}

    BubbleWindow(wxWindow* parent, const wxSize& internalSize)
    {
        Create(parent, internalSize);
    }

    bool Create(wxWindow *parent, const wxSize& internalSize)
    {
        setVistaFont(this);
        m_internalSize = internalSize;
        InitPoly();
        if (!wxFrame::Create(parent, wxID_ANY, wxEmptyString,
                wxDefaultPosition, wxDefaultSize,
                wxFRAME_SHAPED | wxBORDER_NONE | wxFRAME_NO_TASKBAR | wxSTAY_ON_TOP))
            return false;

        return true;
    }

    void ShowPointTo(const wxPoint& point)
    {
        int x = point.x;
        int y = point.y;
        int xborder = 0;
        int yborder = 0;
        int startx = 0, starty = 10;
        int px = 10; int py = 0;
        int endx = (2*xborder + m_internalSize.x + startx);
        int endy = (2*yborder + m_internalSize.y + starty);
        int diff = endy;

        Freeze();
        {
            SetPosition(wxPoint(x - px, y - py - diff));
            SetSize(wxSize(endx+1, endy+1));
            SetShape(GetPolyRegion(m_poly, endx, endy));
            ShowNoActivate(true);
        }
        Thaw();
    }

    virtual void DrawContent(wxDC& /*dc*/) {}

    void SetText(const wxString& text)
    {
        if (text == m_labelText)
            return;

        m_labelText = text;

        {
            wxMemoryDC dc;
            dc.SetFont(GetFont());
            m_internalSize = dc.GetTextExtent(text) + wxSize(18, 20);
        }
        InitPoly();

        if (IsShown())
            Refresh();
    }

protected:
    void InitPoly()
    {
        wxPoint point(10, 0);
        int xborder = 0;
        int yborder = 0;
        int startx = 0;
        int starty = 10;
        int px = point.x;
        int py = point.y;
        int endx = (2*xborder + m_internalSize.x + startx);
        int endy = (2*yborder + m_internalSize.y + starty);

#ifdef pt
#error "pt is defined, oops"
#else
#define pt(x, y) wxPoint(x, (-1*(y))+(endy))
#endif

        m_poly.clear();
        m_poly.push_back(pt(px,py));
        m_poly.push_back(pt(px+1,py));
        m_poly.push_back(pt(px+11,starty));
        m_poly.push_back(pt(endx,starty));
        m_poly.push_back(pt(endx,endy));
        m_poly.push_back(pt(startx,endy));
        m_poly.push_back(pt(startx,starty));
        m_poly.push_back(pt(px,starty));
        m_poly.push_back(pt(px,py));

#undef pt
    }

    int GetNumPolyPoints()
    {
        return m_poly.size();
    }

    wxPoint* GetPolyPoints()
    {
        return &m_poly[0];
    }

    void OnPaint(wxPaintEvent&)
    {
        wxAutoBufferedPaintDC dc(this);
        wxColor o(254, 214, 76);
        wxColor y(255, 251, 184);

        dc.SetPen(wxPen(o));
        dc.SetBrush(wxBrush(y));
        dc.DrawPolygon(GetNumPolyPoints(), GetPolyPoints());//, 0, 0, wxWINDING_RULE);
        DrawContent(dc);

        dc.SetFont(GetFont());
        wxSize textSize = dc.GetTextExtent(m_labelText);
        dc.DrawText(m_labelText, 10, (GetSize().y-textSize.y)/2-5);
    }

    wxSize m_internalSize;
    vector<wxPoint> m_poly;
    wxString m_labelText;

private:
    DECLARE_DYNAMIC_CLASS(BubbleWindow)
    DECLARE_EVENT_TABLE()
};

IMPLEMENT_DYNAMIC_CLASS(BubbleWindow, wxFrame)
BEGIN_EVENT_TABLE(BubbleWindow, wxFrame)
    EVT_PAINT(BubbleWindow::OnPaint)
END_EVENT_TABLE()

LoginWindow::LoginWindow(wxWindow* parent, const wxPoint& pos, LoginWindowBitmaps& bitmaps, const wxString& revision, bool showLanguages)
{
    Create(parent, pos, bitmaps, revision, showLanguages);
}

LoginWindow::LoginWindow()
{
}

BubbleWindow* LoginWindow::GetBubble()
{
    if (!m_bubble)
        m_bubble = new BubbleWindow(this, wxSize(100, 40));

    return m_bubble;
}

bool LoginWindow::Create(wxWindow *parent, const wxPoint& pos, LoginWindowBitmaps& bitmaps, const wxString& revision, bool showLanguages)
{
#if __WXMSW__
    m_useGlass = isGlassEnabled();
    wxLogDebug(wxT("creating LoginWindow(glass=%d)"), m_useGlass);
#endif

    m_bubble = 0;
    languageChoice = 0;

    int style = wxDEFAULT_FRAME_STYLE & ~(wxRESIZE_BORDER | wxMAXIMIZE_BOX | wxMINIMIZE_BOX);
    if (!useGlass())
        style |= wxFRAME_SHAPED;

    if (!wxFrame::Create(parent, wxID_ANY, wxT(""), pos, wxDefaultSize, style, wxT("Digsby Login Window")))
        return false;

    m_logoBitmap = bitmaps.logo;
    m_helpBitmap = bitmaps.help;
    m_settingsBitmap = bitmaps.settings;
    m_languageBitmap = bitmaps.language;

    m_helpHover = false;

    revisionString = revision;

    m_showRevision = false;

    SetBackgroundStyle(wxBG_STYLE_CUSTOM);
    createComponents(showLanguages);

    setupGlass();
    if(!useGlass())
        SetShape(wxRegion(0, 0, GetClientSize().x, GetClientSize().y));

    // push an event handler that allows dragging the window from any point
    dragMixin = new DragMixin(panel);
    panel->PushEventHandler(dragMixin);

    return true;
}

void LoginWindow::setupGlass()
{
#if __WXMSW__
    if (useGlass()) {
        glassMarginTop = 10 + m_logoBitmap.GetHeight();
        glassExtendInto(this, 0, 0, glassMarginTop, 0);
    } else 
#endif
    {
        glassMarginTop = 0;
    }
}

LoginWindow::~LoginWindow()
{
}

void LoginWindow::UpdateUIStrings()
{
    SetTitle(_("Welcome to Digsby"));
    usernameLabel->SetLabel(_("Profile &Name:"));
    passwordLabel->SetLabel(_("&Profile Password:"));
    saveCheck->SetLabel(_("&Save password"));
    autoLoginCheck->SetLabel(_("&Auto login"));
    saveButton->SetLabel(_("Sign In"));
    forgetPasswordLink->SetLabel(_("Forgot?"));
    noAccountLink->SetLabel(_("New User?"));
    GetSizer()->Fit(this);

}

void LoginWindow::SetStatus(const wxString& status, const wxString& windowTitle /* = wxEmptyString */)
{
    statusLabel->SetLabel(status);

    wxString title(windowTitle.length() ? windowTitle : status);
    if (title.length())
        SetTitle(title);

    panel->Layout();
}

void LoginWindow::EnableControls(bool enable, const wxString& label, int buttonEnable)
{
    Freeze();

    usernameTextbox->Enable(enable);
    passwordTextbox->Enable(enable);
    saveCheck->Enable(enable);

    if (buttonEnable != -1)
        saveButton->Enable(buttonEnable != 0);

    saveButton->SetLabel(label);

    Thaw();
    Refresh();
    Update();
}

void LoginWindow::setShowRevision(bool show, bool repaint)
{
    m_showRevision = show;
    if (repaint)
        Refresh();
}

static void setHyperlinkColor(wxHyperlinkCtrl* link)
{
    wxColor c(link->GetNormalColour());
    link->SetVisitedColour(c);
    link->SetHoverColour(c);
}

void LoginWindow::makeTooltipButton(wxControl* ctrl)
{
    ctrl->SetCursor(wxCURSOR_HAND);
    ctrl->Connect((int)wxEVT_MOTION, (wxObjectEventFunction)&LoginWindow::OnButtonHover, (wxObject*)NULL, (wxEvtHandler*)this);
    ctrl->Connect((int)wxEVT_LEAVE_WINDOW, (wxObjectEventFunction)&LoginWindow::OnButtonLeave, (wxObject*)NULL, (wxEvtHandler*)this);
}

wxSizer* LoginWindow::createComponents(bool showLanguages)
{
    panel = new wxPanel(this);
    panel->SetBackgroundStyle(wxBG_STYLE_CUSTOM);
    panel->Connect((int)wxEVT_PAINT, (wxObjectEventFunction)&LoginWindow::OnPaint, (wxObject*)NULL, (wxEvtHandler*)this);
    panel->Connect((int)wxEVT_LEFT_DCLICK, (wxObjectEventFunction)&LoginWindow::OnDoubleClick, (wxObject*)NULL, (wxEvtHandler*)this);

    //
    // Construct
    //
    wxHyperlinkCtrl *closeLink = 0;
#ifndef __WXMAC__
    if (!useGlass()) {
        closeLink = new wxHyperlinkCtrl(panel, wxID_CLOSE, wxT("X"), wxT("#"));
        ModifyFont(closeLink, wxFONTWEIGHT_BOLD, 14, wxT("Arial Black"), 0);
        closeLink->SetNormalColour(wxColour(0xBB, 0xBB, 0xBB));
        closeLink->SetHoverColour(wxColour(0x4f, 0x4f, 0x4f));
    }
#endif

    // username, password
    usernameLabel = new wxStaticText(panel, -1, wxEmptyString);
    usernameTextbox = new wxTextCtrl(panel, USERNAME);
    passwordLabel = new wxStaticText(panel, -1, wxEmptyString);
    passwordTextbox = new wxTextCtrl(panel, PASSWORD, wxEmptyString, wxDefaultPosition, wxDefaultSize, wxTE_PASSWORD);

    // save password, auto login checkboxes
    saveCheck = new wxCheckBox(panel, SAVEPASSWORD, wxEmptyString);
    autoLoginCheck = new wxCheckBox(panel, AUTOLOGIN, wxEmptyString);

    // sign in button
    saveButton = new wxButton(panel, wxID_OK, wxEmptyString);
    saveButton->SetDefault();

    // help hyperlinks
    forgetPasswordLink = new wxHyperlinkCtrl(panel, FORGOTPASSWORD, wxEmptyString, wxT("#"));
    noAccountLink = new wxHyperlinkCtrl(panel, NOACCOUNT, wxEmptyString, wxT("#"));

    settingsButton = new wxStaticBitmap(panel, -1, m_settingsBitmap);
    settingsButton->Connect((int)wxEVT_LEFT_DOWN, (wxObjectEventFunction)&LoginWindow::OnClickSettings, (wxObject*)NULL, (wxEvtHandler*)this);
    makeTooltipButton(settingsButton);

    wxStaticBitmap* helpButton = new wxStaticBitmap(panel, -1, m_helpBitmap);
    helpButton->Connect((int)wxEVT_LEFT_DOWN, (wxObjectEventFunction)&LoginWindow::OnClickHelp, (wxObject*)NULL, (wxEvtHandler*)this);
    makeTooltipButton(helpButton);

    // language dropdown
    wxStaticBitmap* languageBitmap = 0;
    if (showLanguages) { 
        //languageBitmap = new wxStaticBitmap(panel, -1, m_languageBitmap);
        languageChoice = new wxChoice(panel, LANGUAGE);
    }

#ifdef __WXMAC__
    // on Mac, make the links the smaller variant
    wxWindowVariant windowVariant = wxWINDOW_VARIANT_SMALL;
    forgetPasswordLink->SetWindowVariant(windowVariant);
    noAccountLink->SetWindowVariant(windowVariant);
#endif

    // status text
    statusLabel = new wxStaticText(panel, -1, wxEmptyString, wxDefaultPosition, wxDefaultSize, wxALIGN_CENTER);
    ModifyFont(statusLabel, wxFONTWEIGHT_BOLD);

    // set background colors of controls to match the window
    wxColor bgColor(*wxWHITE);
    usernameLabel->SetBackgroundColour(bgColor);
    passwordLabel->SetBackgroundColour(bgColor);
    saveCheck->SetBackgroundColour(bgColor);
    autoLoginCheck->SetBackgroundColour(bgColor);
    saveButton->SetBackgroundColour(bgColor);
    forgetPasswordLink->SetBackgroundColour(bgColor);
    noAccountLink->SetBackgroundColour(bgColor);
    statusLabel->SetBackgroundColour(bgColor);
    if (closeLink)
        closeLink->SetBackgroundColour(bgColor);

    setHyperlinkColor(forgetPasswordLink);
    setHyperlinkColor(noAccountLink);

    setVistaFont(usernameLabel);
    setVistaFont(passwordLabel);
    setVistaFont(saveCheck);
    setVistaFont(autoLoginCheck);
    setVistaFont(saveButton);
    setVistaFont(forgetPasswordLink);
    setVistaFont(noAccountLink);

    //
    // Layout
    //
    wxBoxSizer* outerSizer = new wxBoxSizer(wxHORIZONTAL);
    wxBoxSizer* mainSizer = new wxBoxSizer(wxVERTICAL);
    wxBoxSizer* subSizer = new wxBoxSizer(wxHORIZONTAL);

    subSizer->Add(saveCheck);
    subSizer->Add(saveButton->GetSize().x / 2, 0);
    subSizer->Add(autoLoginCheck);

    if (closeLink) {
        wxBoxSizer* linkSizer = new wxBoxSizer(wxHORIZONTAL);
        linkSizer->Add(closeLink, 0, wxALIGN_RIGHT);
        linkSizer->AddSpacer(8);
        mainSizer->Add(linkSizer, 0, wxALIGN_RIGHT);
    }

    mainSizer->Add(0, m_logoBitmap.GetHeight() + 10);

    if (!useGlass())
        mainSizer->Add(10, 10);

    wxBoxSizer* hSizer = new wxBoxSizer(wxHORIZONTAL);
    hSizer->Add(0, 7);
    hSizer->AddStretchSpacer(1);
    hSizer->Add(statusLabel, 0, wxEXPAND);
    hSizer->AddStretchSpacer(1);

    wxBoxSizer* usernameHSizer = new wxBoxSizer(wxHORIZONTAL);
    usernameHSizer->Add(usernameLabel);
    usernameHSizer->AddStretchSpacer(1);
    usernameHSizer->Add(noAccountLink);
    mainSizer->Add(usernameHSizer, 0, wxEXPAND);

    mainSizer->Add(usernameTextbox, 0, wxEXPAND | wxALL, 4);

    wxBoxSizer* passwordHSizer = new wxBoxSizer(wxHORIZONTAL);
    passwordHSizer->Add(passwordLabel);
    passwordHSizer->AddStretchSpacer(1);
    passwordHSizer->Add(forgetPasswordLink);
    mainSizer->Add(passwordHSizer, 0, wxEXPAND);

    mainSizer->Add(passwordTextbox, 0, wxEXPAND | wxALL, 4);
    mainSizer->Add(subSizer, 0, wxALIGN_CENTER);

    mainSizer->AddSpacer(10);
    mainSizer->Add(hSizer, 0, wxALIGN_CENTER);
    mainSizer->AddSpacer(10);
    mainSizer->Add(saveButton, 0, wxALIGN_CENTER);

    mainSizer->AddSpacer(20);

    wxBoxSizer* buttonsH = new wxBoxSizer(wxHORIZONTAL);
    buttonsH->Add(settingsButton, 0, wxALIGN_BOTTOM);
    buttonsH->Add(helpButton, 0, wxALIGN_BOTTOM | wxLEFT, 4);
    buttonsH->AddStretchSpacer(1);
    if (languageBitmap)
        buttonsH->Add(languageBitmap, 0, wxALIGN_BOTTOM | wxRIGHT, 4);
    if (languageChoice)
        buttonsH->Add(languageChoice, 0, wxALIGN_BOTTOM | wxRIGHT, 4);
    mainSizer->Add(buttonsH, 0, wxEXPAND);


    outerSizer->Add(mainSizer, 1, wxEXPAND | wxALL, 4);

    panel->SetSizer(outerSizer);

    wxSizer* s = new wxBoxSizer(wxVERTICAL);
    s->Add(panel, 1, wxEXPAND);


    SetSizer(s);

    UpdateUIStrings();
    return outerSizer;
}

void LoginWindow::OnDoubleClick(wxMouseEvent& event)
{
    event.Skip();
    setShowRevision(!showRevision());
    Refresh();
}

void LoginWindow::OnPaint(wxPaintEvent&)
{
    // note: this OnPaint is actually called for the "panel" member variable wxPanel object's EVT_PAINT
    wxAutoBufferedPaintDC dc(panel);
    dc.SetPen(*wxTRANSPARENT_PEN);
    dc.SetBrush(*wxWHITE);
    dc.DrawRectangle(panel->GetClientRect());

    wxRect rect(GetClientSize());
    if (useGlass()) {
        // black in the extended glass area becomes transparent
        dc.SetBrush(*wxBLACK_BRUSH);
        dc.DrawRectangle(rect.x, rect.y, rect.width, glassMarginTop);

        // don't draw white onto the glass area
        rect.SetHeight(rect.GetHeight() - glassMarginTop);
        rect.Offset(0, glassMarginTop);
    } else
        dc.SetPen(*wxBLACK_PEN);

    dc.SetBrush(*wxWHITE_BRUSH);
    dc.DrawRectangle(rect);

    // draw the digsby logo
    dc.DrawBitmap(m_logoBitmap, GetClientSize().x / 2 - m_logoBitmap.GetWidth() / 2, useGlass() ? 0 : 30, true);

    if (showRevision())
        DrawRevision(dc, rect);
}

void LoginWindow::OnCloseLink(wxHyperlinkEvent&)
{
    Close();
}

void LoginWindow::HideBubble()
{
    if (wxWindow* window = wxWindow::GetCapture())
        while (window->HasCapture())
            window->ReleaseMouse();

    GetBubble()->Hide();
}

void LoginWindow::OnClickSettings(wxMouseEvent&)
{
    HideBubble();
    wxHyperlinkEvent linkEvent(panel, CONNSETTINGS, wxT("#"));
    GetEventHandler()->ProcessEvent(linkEvent);
}

void LoginWindow::OnClickHelp(wxMouseEvent&)
{
    HideBubble();
    wxCommandEvent event(wxEVT_COMMAND_BUTTON_CLICKED, HELPBUTTON);
    GetEventHandler()->ProcessEvent(event);
}

void LoginWindow::OnButtonHover(wxMouseEvent& e)
{
    e.Skip();
    if (wxObject* obj = e.GetEventObject()) {
        wxControl* ctrl = (wxControl*)obj;
        if (!ctrl->GetClientRect().Contains(e.GetPosition())) {
            while (ctrl->HasCapture())
                ctrl->ReleaseMouse();
            GetBubble()->Show(false);
        } else if (IsActive()) {
            wxPoint pt(ctrl->ClientToScreen(wxPoint(ctrl->GetSize().x/2, 0)));
            ctrl->CaptureMouse();
            GetBubble()->SetText(ctrl == settingsButton ? wxT("Connection Settings") : wxT("Help"));
            GetBubble()->ShowPointTo(pt);
        }
    }
}

void LoginWindow::OnButtonLeave(wxMouseEvent& e)
{
    e.Skip();
    if (wxObject* obj = e.GetEventObject()) {
        wxControl* ctrl = (wxControl*)obj;
        while (ctrl->HasCapture())
            ctrl->ReleaseMouse();
        GetBubble()->Show(false);
    }
}

void LoginWindow::DrawRevision(wxDC& dc, const wxRect& rect)
{
    static wxColour revisionColor(200, 200, 200);
    wxFont font(GetFont());
    font.SetPointSize(7);

    int x, y;
    dc.GetTextExtent(revisionString, &x, &y);
    dc.SetFont(font);
    dc.SetTextForeground(revisionColor);
    dc.DrawText(revisionString, rect.x + 5, rect.GetBottom() - y - 18);
}

void LoginWindow::SetUsername(const wxString& username)
{
    usernameTextbox->ChangeValue(username);
}

wxString LoginWindow::GetUsername() const
{
    return usernameTextbox->GetValue();
}

void LoginWindow::SetPassword(const wxString& password)
{
    passwordTextbox->ChangeValue(password);
}

wxString LoginWindow::GetPassword() const
{
    return passwordTextbox->GetValue();
}

bool LoginWindow::GetSaveInfo() const
{
    return saveCheck->GetValue();
}

void LoginWindow::SetSaveInfo(bool saveInfo)
{
    saveCheck->SetValue(saveInfo);
}

bool LoginWindow::GetAutoLogin() const
{
    return autoLoginCheck->GetValue();
}

void LoginWindow::SetAutoLogin(bool autoLogin)
{
    autoLoginCheck->SetValue(autoLogin);
}

//test
