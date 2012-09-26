#include "MSIMEncoder.h"

#define STYLEFTAG (STYLEFONT | STYLESIZE | STYLEBOLD | STYLEITAL | STYLEUNDL)

MarkupDesc*
MSIMEncoder::GetMarkup(const StyleDesc& styleDesc, unsigned char dirtyMask, bool /*base*/) const{
    
    MarkupDesc *md = new MarkupDesc;
    
    MarkupDesc *mdp = md;
    
    if(dirtyMask & STYLEFTAG){
    
        wxString fonttag(L"<f");
    
        if(dirtyMask & STYLEFONT){
            fonttag.Append(wxString::Format(L" f=\"%s\"", styleDesc.font->name));
            mdp->contentflags |= STYLEFONT;
        }
        
        if(dirtyMask & STYLESIZE){
            fonttag.Append(wxString::Format(L" h=\"%d\"", (styleDesc.size / 2) * 96 / 72));
            mdp->contentflags |= STYLESIZE;
        }

        if(dirtyMask & (STYLEBOLD | STYLEITAL | STYLEUNDL)){
            fonttag.Append(wxString::Format(
                L" s=\"%d\"", (styleDesc.styleflags & STYLEUNDL? 4 : 0) |
                              (styleDesc.styleflags & STYLEITAL? 2 : 0) |
                              (styleDesc.styleflags & STYLEBOLD? 1 : 0)));
            mdp->contentflags |= (STYLEBOLD | STYLEITAL | STYLEUNDL);
            
        }
        
        fonttag.Append(L">");
        
        mdp->initmarkup = fonttag;
        mdp->termmarkup = L"</f>";
        mdp->formatMask = dirtyMask & STYLEFTAG;
    }
    
    
    if(dirtyMask & STYLECOLOR){
        mdp = mdp->NewDesc();
        
        
        mdp->initmarkup.Printf(L"<c v=\"rgba(%d, %d, %d, 255)\">", styleDesc.color->r,
                                                                   styleDesc.color->g,
                                                                   styleDesc.color->b);
        mdp->termmarkup = L"</c>";
        mdp->contentflags |= STYLECOLOR;
        mdp->formatMask = STYLECOLOR;
    }
    
    if(dirtyMask & STYLEBGCLR && !styleDesc.bgcolor->IsWhite()){
        mdp = mdp->NewDesc();
        
        mdp->initmarkup.Printf(L"<b v=\"rgba(%d, %d, %d, 255)\">", styleDesc.bgcolor->r,
                                                                   styleDesc.bgcolor->g,
                                                                   styleDesc.bgcolor->b);
        mdp->termmarkup = L"</b>";
        mdp->contentflags |= STYLEBGCLR;
        mdp->formatMask = STYLEBGCLR;
    }
        
    return md;
}

wxString
MSIMEncoder::FormatString(const wxString& originalString) const{

    wxString workingString(originalString);
    
    workingString.Replace(L"&", L"&amp;");
    workingString.Replace(L"<", L"&lt;");
    workingString.Replace(L">", L"&gt;");
    
    workingString.Replace(L"\n", L"<br />");
    
    return workingString;

}

wxString
MSIMEncoder::FormatLink(const wxString& target, const wxString& text) const{
    return FormatString(wxString::Format(L"%s(%s)", text, target));
}

wxString
MSIMEncoder::GetHeader() const{
    return wxString(L"<p>");
}

wxString
MSIMEncoder::GetFooter() const{
    return wxString(L"</p>");
}

unsigned int
MSIMEncoder::GetTerminalFlags(const StyleDesc& /*styleDesc*/, unsigned char dirtyMask) const{
    return dirtyMask & (STYLEFONT | STYLESIZE | STYLEITAL | STYLEBOLD | STYLEUNDL | STYLECOLOR | STYLEBGCLR);
}

wxString
MSIMEncoder::FormatUnicodeChar(unsigned long unichar) const{
    return wxString::Format(L"%c", unichar);
}
