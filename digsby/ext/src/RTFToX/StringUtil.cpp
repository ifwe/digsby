#include "StringUtil.h"

wxString URLEncode(wxString input){

    wxString output;
    wxString temp;
    wxChar c;

    for(unsigned int i = 0; i < input.Length(); ++i){
        c = input[i];
        if((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')){
            output.Append(c);
        }else if(c < 256){
            temp.Printf(L"%%%02x",c);
            output.Append(temp);
        }else{

            temp.Printf(L"%04x",c);

            for(unsigned int j = 0; j < temp.Length(); j += 2){
                output << L"%" << temp.Mid(j, 2);
            }

        }
    }

    return output;

}

bool HasDigits(const wxString &string){
    for (size_t i = 0; i < string.Len(); i++)
        if (wxIsdigit(string[i]))
            return true;

    return false;
}

bool GetDigits(const wxString &string, wxString &command, wxString &arg){

    unsigned int l = string.Len();
    for(unsigned int i = 0; i < l; ++i){
        if(wxIsdigit(string[i])){

            command = string.Mid(0, i);
            arg = string.Mid(i, l-i);
            return true;
        }
    }

    return false;
}


wxString EscapeUnicode(const wxString &string, wxString (*FormatUnicodeChar)(unsigned long)){

    if(string.IsEmpty()) return string;

    wxString output;
    output.Alloc(string.size());

    for (size_t i = 0; i < string.size(); ++i) {
        wxChar c = string.GetChar(i);
        if (c > 0x80)
            output += FormatUnicodeChar(c);
        else
            output += c;
    }

    return output;
}

wxString HTMLEscapeUnicode(unsigned long unichar){
    return wxString::Format(L"&#%d;", unichar);
}
