#ifndef __DEMO__
#define __DEMO__

#include "wx/wx.h"
#include "wx/event.h"
#include "wx/dcbuffer.h"
#include "wx/textctrl.h"
#include ".\splitimage4.h"

class SI4Demo: public wxApp{
	virtual bool OnInit();
};

class Frame: public wxFrame{
public:

	SplitImage4 *si4;
	//SplitImage4 *si4_2;

	Frame(const wxString& title, const wxPoint& pos, const wxSize& size);
	~Frame();
	void OnQuit(wxCommandEvent& event);
	void OnAbout(wxCommandEvent& event);
	void OnPaint(wxPaintEvent& event);
	void OnBG(wxEraseEvent &event);
	void OnSize(wxSizeEvent& event);
};

enum{
	ID_About = 1,
	ID_Quit,
};

#endif //__DEMO__