//ExpandoTextCtrl test splitter edition


#define ENCODER HTMLEncoder

#define USEEXPANDO 1

#if USEEXPANDO
    #define INPUTCTRL ExpandoTextCtrl
#else
    #define INPUTCTRL InputBox
#endif //USEEXPANDO


#include "wx/wx.h"
#include "wx/fontdlg.h"
#include "wx/numdlg.h"
#include "wx/colordlg.h"
#include "wx/splitter.h"

#include "DebugUtil.h"
#include "ExpandoTextCtrl.h"
#include "InputBox.h"
#include "ExpandEvent.h"
#include "SelectionEvent.h"
#include "StyleDescs.h"

#include "RTFToX.h"

#include <cstdio>
#include <Richedit.h>

#include "HTMLEncoder.h"

//#define RTFLINK = L"{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1033{\\fonttbl{\\f0\\fswiss\\fcharset0 Comic Sans MS;}{\\f1\\fnil\\fcharset0 MS Shell Dlg 2;}}\r\n{\\colortbl ;\\red255\\green0\\blue255;\\red0\\green255\\blue255;}\r\n{\\*\\generator Msftedit 5.41.21.2509;}\\viewkind4\\uc1\\pard\\cf1\\highlight2\\ul\\b\\i\\f0\\fs44 test 123\\cf0\\highlight0\\ulnone\\b0\\i0\\f1\\fs17\\par\\parI use {\\hl {\\hlloc  http://www.digsby.com/?utm_source=aim&utm_medium=aim&utm_campaign=aimprofilelink } {\\hlfr digsby} }\\par\r\n}"

class ExpandoApp: public wxApp{
	virtual bool OnInit();
};

void CreateTestWindow(ExpandoApp *app, wxString title);

//Format IDs
int ID_FONT = wxNewId();
int ID_SIZE = wxNewId();
int ID_BOLD = wxNewId();
int ID_ITAL = wxNewId();
int ID_UNDR = wxNewId();
int ID_COLR = wxNewId();
int ID_BCLR = wxNewId();
int ID_RTLT = wxNewId();

//Debug IDs
int ID_GRTF = wxNewId();
int ID_SEPR = wxNewId();
int ID_RTFG = wxNewId();
int ID_RSIZ = wxNewId();
int ID_SETV = wxNewId();
int ID_GVAL = wxNewId();
int ID_LINK = wxNewId();
int ID_NEW  = wxNewId();

RTFToX converter;
ENCODER encoder(false);
wxTextCtrl *output, *input;

wxString rtfTemp;


class DebugBar : public wxPanel{
    public:
    
        INPUTCTRL *textctrl;
        
        DebugBar(wxWindow *parent, wxWindowID id, INPUTCTRL *textctrl) : wxPanel(parent, id){
            SetMinSize(wxSize(-1, 30));
            wxBoxSizer *ts = new wxBoxSizer(wxHORIZONTAL);
            SetSizer(ts);
            
            this->textctrl = textctrl;
            
            Connect(wxEVT_COMMAND_BUTTON_CLICKED, wxCommandEventHandler(DebugBar::OnButton));
            
            
            wxButton *brtf       = new wxButton(this, ID_GRTF, _T("Convert"));
            wxButton *bsep       = new wxButton(this, ID_SEPR, _T("==="));
            wxButton *bresize    = new wxButton(this, ID_RSIZ, _T("ReSize"));
            wxButton *brtfstore  = new wxButton(this, ID_RTFG, _T("Get/Set"));
            wxButton *bsetval    = new wxButton(this, ID_SETV, _T("Set"));
            wxButton *bptxt      = new wxButton(this, ID_GVAL, _T("Plaintext"));
            wxButton *blink      = new wxButton(this, ID_LINK, _T("Link"));
            wxButton *bnew       = new wxButton(this, ID_NEW , _T("New"));
            
            
            
            brtf->SetMinSize(wxSize(50,30));
            bsep->SetMinSize(wxSize(30,30));
            brtfstore->SetMinSize(wxSize(50,30));
            bresize->SetMinSize(wxSize(50,30));
            bsetval->SetMinSize(wxSize(30,30));
            bptxt->SetMinSize(wxSize(50,30));
            blink->SetMinSize(wxSize(30,30));
            bnew->SetMinSize(wxSize(30,30));
            
            
            ts->Add(brtf, 0, 0);
            ts->Add(bsep, 0, 0);
            ts->Add(brtfstore, 0, 0);
            ts->Add(bresize, 0, 0);
            ts->Add(bsetval, 0, 0);
            ts->Add(bptxt, 0, 0);
            ts->Add(blink, 0, 0);
            ts->Add(bnew, 0, 0);
        }
        
