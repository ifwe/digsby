#include "ExpandoTextCtrl.h"


ExpandoTextCtrl::ExpandoTextCtrl(wxWindow *parent,
                                 wxWindowID id,
                                 const wxString &value,
                                 const wxPoint &pos,
                                 const wxSize &size,
                                 long  style,
                                 const wxValidator &validator,
                                 const wxString &name)
        : InputBox(parent, id, value, pos, size, style | wxTE_MULTILINE, validator, name){
    
    //Setting up defaults
    maxHeight = -1;
    minHeight = -1;
 

#if __WXMSW__
    //Hide Vertical Scrollbar
    SendMessage(GetHwnd(), EM_SHOWSCROLLBAR, SB_VERT, FALSE);
#endif
    
    //Figure out the size of the expando
    RequestResize();
}

bool
ExpandoTextCtrl::SetStyle(long start, long end, const wxTextAttr &style){
    
    bool success = InputBox::SetStyle(start, end, style);
    
    //Force resize check
    RequestResize();
    
    return success;
}



//Set a MinHeight so that the Expando won't get any shorter than this
void ExpandoTextCtrl::SetMinHeight(const int &h){
    if(minHeight != h){
        minHeight = h;
        RequestResize();
    }
        
}

int ExpandoTextCtrl::GetMinHeight() const {
    return minHeight;
}

//Set a a MaxHeight so that the Expando won't get any taller than this
void ExpandoTextCtrl::SetMaxHeight(const int &h){
    maxHeight = h;
    if(GetSize().GetHeight() > maxHeight){
        RequestResize();
    }
}

int ExpandoTextCtrl::GetMaxHeight() const {
    return maxHeight;
}

int ExpandoTextCtrl::GetDecHeight() const {
    return decHeight;
}

int ExpandoTextCtrl::GetNatHeight() const{

#ifdef __WXMSW__
    return wxMin(reqHeight, maxHeight);
#else
    return GetBestSize().y;
#endif
    
}

//force the expando to through a EN_REQUESTRESIZE notification
void ExpandoTextCtrl::RequestResize(){
#if __WXMSW__
     SendMessage(GetHwnd(), EM_REQUESTRESIZE, 0, 0);
#endif
}

#ifdef __WXMSW__
#define EXTRA_TEXTCTRL_PIXELS 8 //Magic number!? Why 8? What determines this?
#else
#define EXTRA_TEXTCTRL_PIXELS 0
#endif

#if __WXMSW__
//hook into the notify message callback to add EN_REQUESTRESIZE handling
bool ExpandoTextCtrl::MSWOnNotify(int idCtrl, WXLPARAM lParam, WXLPARAM *result){
    NMHDR *hdr = (NMHDR*)lParam;
    
    if(hdr->code == EN_REQUESTRESIZE){
        //Resize event!
        REQRESIZE *rrStruct = (REQRESIZE*)lParam;

        reqHeight = rrStruct->rc.bottom - rrStruct->rc.top + EXTRA_TEXTCTRL_PIXELS;

        AdjustCtrl(reqHeight);
        
        return true;
    }
    
    
    return InputBox::MSWOnNotify(idCtrl, lParam, result);
}
#endif

//Resize logics
void ExpandoTextCtrl::AdjustCtrl(long newHeight){

    //If the required height is more than the maxHieght, decrease it to that
    if(maxHeight != -1 && newHeight > maxHeight){
            newHeight = maxHeight;
    }

    //If the required height is less than the minHieght, increase it to that
    if(minHeight != -1 && newHeight < minHeight){
            newHeight = minHeight;
    }
    
    decHeight = newHeight;
    
    SetMinSize(wxSize(GetMinSize().GetWidth(), newHeight));
    
    //If requested height between min and max height, resize the Expando       
    if(newHeight != GetSize().GetHeight()){
        
        bool hasSizer = GetContainingSizer() != NULL;
            
        if(!hasSizer){
            SetSize(GetSize().GetWidth(), newHeight);
        }
    
        //Throw a LayoutNeeded Event
        wxExpandEvent evt(wxEVT_ETC_LAYOUT_NEEDED, GetId());
        evt.SetEventObject(this);
        evt.height = newHeight;
        evt.numLines = GetNumberOfLines();
        GetEventHandler()->ProcessEvent(evt);
    }
}