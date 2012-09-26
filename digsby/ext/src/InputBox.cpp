#include "InputBox.h"
#include "ctextutil.h"

#include <wx/clipbrd.h>

InputBox::InputBox(wxWindow* parent, wxWindowID id, const wxString& value,
                   const wxPoint& pos, const wxSize& size, long style,
                   const wxValidator& validator, const wxString& name)
                  : wxTextCtrl(parent, id, value, pos, size, style | wxTE_RICH2, validator, name),
                    settingStyle(false), gettingStyle(false), inSelection(false){
    
    lastLayout = 0;
    GetCurrentStyle()->SetFont(wxSystemSettings::GetFont(wxSYS_DEFAULT_GUI_FONT));
    GetCurrentStyle()->SetTextColour(*wxBLACK);
    GetCurrentStyle()->SetBackgroundColour(*wxWHITE);
    SetStyle(GetInsertionPoint(), GetInsertionPoint(), *GetCurrentStyle());
    
    Connect(wxEVT_COMMAND_TEXT_UPDATED, wxCommandEventHandler(InputBox::OnTextChanged));
    Connect(wxEVT_KEY_DOWN, wxKeyEventHandler(InputBox::OnKey));
    Connect(wxEVT_COMMAND_TEXT_PASTE, wxCommandEventHandler(InputBox::OnPaste));
    Connect(wxEVT_SET_FOCUS, wxFocusEventHandler(InputBox::OnFocus));

#ifdef __WXMSW__
    //Tell Windows we want EN_REQUESTRESIZE events for this textctrl
    LPARAM mask = SendMessage(GetHwnd(), EM_GETEVENTMASK, 0, 0);
    SendMessage(GetHwnd(), EM_SETEVENTMASK, 0, mask | ENM_REQUESTRESIZE | ENM_SELCHANGE);
#endif
}

#ifdef __WXMSW__
#define WXC2CR(c) RGB(c.Red(), c.Green(), c.Blue())
#endif

bool InputBox::SetDefaultColors(const wxColor& fg, const wxColor& bg) {
#ifdef __WXMSW__
    //printf("SetDefaultColors\n");
    CHARFORMAT2 cf;
    cf.cbSize = sizeof(CHARFORMAT2);
    cf.dwMask = CFM_COLOR | CFM_BACKCOLOR;
    cf.crTextColor = WXC2CR(fg);
    cf.crBackColor = WXC2CR(bg);
    return 0 != ::SendMessage(GetHwnd(), EM_SETCHARFORMAT, SCF_DEFAULT, (LPARAM)&cf);
#endif
    return false;
}

void InputBox::ShowDefaultColors() {
#ifdef __WXMSW__
    CHARFORMAT2 cf;
    cf.cbSize = sizeof(CHARFORMAT2);
    ::SendMessage(GetHwnd(), EM_GETCHARFORMAT, SCF_DEFAULT, (LPARAM)&cf);
    printf("fore: %s %d %d %d\n",
            (cf.dwMask & CFM_COLOR ? "on" : "off"),
            GetRValue(cf.crTextColor),
            GetGValue(cf.crTextColor),
            GetBValue(cf.crTextColor));

    printf("back: %s %d %d %d\n",
            (cf.dwMask & CFM_BACKCOLOR ? "on" : "off"),
            GetRValue(cf.crBackColor),
            GetGValue(cf.crBackColor),
            GetBValue(cf.crBackColor));
#endif
}


//Intercepts SetStyle() calls to premptivly handle newline sizes and to force a resize on set
bool
InputBox::SetStyle(long start, long end, const wxTextAttr &style){

    settingStyle = true;
    
    wxTextAttr workingStyle(style);
    
    
    
    //long i = GetInsertionPoint();
    //wxString temp = GetRTF();
    if(IsEmpty()){
    
    
        if(style.HasFont()){
            //fixes the height of the cursor when in empty fields
            SetFont(style.GetFont());
        }
        
        //printf("Atter Has: %s %s\n\n", workingStyle.HasTextColour()? "TextColour" : "", workingStyle.HasBackgroundColour()? "BGColor" : "");
       
        SetDefaultColors(workingStyle.HasTextColour()?       workingStyle.GetTextColour()       : GetCurrentStyle()->GetTextColour(),
                         workingStyle.HasBackgroundColour()? workingStyle.GetBackgroundColour() : GetCurrentStyle()->GetBackgroundColour());
    }
    
    //SetRTF(temp);
    //SetInsertionPoint(i);
    
    //Actually set the style
    bool success = wxTextCtrl::SetStyle(start, end, workingStyle);

    GetStyle(GetInsertionPoint(), *GetCurrentStyle());
    
    settingStyle = false;
    
    return success;
}

