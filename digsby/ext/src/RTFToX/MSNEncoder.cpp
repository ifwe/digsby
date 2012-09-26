#include "MSNEncoder.h"

MarkupDesc*
MSNEncoder::GetMarkup(const StyleDesc& styleDesc, unsigned char dirtyMask, bool base) const{
    //"X-MMS-IM-Format: FN=%s; EF=%s; CO=%s; CS=%d; PF=%sd"
    MarkupDesc *md = new MarkupDesc;
    
    if(!base)
        return md;
    
    wxString formatString(L"X-MMS-IM-Format:");
    
    if(dirtyMask & STYLEFONT)
        //TODO: Set CS to Character Set and PF to Font Family
        formatString.Append(wxString::Format(L" FN=%s; CS=%d; PF=%d", URLEncode(styleDesc.font->name), 0, 22));
    
    if(dirtyMask & (STYLEBOLD | STYLEITAL | STYLEUNDL))
        formatString << L"; EF=" << wxString::Format(L"%s%s%s",
            styleDesc.styleflags & STYLEBOLD ? L"B" : L"",
            styleDesc.styleflags & STYLEITAL ? L"I" : L"",
            styleDesc.styleflags & STYLEUNDL ? L"U" : L"");
    
    if(dirtyMask & STYLECOLOR)
        formatString << L"; CO=" << wxString::Format(L"%s", styleDesc.color->ToHex(L"bgr"));
    
    formatString.Append(L"\r\n\r\n");
    
    md->initmarkup = formatString;
    md->formatMask = dirtyMask;
    
    return md;
}

wxString
MSNEncoder::FormatString(const wxString& originalString) const{
    return originalString;
}

wxString
MSNEncoder::FormatLink(const wxString& target, const wxString& text) const{
    return FormatString(wxString::Format(L"%s(%s)", text, target));
}

wxString
MSNEncoder::GetHeader() const{
    return wxString(L"MIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\n");
}

wxString
MSNEncoder::GetFooter() const{
    return wxEmptyString;
}

unsigned int
MSNEncoder::GetTerminalFlags(const StyleDesc& /*styleDesc*/, unsigned char /*dirtyMask*/) const{
    return 0;
}

wxString
MSNEncoder::FormatUnicodeChar(unsigned long unichar) const{
    return wxString::Format(L"%c", unichar);
}
