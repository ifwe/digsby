class InputBox : wxTextCtrl
{

%TypeHeaderCode
#include "InputBox.h"
%End

public:
    void ShowDefaultColors();
    bool SetDefaultColors(const wxColour& fg, const wxColour& bg);

    //InputBox() /Transfer/;
    InputBox(wxWindow* parent, wxWindowID id = wxID_ANY,
             const wxString& value = wxEmptyString,
             const wxPoint& pos = wxDefaultPosition,
             const wxSize& size = wxDefaultSize,
             long style = 0,
             const wxValidator& validator = wxDefaultValidator,
             const wxString& name = wxTextCtrlNameStr) /Transfer/;

    virtual ~InputBox();

    virtual bool CanPaste() const;
	
	virtual wxString GetValue();

    bool SetStyle(long start, long end, const wxTextAttr& style);
    bool GetStyle(long position, wxTextAttr &style /Out/);

    bool SetRTL(bool rtl);
    bool GetRTL();

    int  GetReqHeight() const;
    int  GetNatHeight() const;

    wxString GetRTF();
    void SetRTF(const wxString& rtf);

    bool AutoSetRTL();

private:
    InputBox(const InputBox&);
};

//bool TextCtrlAutoComplete(wxTextCtrl* ctrl, const wxArrayString& choices);

