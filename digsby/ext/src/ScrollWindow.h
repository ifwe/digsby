/**
  ScrollWindow.h
  
  Like wxScrolledWindow, except uses the pixel vaulues set by
  wxWindow::SetVirtualSize as the only units to scroll by.
*/

#ifndef _SCROLLWINDOW_INCLUDED__H_
#define _SCROLLWINDOW_INCLUDED__H_

#include "wx/wxprec.h"
#ifndef WX_PRECOMP
#include "wx/wx.h"
#endif


class SkinScrollWindow : public wxWindow {
public:
	SkinScrollWindow(wxWindow* parent, wxWindowID = -1, int style = wxBORDER_NONE);
	virtual ~SkinScrollWindow();

	void AdjustScrollbars(int x = -1, int y = -1);
	void PrepareDC(wxDC& dc);

    void Scroll(int x, int y);
	void EnablePhysicalScrolling(bool enable);
	bool IsPhysicalScrollingEnabled() const { return physicalScrolling; }
	
	void SetVirtualSize(const wxSize& size);
	void SetVirtualSize(int width, int height);
	
	int GetViewStart() const;
	wxRect GetViewRect() const;
	

	bool CanSmoothScroll() const
	{
#ifdef __WXMSW__
		return true;
#else
		return false;
#endif
	}

	bool SetSmoothScrolling(bool useSmooth)
	{
#ifdef __WXMSW__
		return smoothScroll = useSmooth;
#else
		return false;
#endif
	}
	
#ifdef __WXMSW__
	void ScrollWindow(int dx, int dy, const wxRect* prect = NULL);
#endif

#ifndef SWIG
protected:
	bool physicalScrolling;
	bool smoothScroll;

	// event handling callbacks.
    void OnScroll(wxScrollWinEvent& event);
	virtual void OnHandleScroll(wxScrollWinEvent& event);
	
	void OnSize(wxSizeEvent& event);
	void OnMouseWheel(wxMouseEvent& event);

    DECLARE_CLASS(SkinScrollWindow)
	DECLARE_EVENT_TABLE()
#endif
	    
};

#endif