bool
InputBox::GetStyle(long position, wxTextAttr &style){
    
    gettingStyle = true;
    bool success = wxTextCtrl::GetStyle(position, style);
    gettingStyle = false;
    
    return success;
}

int
InputBox::GetReqHeight() const {
#ifdef __WXMSW__
    return reqHeight;
#else
    return GetBestSize().y;
#endif
}

int
InputBox::GetNatHeight() const{
#ifdef __WXMSW__
    return reqHeight;
#else
    return GetBestSize().y;
#endif
}


//Prevents resetting the font when the text is cleared
void
InputBox::OnTextChanged(wxCommandEvent &event){
    if(!settingStyle && IsEmpty()){
    
        //This fixes the height of the cursor in empty fields
        SetFont(GetCurrentStyle()->GetFont());
        
        //text has been cleared, restore formatting
        SetDefaultStyle(*GetCurrentStyle());
        
    }
    
    event.Skip();
}

void
InputBox::OnFocus(wxFocusEvent &event){
    event.Skip();
    if(!HasSelection()){
        long ip = GetInsertionPoint();
        SetStyle(ip, ip, *GetCurrentStyle());
    }
}

bool
InputBox::AutoSetRTL(){
#ifdef __WXMSW__
    bool isRTL = IsRTLLang(GetKeyboardLayout(0));
    if(isRTL != GetRTL()) {
        return SetRTL(isRTL);
    }
    
    return true;
#else
    return false;
#endif
}

bool
InputBox::SetRTL(bool rtl){
#ifdef __WXMSW__
    settingStyle = true;
    
    PARAFORMAT2 pf;
    pf.cbSize = sizeof(pf);
    
    pf.dwMask = PFM_RTLPARA;
    pf.wEffects = rtl? PFE_RTLPARA : 0;
    
    int success = SendMessage(GetHwnd(), EM_SETPARAFORMAT, 0, (LPARAM)&pf);
    //printf("set: %d\n", success);
    
    settingStyle = false;
    
    return success != 0;
#else
    return false;
#endif
}

bool
InputBox::GetRTL(){
#ifdef __WXMSW__
    PARAFORMAT2 pf;
    pf.cbSize = sizeof(pf);
    
    SendMessage(GetHwnd(), EM_GETPARAFORMAT, 0, (LPARAM)&pf);
    
    return pf.wAlignment == PFA_RIGHT;
#else
    return false;
#endif
}

void
InputBox::Clear(){
    if(!IsEmpty()){
#ifdef __WXMSW__
        HKL hkl = GetKeyboardLayout(0);
#endif
        wxTextCtrl::Clear();
#ifdef __WXMSW__
        ActivateKeyboardLayout(hkl,0);
#endif
    }
}

void
InputBox::OnKey(wxKeyEvent &event){

    int keyCode = event.GetKeyCode();

    // Shift+Insert is apparently paste from clipboard but doesn't throw a paste event, does now
    if(keyCode == WXK_INSERT && event.ShiftDown()) {
        Paste();
        return;
    }
    
    if(keyCode == WXK_DELETE || keyCode == WXK_BACK){
        if(keyCode == WXK_DELETE && !HasSelection() && GetInsertionPoint() == GetLastPosition()){
            return;
        }else if(HasSelection()){
            long start = 0;
            long end = 0;
            GetSelection(&start, &end);
            if(start == 0 && end >= GetLastPosition()){
                if(keyCode == WXK_DELETE && event.ShiftDown()){
                    Copy();
                }
                Clear();
                return;
            }
        }
    }
    
#ifdef TEST
    if(keyCode == WXK_RETURN && event.GetModifiers() != wxMOD_SHIFT){
        wxString rtf = GetRTF();
        output->SetValue(converter->Convert(rtf, *encoder));
        input->SetValue(rtf);
        Clear();
        SetFocus();
        return;
    }//else if(event.GetKeyCode() == WXK_RETURN && event.GetModifiers() == wxMOD_SHIFT){
    //    Replace(GetInsertionPoint(), GetInsertionPoint(), L"\n");
    //    return;
    //}
#endif //TEST
    
    
    event.Skip();
    
}

