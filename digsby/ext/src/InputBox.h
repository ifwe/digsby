#ifndef _CGUI_INPUTBOX_H_
#define _CGUI_INPUTBOX_H_

#include "wx/TextCtrl.h"
#include "wx/Event.h"
#include "wx/Sizer.h"
#include "wx/String.h"
#include "wx/settings.h"

#include <map>

#ifdef __WXMSW__
#include <windowsx.h>
#include <cstring>

#include "wx/msw/private.h"
#include "wx/msw/winundef.h"
#include "wx/msw/mslu.h"

#include "windows.h"
#include "RichEdit.h"
#endif

#include "SelectionEvent.h"


#ifdef TEST
#include "RTFToX.h"
#include "Encoder.h"
#endif


//static std::map<long long, wxTextAttr> styleMap;

/**
 * The InputBox class extends wxTextCtrl to include the following
 *   - Exposes otherwise inaccessable RTF related interfaces
 *   - Fixes for persistant font style in situtaions that would normally clear them
 *   - Interface for Right-To-Left language support
 *   - Addition of standard but not built in keyboard commands
 *   - Addition of events for situations that wxTwxtCtrl lacked
 */
class InputBox : public wxTextCtrl{
    private:
        void OnTextChanged(wxCommandEvent &event);
        void OnFocus(wxFocusEvent &event);
        
    protected:
        int reqHeight;
        bool gettingStyle;
        bool settingStyle;
        bool inSelection;
        
        long lastLayout;
        
        std::map<long, wxTextAttr> styleMap;
        wxTextAttr* GetCurrentStyle();
        
    public:
        void ShowDefaultColors();
        bool SetDefaultColors(const wxColor&, const wxColor&);

        InputBox(wxWindow* parent, wxWindowID id = wxID_ANY,
                 const wxString& value = wxEmptyString,
                 const wxPoint& pos = wxDefaultPosition,
                 const wxSize& size = wxDefaultSize,
                 long style = 0,
                 const wxValidator& validator = wxDefaultValidator,
                 const wxString& name = wxTextCtrlNameStr);
                 
        virtual bool CanPaste() const;
        
        virtual void SetValue(const wxString &value);
        virtual wxString GetValue();
                 
        bool SetStyle(long start, long end, const wxTextAttr& style);
        bool GetStyle(long position, wxTextAttr &style);
        
        bool AutoSetRTL();
        bool SetRTL(bool rtl);
        bool GetRTL();
        
        int  GetReqHeight() const;
        int  GetNatHeight() const;

#ifdef __WXMSW__
        bool MSWOnNotify(int idCtrl, WXLPARAM lParam, WXLPARAM *result);
        WXLRESULT MSWWindowProc(WXUINT nMsg, WXWPARAM wParam, WXLPARAM lParam);
#endif


        void OnKey(wxKeyEvent &event);
        void OnPaste(wxCommandEvent &event);
        
        
        virtual void Clear();
        virtual void Replace(long from, long to, const wxString& value);

        wxString GetRTF() const;
        void SetRTF(const wxString& rtf);
        
        virtual ~InputBox();
        
#ifdef TEST
        Encoder *encoder;
        RTFToX *converter;
        wxTextCtrl *output;
        wxTextCtrl *input;
        void SetStuff(Encoder *encoder, RTFToX *converter, wxTextCtrl *output, wxTextCtrl *input);
#endif //TEST

        
};


#endif // _CGUI_INPUTBOX_H_

