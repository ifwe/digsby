#include "wx/wxprec.h"

#if __WXMSW__
#define EXPANDO 1
#else
#define EXPANDO 0
#endif

#if EXPANDO
   #include "ExpandoTextCtrl.h"
   #define TC ExpandoTextCtrl
#else
   #define TC wxTextCtrl
#endif

class ExpandoTest : public wxApp{
    public:
	    virtual bool OnInit();
};

class TheFrame : public wxFrame{
    public:
        TheFrame(wxWindow *parent, wxWindowID id, const wxString &title);
    private:
        TC *etc;
        void OnButton(wxCommandEvent &evt);
        void OnText(wxCommandEvent &evt);
};

 
#define ID_BUTTON 1773
#define ID_EXPANDO 1774
 

TheFrame::TheFrame(wxWindow *parent, wxWindowID id, const wxString &title):wxFrame(parent, id, title){
    wxBoxSizer *szr = new wxBoxSizer(wxVERTICAL);
    SetSizer(szr);
    
    #if EXPANDO
        etc = new ExpandoTextCtrl(this,ID_EXPANDO,L"ZOMG oh hia thar!");
        etc->SetMaxHeight(100);
    #else
        etc = new wxTextCtrl(this,ID_EXPANDO,L"",wxDefaultPosition,wxDefaultSize);
        etc->SetSize(etc->GetMinSize());
    #endif
    
    szr->Add(etc);
    
    wxButton *b = new wxButton(this,ID_BUTTON,L"Change");
    szr->Add(b);
    
    Connect(ID_BUTTON,  wxEVT_COMMAND_BUTTON_CLICKED, wxCommandEventHandler(TheFrame::OnButton));
    Connect(ID_EXPANDO, wxEVT_COMMAND_TEXT_UPDATED,   wxCommandEventHandler(TheFrame::OnText  ));
}

DECLARE_APP(ExpandoTest)
 
IMPLEMENT_APP(ExpandoTest)

bool ExpandoTest::OnInit(){

    AllocConsole();
    freopen("CONIN$",  "rb", stdin);
    freopen("CONOUT$", "wb", stdout);
    freopen("CONOUT$", "wb", stderr);

	TheFrame *frame = new TheFrame((wxFrame*) NULL, -1, _T("Expando Test"));
	
    
	frame->Show(true);
	SetTopWindow(frame);
	return true;
}

void TheFrame::OnButton(wxCommandEvent &evt){
    static bool turn = true;
    etc->SetFont(wxFont((turn?20:10), wxFONTFAMILY_DEFAULT, wxFONTSTYLE_NORMAL, wxFONTWEIGHT_NORMAL));
    turn = !turn;
}

void TheFrame::OnText(wxCommandEvent &evt){
    printf("hey! it's a text event!\n");
}
