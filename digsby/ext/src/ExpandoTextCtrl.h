#ifndef _EXPANDOTEXTCTRL_H_
#define _EXPANDOTEXTCTRL_H_

#include "InputBox.h"

#include "ExpandEvent.h"

#include "wx/TextCtrl.h"
#include "wx/Event.h"
#include "wx/Sizer.h"
#include "wx/String.h"

#if __WXMSW__
#include <windowsx.h>

#include "wx/msw/private.h"
#include "wx/msw/winundef.h"
#include "wx/msw/mslu.h"

#include "windows.h"

#include "RichEdit.h"
#endif

/**
 * ExpandoTextCtrl is a wxTextCtrl that automatically resizes itself within limitations to fit it's text
 */
class ExpandoTextCtrl : public InputBox{

    private:
        int maxHeight;
        int minHeight;
        int decHeight;
    
    public:
        ExpandoTextCtrl(wxWindow *parent, wxWindowID id = wxID_ANY,
                        const wxString &value = wxEmptyString,
                        const wxPoint &pos = wxDefaultPosition,
                        const wxSize &size = wxDefaultSize,
                        long  style = 0,
                        const wxValidator& validator = wxDefaultValidator,
                        const wxString& name = wxTextCtrlNameStr);
                        
        
        bool SetStyle(long start, long end, const wxTextAttr& style);
        void SetMinHeight(const int &h);
        int  GetMinHeight() const;
        void SetMaxHeight(const int &h);
        int  GetMaxHeight() const;
        int  GetDecHeight() const;
        int  GetNatHeight() const;
        void RequestResize();
#if __WXMSW__
        bool MSWOnNotify(int idCtrl, WXLPARAM lParam, WXLPARAM *result);
#endif
        void AdjustCtrl(long height);
        

        
};

#endif
