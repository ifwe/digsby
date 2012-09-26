#include "XHTMLEncoder.h"


MarkupDesc*
XHTMLEncoder::GetMarkup(const StyleDesc& styleDesc, unsigned char dirtyMask, bool base) const{
    
    MarkupDesc *md = new MarkupDesc;
    
    if((dirtyMask == STYLEBGCLR) && styleDesc.bgcolor->IsWhite()){
        return md;
    }
    
    wxString stylestring;
    unsigned int contentflags = 0;
    
    if(dirtyMask & STYLEFONT){
        stylestring.Append(wxString::Format(L" font-family: %s;", styleDesc.font->name));
        contentflags |= STYLEFONT;
    }
    
    if(dirtyMask & STYLESIZE){
        stylestring.Append(wxString::Format(L" font-size: %dpt;", styleDesc.size/2));
        contentflags |= STYLESIZE;
    }
    
    if(dirtyMask & STYLEITAL){
        if(styleDesc.styleflags & STYLEITAL){
            stylestring.Append(L" font-style: italic;");
        }else{
            stylestring.Append(L" font-style: normal;");
        }

        contentflags |= STYLEITAL;
        
    }
    
    if(dirtyMask & STYLEBOLD){
        if(styleDesc.styleflags & STYLEBOLD){
            stylestring.Append(L" font-weight: bold;");
        }else{
            stylestring.Append(L" font-weight: normal;");
        }
        
        contentflags |= STYLEBOLD;
        
    }
    
    
    
    if(dirtyMask & STYLECOLOR){
        stylestring.Append(wxString::Format(L" color: #%s;", styleDesc.color->ToHex()));
        contentflags |= STYLECOLOR;
    }
    
    if(dirtyMask & STYLEBGCLR && !styleDesc.bgcolor->IsWhite()){
        if(base){
            md->GetLast()->next = GetMarkup(styleDesc, STYLEBGCLR, false);
            dirtyMask = dirtyMask & ~STYLEBGCLR;
        }else{
            stylestring.Append(wxString::Format(L" background-color: #%s;", styleDesc.bgcolor->ToHex()));
            contentflags |= STYLEBGCLR;
        }
    }
    
    if((dirtyMask & STYLEUNDL) && (styleDesc.styleflags & STYLEUNDL)){
        if(contentflags){
            md->GetLast()->next = GetMarkup(styleDesc, STYLEUNDL, false);
            dirtyMask = dirtyMask & ~STYLEUNDL;
        }else{
            
            stylestring.Append(L" text-decoration: underline;");
            
            contentflags |= STYLEUNDL;
        }
    }

    
        
    if(!stylestring.IsEmpty()){
        
        if (stylestring.StartsWith(L" ")){
            stylestring.Trim(false); // from left
        }
            
        md->initmarkup.Printf(L"<span style=\"%s\">", stylestring);
        md->contentflags = base? 0 : contentflags;
        md->termmarkup = L"</span>";
        md->formatMask = dirtyMask;
    }
    
    
    return md;
    
}

wxString
XHTMLEncoder::FormatString(const wxString& originalString) const{
    wxString workingString(originalString);
    
    workingString.Replace(L"&", L"&amp;");
    workingString.Replace(L"<", L"&lt;");
    workingString.Replace(L">", L"&gt;");
    workingString.Replace(L"\x00A0", L"&#160;");
    
    workingString.Replace(L"\n", L"<br />");
    
    workingString = EscapeUnicode(workingString, &HTMLEscapeUnicode);
    
    return workingString;
}

wxString
XHTMLEncoder::FormatLink(const wxString& target, const wxString& text) const{
    return wxString::Format(L"<a href=\"%s\">%s</a>", FormatString(target), FormatString(text));
}

wxString
XHTMLEncoder::GetHeader() const{
    return wxEmptyString;
}

wxString
XHTMLEncoder::GetFooter() const{
    return wxEmptyString;
}

unsigned int
XHTMLEncoder::GetTerminalFlags(const StyleDesc& /*styleDesc*/, unsigned char dirtyMask) const{
    return dirtyMask & (STYLEFONT | STYLESIZE | STYLEITAL | STYLEBOLD | STYLEUNDL | STYLECOLOR | STYLEBGCLR);
}

wxString
XHTMLEncoder::FormatUnicodeChar(unsigned long unichar) const{
    return  HTMLEscapeUnicode(unichar);
}
