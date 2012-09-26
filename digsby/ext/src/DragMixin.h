#ifndef _CGUI_DRAGMIXIN_
#define _CGUI_DRAGMIXIN_

#include <wx/gdicmn.h>
#include <wx/event.h>

//
// use my_window->PushEventHandler(new DragMixin(my_window)) to make a window draggable
//
class DragMixin : public wxEvtHandler
{
public:
    DragMixin(wxWindow* win);
    virtual ~DragMixin();

protected:
    void OnLeftDown(wxMouseEvent&);
    void OnLeftUp(wxMouseEvent&);
    void OnMotion(wxMouseEvent&);
    void OnCaptureLost(wxMouseCaptureLostEvent&);

    wxPoint origin;
    wxWindow* win;

private:
    DECLARE_EVENT_TABLE()
};

#endif // _CGUI_DRAGMIXIN_
