#ifndef _SELECTION_CHANGED_EVENT_
#define _SELECTION_CHANGED_EVENT_

#include "wx/Event.h"

DECLARE_EVENT_TYPE(wxEVT_SELECTION_CHANGED, 7778)

#define EVT_SELECTION_CHANGED(fn) \
	DECLARE_EVENT_TABLE_ENTRY( wxEVT_SELECTION_CHANGED, wxID_ANY, wxID_ANY, \
	(wxObjectEventFunction)(wxEventFunction)(wxCommandEventFunction)&fn, (wxObject*) NULL ),

class wxSelectionEvent : public wxCommandEvent{
    public:
        wxSelectionEvent(WXTYPE commandEventType = 0, int id = 0, long selectionStart = 0, long selectionEnd = -1);
	    wxSelectionEvent( const wxSelectionEvent &event );

        virtual wxEvent *Clone() const { return new wxSelectionEvent(*this); }
        
        long selectionStart;
        long selectionEnd;

        DECLARE_DYNAMIC_CLASS(wxSelectionEvent)
};


#endif //_SELECTION_CHANGED_EVENT_