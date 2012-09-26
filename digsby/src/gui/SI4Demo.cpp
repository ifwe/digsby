#include ".\si4demo.h"
#include ".\SplitImage4.h"
#include "wx/sysopt.h"

IMPLEMENT_APP(SI4Demo)

bool SI4Demo::OnInit(){
	wxInitAllImageHandlers();
	Frame* f = new Frame(_T("Test"),wxPoint(50,50),wxSize(800,800));
	f->Show(TRUE);
	SetTopWindow(f);
	return TRUE;
}

ImageData MakeImageData(){
	
	ImageData idata;

	idata.x1=30;
	idata.x2=-30;
	idata.y1=30;
	idata.y2=-30;
	idata.source= wxT("digsbybig.png");

	Region* reg[]={&idata.center,&idata.top,&idata.right,&idata.bottom,&idata.left};
	
	reg[0]->offset=wxPoint(0,0);
	reg[0]->hstyle=1;
	reg[0]->vstyle=1;
	reg[0]->align = wxALIGN_CENTER_HORIZONTAL|wxALIGN_CENTER_VERTICAL;//wxALIGN_LEFT | wxALIGN_TOP;//wxALIGN_RIGHT | wxALIGN_BOTTOM;//
	reg[0]->extends.down=false;
	reg[0]->extends.left=false;
	reg[0]->extends.right=false;
	reg[0]->extends.up=false;

	for(int i=1;i<5;++i){
		reg[i]->offset=wxPoint(0,0);
		reg[i]->hstyle=1;
		reg[i]->vstyle=1;
		reg[i]->align = wxALIGN_TOP|wxALIGN_LEFT;
		bool* ext[]={&reg[i]->extends.down,&reg[i]->extends.left,&reg[i]->extends.right,&reg[i]->extends.up};
		for(int n=0;n<4;++n){
			*ext[n]=false;
		}
	}

	return idata;

}

Frame::Frame(const wxString& title, const wxPoint& pos, const wxSize& size)
:wxFrame((wxFrame*)NULL,-1,title,pos,size){

	//InitConsole(this,console);
	wxMenu* menuFile  = new wxMenu;

	menuFile->Append(ID_About,_T("&About..."));
	menuFile->AppendSeparator();
	menuFile->Append(ID_Quit,_T("E&xit"));

	wxMenuBar* menuBar = new wxMenuBar;
	menuBar->Append(menuFile, _T("&File"));

	SetMenuBar(menuBar);

	CreateStatusBar();
	SetStatusText(_T("Welcome to my Nightmare"));

	Connect(ID_About,wxEVT_COMMAND_MENU_SELECTED,wxCommandEventHandler(Frame::OnQuit));
	Connect(ID_About,wxEVT_COMMAND_MENU_SELECTED,wxCommandEventHandler(Frame::OnAbout));
	Connect(wxEVT_PAINT,wxPaintEventHandler(Frame::OnPaint));
	Connect(wxEVT_ERASE_BACKGROUND,wxEraseEventHandler(Frame::OnBG));
	Connect(wxEVT_SIZE,wxSizeEventHandler(Frame::OnSize));
	
	ImageData idata=MakeImageData();
	
	si4= new SplitImage4(idata);
	//idata.source=_("menubgofulyness.png");
	//si4_2 = new SplitImage4(idata);

	//digsby =new wxBitmap(_("digsbybig.png"),wxBITMAP_TYPE_ANY);

}
Frame::~Frame(){
	delete si4;
}

void Frame::OnQuit(wxCommandEvent& WXUNUSED(event)){
	Close(TRUE);
}

void Frame::OnAbout(wxCommandEvent& WXUNUSED(event)){
	wxMessageBox(_T("This is a wxWidgets Hello world sample"),_T("About Hello World"),wxOK | wxICON_INFORMATION, this);
}

void Frame::OnSize(wxSizeEvent& event){
	event.Skip();
	Refresh();
}

void Frame::OnPaint(wxPaintEvent& event){
	wxBufferedPaintDC dc(this);
	wxRect rect=wxRect(GetSize());
	dc.SetBrush(*wxRED_BRUSH);
	dc.DrawRectangle(rect);
	//si4->Draw(&dc,rect.Deflate(100,100));
	//dc.DrawBitmap(si4_2->GetBitmap(rect.GetSize()),100,100);
	
	si4->Draw(&dc,rect.Deflate(100,100));
	//dc.DrawBitmap(si4_2->GetBitmap(rect.Deflate(200,200).GetSize()),GetSize().x/3,GetSize().y/3);

}

void Frame::OnBG(wxEraseEvent &event){}
