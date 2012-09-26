#include "ExpandEvent.h"

DEFINE_EVENT_TYPE(wxEVT_ETC_LAYOUT_NEEDED);
IMPLEMENT_DYNAMIC_CLASS(wxExpandEvent, wxEvent)

wxExpandEvent::wxExpandEvent(WXTYPE commandEventType, int id) : wxCommandEvent(commandEventType, id){
}
 
wxExpandEvent::wxExpandEvent(const wxExpandEvent &event) : wxCommandEvent(event){
}