        void OnButton(wxCommandEvent &event){
        
           
            int id = event.GetId();
            long flags = 0;

            if(id == ID_GRTF){
                wxString rtf = textctrl->GetRTF();
                printf("%s\n\n", rtf.ToAscii());
                output->SetValue(converter.Convert(rtf, encoder));
                input->SetValue(rtf);
            }else if(id == ID_GVAL){
                wxString text = textctrl->GetValue();
                wxTextAttr style;
                textctrl->GetStyle(0, style);
                output->SetValue(converter.Convert(text, encoder, L"plaintext", &style));
                input->SetValue(text);
            }else if(id == ID_SEPR){
                printf("\n========\n\n");
            }else if(id == ID_RSIZ){
#if USEEXPANDO
                textctrl->SetMinHeight(wxGetNumberFromUser(_T("Input Height:"), _T(""),  _T("Set Input Height"), textctrl->GetMinHeight()));
                printf("%d\n", textctrl->GetMinSize().GetHeight());
#endif //USEEXPANDO
            }else if(id == ID_RTFG){
                if(rtfTemp.IsEmpty()){
                    rtfTemp = textctrl->GetRTF();
                    textctrl->Clear();
                }else{
                    textctrl->SetRTF(rtfTemp);
                    rtfTemp.Clear();
                }
            }else if(id == ID_SETV){
                wxString v = wxGetTextFromUser(L"Text?");
                textctrl->SetValue(v);
            }else if(id == ID_LINK){
                wxString rtf(L"{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1033{\\fonttbl{\\f0\\fswiss\\fcharset0 Comic Sans MS;}{\\f1\\fnil\\fcharset0 MS Shell Dlg 2;}}\r\n{\\colortbl ;\\red255\\green0\\blue255;\\red0\\green255\\blue255;}\r\n{\\*\\generator Msftedit 5.41.21.2509;}\\viewkind4\\uc1\\pard\\cf1\\highlight2\\ul\\b\\i\\f0\\fs44 test 123\\cf0\\highlight0\\ulnone\\b0\\i0\\f1\\fs17\\par\\par I use {\\hl {\\hlloc  http://www.digsby.com/?utm_source=aim&utm_medium=aim&utm_campaign=aimprofilelink } {\\hlfr digsby} }\\par\r\n}");
                //printf("%s\n\n", rtf.ToAscii());
                output->SetValue(converter.Convert(rtf, encoder));
                input->SetValue(rtf);
            }else if(id == ID_NEW){
                CreateTestWindow((ExpandoApp*)wxTheApp, L"Spawn");
            }
            
            textctrl->SetFocus();
        }
        
};


class ToolBar : public wxPanel{
    public:
    
        INPUTCTRL *textctrl;
        
