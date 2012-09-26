%module scrollwindow

%{

#include "wx/wxPython/wxPython.h"
#include "wx/wxPython/pyclasses.h"
#include "scrollwindow.h"

%}

%import typemaps.i
%import my_typemaps.i

%import core.i
%import windows.i

class ScrollWindow : public wxWindow {
public:
	ScrollWindow(wxWindow* parent, wxWindowID = -1);
	virtual ~ScrollWindow();

	void AdjustScrollbars(int x = -1, int y = -1);
	void PrepareDC(wxDC& dc);
	
	void SetVirtualSize(const wxSize& size);
	void SetVirtualSize(int width, int height);
		
protected:
     void handleScrollEvent(wxScrollWinEvent& e);
     
};
