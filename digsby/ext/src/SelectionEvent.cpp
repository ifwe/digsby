#include "SelectionEvent.h"

DEFINE_EVENT_TYPE(wxEVT_SELECTION_CHANGED);
IMPLEMENT_DYNAMIC_CLASS(wxSelectionEvent, wxEvent)

wxSelectionEvent::wxSelectionEvent(WXTYPE commandEventType, int id, long selectionStart, long selectionEnd) : wxCommandEvent(commandEventType, id){
    this->selectionStart = selectionStart;
    this->selectionEnd = selectionEnd == -1? selectionStart : selectionEnd;
}
 
wxSelectionEvent::wxSelectionEvent(const wxSelectionEvent &event) : wxCommandEvent(event){
    this->selectionStart = event.selectionStart;
    this->selectionEnd = event.selectionEnd;
}