void
InputBox::OnPaste(wxCommandEvent &event){

    if (wxTheClipboard->Open()){
        
        //Insure that pasting text strips formating and extra newlines
        if (wxTheClipboard->IsSupported( wxDF_TEXT )){
        
            wxTextDataObject data;
            wxTheClipboard->GetData(data);
            wxString text = data.GetText();
            
            wxChar nl(L'\n');
            if(text.EndsWith(&nl)){
                text = text.Trim();
            }
            
            WriteText(text);
            
            wxTheClipboard->Close();
            
            return;
            
        }  
        
        wxTheClipboard->Close();
    }
    
    event.Skip();

    
}

wxTextAttr*
InputBox::GetCurrentStyle(){
#if __WXMSW__
    long kbLayout = (long)GetKeyboardLayout(0);
    
    //long long id = 0;

    //id = (long long)GetId() << 32 | kbLayout;
    
    //printf("\n===StyleMap=========\n");
    //for(map<long long, wxTextAttr>::iterator it = styleMap.begin(); it != styleMap.end(); it++){
    //    printf("ID: %016llx\n", it->first);
    //    PrintTextAttr(it->second);
    //}
    //printf("====================\n\n\n");
    //
    //if(!styleMap.count(id)){
    //    if(!styleMap.count(kbLayout)){
    //        printf("Create: %016x\n", kbLayout);
    //        return &styleMap[kbLayout];
    //    }
    //    
    //    styleMap[id] = styleMap[kbLayout];
    //    
    //    printf("Create: %016llx : %s\n", id, styleMap[id].GetFont().GetFaceName().ToAscii());
    //}else{
    //    styleMap[kbLayout] = styleMap[id];
    //    printf("Return: %016llx : %s\n", id, styleMap[id].GetFont().GetFaceName().ToAscii());
    //}
    
    if(kbLayout != lastLayout){
        if(!styleMap.count(kbLayout)){
            styleMap[kbLayout] = styleMap[lastLayout];
        }else{
            styleMap[kbLayout].SetTextColour(styleMap[lastLayout].GetTextColour());
            styleMap[kbLayout].SetBackgroundColour(styleMap[lastLayout].GetBackgroundColour());
        }
    }
    
    lastLayout = kbLayout;
    return &styleMap[kbLayout];
#else
    return const_cast<wxTextAttr*>(&GetDefaultStyle());
#endif
}


#ifdef __WXMSW__
bool
InputBox::MSWOnNotify(int idCtrl, WXLPARAM lParam, WXLPARAM *result){

    NMHDR *hdr = (NMHDR*)lParam;
    
    if(hdr->code == EN_REQUESTRESIZE){
        //Resize event!
        
        
        REQRESIZE *rrStruct = (REQRESIZE*)lParam;
        reqHeight = rrStruct->rc.bottom - rrStruct->rc.top + 8; //Magic number!? Why 8? What determines this?
        
        return true;
        
    }else if(hdr->code == EN_SELCHANGE && !gettingStyle && !inSelection){
    
        Freeze();
        inSelection = true;
    
        //Selection or cursor position changed
        SELCHANGE *scStruct = (SELCHANGE*)lParam;
        
        //If text and no selection
        if(!IsEmpty() && scStruct->chrg.cpMin == scStruct->chrg.cpMax){
            //save the new current style
            GetStyle(GetInsertionPoint(), *GetCurrentStyle());
            
#ifdef TEST
            //printf("IsEmpty? %s with value \"%s\"\n", IsEmpty()? "Yes" : "No", GetValue().ToAscii());
            //printf("GotStyle at %d of %d\n", GetInsertionPoint(), GetLastPosition());
            //PrintTextAttr(*GetCurrentStyle());
            //printf("\n\n");
#endif //TEST

        }
        
        long end = GetLastPosition();
        
        if(scStruct->chrg.cpMax > end){
            SetStyle(end, end+1, *GetCurrentStyle());
        }
        
        wxSelectionEvent evt(wxEVT_SELECTION_CHANGED, GetId(), scStruct->chrg.cpMin, scStruct->chrg.cpMax);
        evt.SetEventObject(this);
        GetEventHandler()->ProcessEvent(evt);
        
        inSelection = false;
        Thaw();
    }
    
    return wxTextCtrl::MSWOnNotify(idCtrl, lParam, result);
    
}

