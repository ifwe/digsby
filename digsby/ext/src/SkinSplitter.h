#ifndef _SKINSPLITTER_H_
#define _SKINSPLITTER_H_

#include <wx/splitter.h>
#include <wx/brush.h>
#include "Python.h"

enum SplitterStates {
	NORMAL = 0,
	ACTIVE = 1,
	HOVER  = 2
};

class SkinSplitter : public wxSplitterWindow {
public:
#if SWIG
    %pythonAppend SkinSplitter "self._setOORInfo(self)"
#endif
	SkinSplitter(wxWindow* parent, long style = wxSP_LIVE_UPDATE | wxNO_BORDER);
	virtual ~SkinSplitter();

	// Set/get the color of the splitter.
	void     SetSplitterColors(const wxColour& normal, const wxColour& active, const wxColour& hover);

	// Set/get native mode
	void SetNative(bool native);
	bool GetNative() const;

protected:
	bool     native;
	wxBrush  brushes[3];

	void DrawSash(wxDC& dc);
	void RedrawSplitter(bool isHot);

	void OnEnterSash();
	void OnLeaveSash();

	void OnLeftDown(wxMouseEvent& event);
	void OnDoubleClick(wxSplitterEvent& event);

#ifndef SWIG
	DECLARE_EVENT_TABLE()
#endif
};

#endif