        ToolBar(wxWindow *parent, wxWindowID id, INPUTCTRL *textctrl) : wxPanel(parent, id){
            SetMinSize(wxSize(-1, 30));
            wxBoxSizer *ts = new wxBoxSizer(wxHORIZONTAL);
            SetSizer(ts);
            
            this->textctrl = textctrl;
            
            Connect(wxEVT_COMMAND_BUTTON_CLICKED, wxCommandEventHandler(ToolBar::OnButton));
            
            wxButton *bfont      = new wxButton(this, ID_FONT, _T("F" ));
            wxButton *bsize      = new wxButton(this, ID_SIZE, _T("S"));
            wxButton *bbold      = new wxButton(this, ID_BOLD, _T("B"));
            wxButton *bitalic    = new wxButton(this, ID_ITAL, _T("I"));
            wxButton *bunderline = new wxButton(this, ID_UNDR, _T("U"));
            wxButton *bcolor     = new wxButton(this, ID_COLR, _T("C"));
            wxButton *bbgcolor   = new wxButton(this, ID_BCLR, _T("BC"));
            wxButton *brtl       = new wxButton(this, ID_RTLT, _T("RTL"));
            
            
            
            bfont->SetMinSize(wxSize(30,30));
            bsize->SetMinSize(wxSize(30,30));
            bbold->SetMinSize(wxSize(30,30));
            bitalic->SetMinSize(wxSize(30,30));
            bunderline->SetMinSize(wxSize(30,30));
            bcolor->SetMinSize(wxSize(30,30));
            bbgcolor->SetMinSize(wxSize(30,30));
            brtl->SetMinSize(wxSize(30,30));
            
            
            
            
            ts->Add(bfont, 0, 0);     
            ts->Add(bsize, 0, 0);     
            ts->Add(bbold, 0, 0);   
            ts->Add(bitalic, 0, 0); 
            ts->Add(bunderline, 0, 0);
            ts->Add(bcolor, 0, 0);
            ts->Add(bbgcolor, 0, 0);
            ts->Add(brtl, 0, 0);
            
        }
        
        void OnButton(wxCommandEvent &event){
        
            wxTextAttr textattr;
            int i = textctrl->GetInsertionPoint();
            textctrl->GetStyle(i, textattr);
            
            
            
            wxFont font = textattr.GetFont();
        
            int id = event.GetId();
            long flags = 0;

            if(id == ID_FONT){
                font = wxGetFontFromUser(this, font);
                flags = wxTEXT_ATTR_FONT_FACE;
            }else if(id == ID_SIZE){
                font.SetPointSize(wxGetNumberFromUser(_T("Size:"), _T(""),  _T("Set Font Size"), font.GetPointSize()));
                flags = wxTEXT_ATTR_FONT_SIZE;
            }else if(id == ID_BOLD){
                font.SetWeight(font.GetWeight() != wxFONTWEIGHT_BOLD? wxFONTWEIGHT_BOLD : wxFONTWEIGHT_NORMAL);
                flags = wxTEXT_ATTR_FONT_WEIGHT;
            }else if(id == ID_ITAL){
                font.SetStyle(font.GetStyle() != wxFONTSTYLE_ITALIC? wxFONTSTYLE_ITALIC : wxFONTSTYLE_NORMAL);
                flags = wxTEXT_ATTR_FONT_ITALIC;
            }else if(id == ID_UNDR){
                font.SetUnderlined(!font.GetUnderlined());
                flags = wxTEXT_ATTR_FONT_UNDERLINE;
            }else if(id == ID_COLR){
                textattr.SetTextColour(wxGetColourFromUser(this, textattr.GetTextColour()));
                flags = wxTEXT_ATTR_TEXT_COLOUR;
            }else if(id == ID_BCLR){
                textattr.SetBackgroundColour(wxGetColourFromUser(this, textattr.GetBackgroundColour()));
                flags = wxTEXT_ATTR_BACKGROUND_COLOUR;
            }else if(id == ID_RTLT){
                //textctrl->SetSelection(0, textctrl->GetLastPosition());
                
                textctrl->SetRTL(!textctrl->GetRTL());
                
                textctrl->SetFocus();
                return;
                
            }
            
            long start, end;
            textctrl->GetSelection(&start, &end);
            
            //printf("TextAttr flags: %x\n", textattr.GetFlags());
            textattr.SetFont(font);
            
            textattr.SetFlags(flags);
            //printf("TextAttr flags: %x\n", textattr.GetFlags());
            
            textctrl->SetStyle(start, end, textattr);
            
            textctrl->SetFocus();
        }
        
};

