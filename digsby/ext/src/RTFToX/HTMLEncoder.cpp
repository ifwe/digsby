#include "HTMLEncoder.h"

#define STYLEFTAG (STYLEFONT | STYLESIZE | STYLECOLOR | STYLEBGCLR)

//Convert the point size of a font to HTML size
int Point2HTMLSize(int s){
    if (s < 10)
        return 1;
    else if (s < 12)
        return 2;
    else if (s < 14)
        return 3;
    else if (s < 18)
        return 4;
    else if (s < 24)
        return 5;
    else if (s < 36)
        return 6;
    else
        return 7;
}

HTMLEncoder::HTMLEncoder(){
    this->escapeUnicode = false;
}

HTMLEncoder::HTMLEncoder(bool escapeUnicode){
    this->escapeUnicode = escapeUnicode;
}

MarkupDesc*
HTMLEncoder::GetMarkup(const StyleDesc& styleDesc, unsigned char dirtyMask, bool /*base*/) const{
    
    MarkupDesc *md = new MarkupDesc;
    
    MarkupDesc *mdp = md;
    
    unsigned char currentMask = dirtyMask;
    
    if(currentMask & STYLEFTAG){
    
        
        wxString fonttag(L"<FONT");
    
        if(currentMask & STYLEFONT){
            fonttag.Append(wxString::Format(L" FACE=\"%s\"", styleDesc.font->name));
        }
        
        if(currentMask & STYLESIZE){
            fonttag.Append(wxString::Format(L" SIZE=%d", Point2HTMLSize((int)styleDesc.size/2)));
        }
        
        if(currentMask & STYLECOLOR){
            fonttag.Append(wxString::Format(L" COLOR=#%s", styleDesc.color->ToHex()));
        }
        
        if(currentMask & STYLEBGCLR && !styleDesc.bgcolor->IsWhite()){
            fonttag.Append(wxString::Format(L" BACK=#%s", styleDesc.bgcolor->ToHex()));
        }
        
        fonttag.Append(L">");
        
        mdp->initmarkup = fonttag;
        mdp->termmarkup = L"</FONT>";
        mdp->contentflags |= STYLEFTAG;
        mdp->formatMask = currentMask & STYLEFTAG;
        
        currentMask = currentMask & ~STYLEFTAG;
    }
    
    if(currentMask & STYLEITAL && styleDesc.styleflags & STYLEITAL){
        mdp = mdp->NewDesc(L"<I>", L"</I>", STYLEITAL, STYLEITAL);
        currentMask = currentMask & ~STYLEITAL;
    }
    
    if(currentMask & STYLEBOLD && styleDesc.styleflags & STYLEBOLD){
        mdp = mdp->NewDesc(L"<B>", L"</B>", STYLEBOLD, STYLEBOLD);
        currentMask = currentMask & ~STYLEBOLD;
    }
    
    if(currentMask & STYLEUNDL && styleDesc.styleflags & STYLEUNDL){
        mdp = mdp->NewDesc(L"<U>", L"</U>", STYLEUNDL, STYLEUNDL);
        currentMask = currentMask & ~STYLEUNDL;    
    }
    
    return md;
    
}

wxString
HTMLEncoder::FormatString(const wxString& originalString) const{
    wxString workingString(originalString);
    
    workingString.Replace(L"&", L"&amp;");
    workingString.Replace(L"<", L"&lt;");
    workingString.Replace(L">", L"&gt;");
    workingString.Replace(L"\x00A0", L"&nbsp;");
    
    workingString.Replace(L"\n", L"<br />");
    
    if (escapeUnicode)
        workingString = EscapeUnicode(workingString, &HTMLEscapeUnicode);
    
    return workingString;
}

wxString
HTMLEncoder::FormatLink(const wxString& target, const wxString& text) const{
    return wxString::Format(L"<a href=\"%s\">%s</a>", FormatString(target), FormatString(text));
}

wxString
HTMLEncoder::GetHeader() const{
    return L"<HTML><BODY>";
}

wxString
HTMLEncoder::GetFooter() const{
    return L"</BODY></HTML>";
}

unsigned int
HTMLEncoder::GetTerminalFlags(const StyleDesc& /*styleDesc*/, unsigned char dirtyMask) const{
    return dirtyMask & (STYLEFONT | STYLESIZE | STYLEITAL | STYLEBOLD | STYLEUNDL | STYLECOLOR | STYLEBGCLR);
}

wxString
HTMLEncoder::FormatUnicodeChar(unsigned long unichar) const{
    if(escapeUnicode){
        return HTMLEscapeUnicode(unichar);
    }else{
        return wxString::Format(L"%c", unichar);
    }
}