WXLRESULT
InputBox::MSWWindowProc(WXUINT nMsg, WXWPARAM wParam, WXLPARAM lParam){
    
    if(nMsg == WM_INPUTLANGCHANGE){
        if(styleMap.count((long)GetKeyboardLayout(0))){
            SetStyle(GetInsertionPoint(), GetInsertionPoint(), *GetCurrentStyle());
        }
        return 1;
    }
    
    return wxTextCtrl::MSWWindowProc(nMsg, wParam, lParam);
    
}

//Callback used to pull the RTF from the richedit
static DWORD CALLBACK EditStreamOutCallback(DWORD_PTR dwCookie, LPBYTE pbBuff, LONG cb, LONG *pcb){
    
    wxString *rtf = (wxString*)dwCookie; //omnomnom
    rtf->Append(wxString::FromAscii((char*)pbBuff));
    *pcb = cb; //cb is incoming character count, pcb is the number processed
    return 0; //0 for no errors
}

struct editstream_helper { 
    const char* str;
    size_t size;
};

//Callback used to push the RTF to the richedit
static DWORD CALLBACK EditStreamInCallback(DWORD_PTR dwCookie, LPBYTE pbBuff, LONG cb, LONG *pcb){
    editstream_helper* helper = (editstream_helper*)dwCookie;
    size_t bytesToRead = std::min(helper->size, (size_t)cb);
    memcpy(pbBuff, helper->str, bytesToRead);
    *pcb = bytesToRead;

    helper->str += bytesToRead;
    helper->size -= bytesToRead;

    return 0; //0 for no errors
}
#endif //__WXMSW__

//Returns a wxString of the raw RTF
wxString
InputBox::GetRTF() const{
    wxString rtf;
#ifdef __WXMSW__
    EDITSTREAM es;
    es.dwCookie = (DWORD_PTR)&rtf;
    es.pfnCallback = &EditStreamOutCallback;
    
    SendMessage(GetHwnd(), EM_STREAMOUT, SF_RTFNOOBJS|SFF_PLAINRTF, (LPARAM)&es);
#endif
    return rtf;
}

//Set RTF from a wxString
void
InputBox::SetRTF(const wxString& rtf){
#ifdef __WXMSW__
    EDITSTREAM es;
    wxCharBuffer buf(rtf.ToAscii());
    editstream_helper helper = {buf, strlen(buf)};
    es.dwCookie = (DWORD_PTR)&helper;
    es.pfnCallback = &EditStreamInCallback;
    SendMessage(GetHwnd(), EM_STREAMIN, SF_RTFNOOBJS|SFF_PLAINRTF, (LPARAM)&es);
#endif //__WXMSW__
}


void InputBox::Replace(long from, long to, const wxString& value){
    // Don't waste time replacing text with itself. This also stops loss of
    // format when replacing "" with ""
    if(GetRange(from, to) == value)
        return;

    Freeze(); // replace involves selection, which can be visible, so stop painting here
    wxTextCtrl::Replace(from, to, value);
    SetStyle(from, from + value.Len() - 1, *GetCurrentStyle());
    Thaw();
}

void
InputBox::SetValue(const wxString &value){
    //Prevents a loss of format on SetValue
    Replace(0, GetLastPosition(), value);
}

wxString
InputBox::GetValue(){
    wxString val = wxTextCtrl::GetValue();
    val.Replace(L"\x0B", L"\n");
    return val;
}

bool
InputBox::CanPaste() const{
    if (!IsEditable())
        return false;

    bool canPaste = false;
    if (wxTheClipboard->Open()) {
        if (wxTheClipboard->IsSupported(wxDF_TEXT) ||
            wxTheClipboard->IsSupported(wxDF_BITMAP))
            canPaste = true;

        wxTheClipboard->Close();
    }

    return canPaste;
}


InputBox::~InputBox() {}


#ifdef TEST


void InputBox::SetStuff(Encoder *encoder, RTFToX *converter, wxTextCtrl *output, wxTextCtrl *input){
    this->encoder = encoder;
    this->converter = converter;
    this->output = output;
    this->input = input;
}


#endif //TEST