class LayoutPanel: public wxPanel{
    public:
        LayoutPanel(wxWindow* parent, wxWindowID id) : wxPanel(parent, id){
            Connect(wxEVT_ETC_LAYOUT_NEEDED, wxCommandEventHandler(LayoutPanel::OnLayoutNeeded));
        }
        
        void OnLayoutNeeded(wxCommandEvent &event){
            GetSizer()->Layout();
            event.Skip();
        }
};

class ExpandoSplitter : public wxSplitterWindow{
    public:
    
        bool resizing;
        ExpandoTextCtrl *expando;
        
        
        
    
        ExpandoSplitter(wxWindow*  parent, wxWindowID id, const wxPoint&  point = wxDefaultPosition,
                        const wxSize&  size = wxDefaultSize, long style=wxSP_3D,
                        const wxString&  name = L"splitterWindow")
                        : wxSplitterWindow(parent, id, point, size, style, name){
                        
             resizing = false;
             
             SetSashGravity(1);
             SetMinimumPaneSize(10);
             
             Connect(wxEVT_ETC_LAYOUT_NEEDED, wxCommandEventHandler(ExpandoSplitter::OnExpandEvent));
             Connect(wxEVT_LEFT_DOWN, wxCommandEventHandler(ExpandoSplitter::OnSplitterStart));
             Connect(wxEVT_LEFT_UP, wxCommandEventHandler(ExpandoSplitter::OnSplitterSet));
                       
        }
        
        
        void OnSplitterStart(wxCommandEvent& event){
        
            resizing = true;
        
            expando->SetMinHeight(expando->GetNatHeight());
            
            event.Skip();
            
        }
        
        void OnSplitterSet(wxCommandEvent& event){
        
            resizing = false;
            event.Skip();
        
            int natHeight = expando->GetNatHeight();
            int setHeight = expando->GetSize().GetHeight();
            int height = setHeight <= natHeight? -1 : setHeight;
            expando->SetMinHeight(height);
        
        
        }
        
        void OnExpandEvent(wxCommandEvent& event){
            if(resizing) return;
            int h =  GetSashSize() + expando->GetMinSize().GetHeight();
            //printf("Expando Event resize: %d\n", h);
            //printf("MaxHeight: %d\tMaxSize.Height: %d\n", expando->GetMaxHeight(), expando->GetMaxSize().GetHeight());
            //printf("MinHeight: %d\tMinSize.Height: %d\n\n", expando->GetMinHeight(), expando->GetMinSize().GetHeight());
            
            SetSashPosition(GetSize().GetHeight() - h);
            
            //SetSashPosition(GetSize().GetHeight() - GetSashSize() - expando->GetMinSize().GetHeight());
        }
        
        void RegisterExpando(ExpandoTextCtrl *expando){
            this->expando = expando;
            
        }
        
        void OnDoubleClickSash(int x, int y){
            return;
        }
    
    
};

 
    
