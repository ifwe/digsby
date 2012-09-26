#include "YahooEncoder.h"

#define STYLEFTAG (STYLEFONT | STYLESIZE)

MarkupDesc*
YahooEncoder::GetMarkup(const StyleDesc &styleDesc, unsigned char dirtyMask, bool base) const{

    MarkupDesc *md = new MarkupDesc;
    
    MarkupDesc *mdp = md;
    
    unsigned char currentMask = dirtyMask;
    
    if(currentMask & STYLEFTAG){
    
        
        wxString fonttag(L"<font");
    
        if(currentMask & STYLEFONT){
            fonttag.Append(wxString::Format(L" face=\"%s\"", styleDesc.font->name));
            if(!base) mdp->contentflags |= STYLEFONT;
        }
        
        if(currentMask & STYLESIZE){
            fonttag.Append(wxString::Format(L" size=\"%d\"", (int)styleDesc.size/2));
            if(!base) mdp->contentflags |= STYLESIZE;
        }
        
        fonttag.Append(L">");
        
        mdp->initmarkup = fonttag;
        mdp->termmarkup = L"</font>";
        mdp->formatMask = currentMask & STYLEFTAG;
        
        currentMask = currentMask & ~STYLEFTAG;
    }
    
    if(currentMask & STYLEBOLD && styleDesc.styleflags & STYLEBOLD){
        mdp = mdp->NewDesc(L"\x1b[1m", L"\x1b[x1m", STYLEBOLD, STYLEBOLD);
        currentMask = currentMask & ~STYLEBOLD;
    }
    
    if(currentMask & STYLEITAL && styleDesc.styleflags & STYLEITAL){
        mdp = mdp->NewDesc(L"\x1b[2m", L"\x1b[x2m", STYLEITAL, STYLEITAL);
        currentMask = currentMask & ~STYLEITAL;
    }
    
    if(currentMask & STYLEUNDL && styleDesc.styleflags & STYLEUNDL){
        mdp = mdp->NewDesc(L"\x1b[4m", L"\x1b[x4m", STYLEUNDL, STYLEUNDL);
        currentMask = currentMask & ~STYLEUNDL;
    }
    
    if(dirtyMask & STYLECOLOR){
        mdp = mdp->NewDesc(wxString::Format(L"\x1b[#%sm", styleDesc.color->ToHex()),
                           wxEmptyString,
                           STYLECOLOR, STYLECOLOR);
    }
    
    //STYLEBGCLR not supported
    
    return md;

}

wxString
YahooEncoder::FormatString(const wxString& originalString) const{
    //TODO: Can escape special chars in yahoo?
    return originalString;
}

wxString
YahooEncoder::FormatLink(const wxString& target, const wxString& text) const{
    return FormatString(wxString::Format(L"%s(%s)", text, target));
}

wxString
YahooEncoder::GetHeader() const{
    return wxEmptyString;
}


wxString
YahooEncoder::GetFooter() const{
    return wxEmptyString;
}

unsigned int
YahooEncoder::GetTerminalFlags(const StyleDesc& /*styleDesc*/, unsigned char dirtyMask) const{
    return dirtyMask & (STYLEFONT | STYLESIZE | STYLEITAL | STYLEBOLD | STYLEUNDL | STYLECOLOR);
}

wxString
YahooEncoder::FormatUnicodeChar(unsigned long unichar) const{

    //TODO: Is this what Yahoo wants?
    return wxString::Format(L"%c", unichar);
}
