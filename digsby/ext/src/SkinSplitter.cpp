#include "skinsplitter.h"
#include <wx/renderer.h>
#include <wx/dc.h>
#include <wx/dcclient.h>
#include <stdio.h>

#if WXPY

#else
#include "wx/wxPython/wxPython.h"
#endif

BEGIN_EVENT_TABLE(SkinSplitter, wxSplitterWindow)
    EVT_LEFT_DOWN(SkinSplitter::OnLeftDown)
    EVT_SPLITTER_DCLICK(wxID_ANY, SkinSplitter::OnDoubleClick)
END_EVENT_TABLE()

SkinSplitter::SkinSplitter(wxWindow* parent, long style)
	: wxSplitterWindow(parent, wxID_ANY, wxDefaultPosition, wxDefaultSize, style)
	, native(true)
{
    m_permitUnsplitAlways = false;
}

SkinSplitter::~SkinSplitter() {}

void SkinSplitter::DrawSash(wxDC& dc)
{
    // don't draw sash if we're not split
    if ( m_sashPosition == 0 || !m_windowTwo )
        return;

    // nor if we're configured to not show it
    if ( HasFlag(wxSP_NOSASH) )
        return;

	wxRect rect(GetClientRect());
	int sashSize = GetSashSize();

	if ( m_splitMode == wxSPLIT_VERTICAL ) {
		rect.x = m_sashPosition;
		rect.width = sashSize;
	} else {
		rect.y = m_sashPosition;
		rect.height = sashSize;
	}

	if ( !native ) {
		// not in native mode--draw the rectangle with our splitter brush
		dc.SetPen(*wxTRANSPARENT_PEN);
		dc.SetBrush(brushes[m_isHot ? (wxGetMouseState().LeftDown() ? ACTIVE : HOVER) : NORMAL]);
		dc.DrawRectangle(rect);
	} else {
		// from wx/generic/splitter.cpp
		wxRendererNative::Get().DrawSplitterSash(this, dc, GetClientSize(), m_sashPosition,
									m_splitMode == wxSPLIT_VERTICAL ? wxVERTICAL
																	: wxHORIZONTAL,
									m_isHot ? (int)wxCONTROL_CURRENT : 0);
	}
}

void SkinSplitter::SetSplitterColors(const wxColour& normal, const wxColor& active, const wxColor& hover)
{
	brushes[NORMAL] = wxBrush(normal);
	brushes[ACTIVE] = wxBrush(active);
	brushes[HOVER]  = wxBrush(hover);


	Refresh();
}

void SkinSplitter::SetNative(bool native) {
	this->native = native;
	Refresh();
}

bool SkinSplitter::GetNative() const {
	return native;
}

void SkinSplitter::OnEnterSash()
{
	if ( native ) {
		return wxSplitterWindow::OnEnterSash();
	} else {
		SetResizeCursor();
		RedrawSplitter(true);
	}
}

void SkinSplitter::OnLeaveSash()
{
	if (native) {
		return wxSplitterWindow::OnLeaveSash();
	} else {
		SetCursor(*wxSTANDARD_CURSOR);
		RedrawSplitter(false);
	}
}

void SkinSplitter::RedrawSplitter(bool isHot)
{
	m_isHot = isHot;
#ifndef __WXMAC__
	wxClientDC dc(this);
	DrawSash(dc);
#endif
}

void SkinSplitter::OnLeftDown(wxMouseEvent& event)
{
	event.Skip();

	if (!native) {
		Refresh();
	}
}


void SkinSplitter::OnDoubleClick(wxSplitterEvent& event)
{
    // don't allow double click to unsplit      
    event.Veto();
}