void CreateTestWindow(ExpandoApp *app, wxString title){
	wxFrame *frame = new wxFrame(NULL, -1, title, wxPoint(200,100), wxSize(400,400));
	wxBoxSizer *fs = new wxBoxSizer(wxVERTICAL);
	frame->SetSizer(fs);
	LayoutPanel *panel = new LayoutPanel(frame, -1);
	wxBoxSizer *s = new wxBoxSizer(wxVERTICAL);
	panel->SetSizer(s);
	fs->Add(panel, 1, wxEXPAND);
	
	
	ExpandoSplitter *splitter = new ExpandoSplitter(panel, -1, wxDefaultPosition, wxDefaultSize, 512|256|wxSP_LIVE_UPDATE);
	s->Add(splitter, 1, wxEXPAND);
	
	
	wxPanel *top = new wxPanel(splitter, -1);
	//wxPanel *bottom = new wxPanel(splitter, -1);
	wxBoxSizer *st = new wxBoxSizer(wxVERTICAL);
	//wxBoxSizer *sb = new wxBoxSizer(wxVERTICAL);
	top->SetSizer(st);
	//bottom->SetSizer(sb);
	
	//splitter->SplitHorizontally(top,bottom);
	
	//s->Add(top, 1, wxEXPAND);
	//s->Add(bottom, 0, wxEXPAND);
	
	output = new wxTextCtrl(top, -1, wxEmptyString, wxDefaultPosition, wxDefaultSize, wxTE_READONLY | wxTE_MULTILINE);
	input = new wxTextCtrl(top, -1, wxEmptyString, wxDefaultPosition, wxDefaultSize, wxTE_READONLY | wxTE_MULTILINE);
	
	st->Add(output, 1, wxEXPAND);
	st->Add(input, 1, wxEXPAND);
	
//=============================================================================
	
	INPUTCTRL *etc = new INPUTCTRL(splitter, wxID_ANY, wxEmptyString, wxDefaultPosition, wxDefaultSize, wxTE_MULTILINE);
	etc->AutoSetRTL();
	
	#ifdef TEST
	    etc->SetStuff(&encoder, &converter, output, input);
	#endif
	
	splitter->RegisterExpando(etc);
	
	//etc->SetRTF(L"{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1033{\\fonttbl{\\f0\\fswiss\\fcharset0 Segoe UI;}}\r\n{\\colortbl ;\\red0\\green0\\blue0;\\red255\\green255\\blue255;}\r\n{\\*\\generator Msftedit 5.41.21.2509;}\\viewkind4\\uc1\\pard\\cf1\\highlight2\\f0\\fs18 test \\b bold\\b0 \\i italic\\i0 \\b\\i bolditalic\\b0 \\ul italicunderline\\i0 \\b underline bold\\par\r\n}\r\n");
	
	DebugBar *debugbar = new DebugBar(top,-1,etc);
    ToolBar *toolbar = new ToolBar(top, -1, etc);
    
    st->Add(debugbar, 0, wxEXPAND);
    st->Add(toolbar, 0, wxEXPAND);
	//sb->Add(etc, 0, wxEXPAND);
	
	//wxFont font(22, wxFONTFAMILY_DEFAULT, wxFONTSTYLE_NORMAL, wxFONTWEIGHT_NORMAL, false, L"Segoe UI");
	//wxTextAttr attr(wxColor(255,0,255), *wxWHITE, font);
	
	wxFont font(22, wxFONTFAMILY_DEFAULT, wxFONTSTYLE_NORMAL, wxFONTWEIGHT_BOLD, true, L"Comic Sans MS");
	wxTextAttr attr(wxColor(255,0,255), wxColor(0,255,255), font);
	
	etc->SetStyle(0, 0, attr);
	
#if USEEXPANDO
	etc->SetMaxHeight(100);
#else
    etc->SetMinSize(wxSize(etc->GetMinSize().GetX(), 60));
#endif //USEEXPANDO

    //etc->SetBackgroundColour(wxColor(255,255,0));

    
    frame->Layout();
    //top->Layout();
    //bottom->Layout();
    splitter->SplitHorizontally(top,etc);
	frame->Show(true);
	app->SetTopWindow(frame);
	
	
	wxExpandEvent evt(wxEVT_ETC_LAYOUT_NEEDED, etc->GetId());
    evt.SetEventObject(etc);
    evt.height = etc->GetMinSize().GetHeight();
    evt.numLines = etc->GetNumberOfLines();
    etc->GetEventHandler()->ProcessEvent(evt);
	
	
	etc->SetFocus();
}
	
bool ExpandoApp::OnInit(){
	   
    #if DBG_CONSOLE
        AllocConsole();
        freopen("CONIN$",  "rb", stdin);
        freopen("CONOUT$", "wb", stdout);
        freopen("CONOUT$", "wb", stderr);
    #endif
    
    CreateTestWindow(this, L"Test");
    
	return true;
}

IMPLEMENT_APP(ExpandoApp)

