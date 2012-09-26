#ifndef _EXPAND_EVENT_
#define _EXPAND_EVENT_

#include "wx/Event.h"

DECLARE_EVENT_TYPE(wxEVT_ETC_LAYOUT_NEEDED, 7777)

#define EVT_ETC_LAYOUT_NEEDED(fn) \
	DECLARE_EVENT_TABLE_ENTRY( wxEVT_ETC_LAYOUT_NEEDED, wxID_ANY, wxID_ANY, \
	(wxObjectEventFunction)(wxEventFunction)(wxCommandEventFunction)&fn, (wxObject*) NULL ),

class wxExpandEvent : public wxCommandEvent{
    public:
        wxExpandEvent(WXTYPE commandEventType = 0, int id = 0);
	    wxExpandEvent( const wxExpandEvent &event );

        virtual wxEvent *Clone() const { return new wxExpandEvent(*this); }
        int height;
        int numLines;

        DECLARE_DYNAMIC_CLASS(wxExpandEvent)
};


#endif