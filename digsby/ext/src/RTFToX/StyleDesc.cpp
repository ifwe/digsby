#include "StyleDescs.h"


MarkupDesc::MarkupDesc()
    : next(0)
    , contentflags(0)
    , formatMask(0)
{}

MarkupDesc::~MarkupDesc(){
    if (next)
        delete next;
}

Color::Color(long red, long green, long blue)
    : r(red)
    , g(green)
    , b(blue)
{}

Color::Color(const wxColor &wxcolor) : r(wxcolor.Red()), g(wxcolor.Green()), b(wxcolor.Blue()){}

wxString
Color::ToHex(const wxString format){
    
    if(format == this->format){
        return hex;
    }
    
    hex.Clear();
    long c;
    
    for(unsigned int i = 0; i < format.Len(); ++i){
        
        switch((const char)format[i]){
        
            case 'r':
                c = r;
                break;
                
            case 'g':
                c = g;
                break;
                
            case 'b':
                c = b;
                break;
                
            case 'a':
                c = 0xff;
                break;
            
            default:
                continue;
        }
        
        hex.Append(wxString::Format(wxT("%02x"), c));
        
    }
    
    this->format = format;
    
    return hex;
}

MarkupDesc* MarkupDesc::NewDesc(const wxString& initMarkup, const wxString& termMarkup, unsigned int contentflags, unsigned char formatMask){
    MarkupDesc* mdp;
    if (initmarkup.Len())
        mdp = next = new MarkupDesc;
    else
        mdp = this;
    
    mdp->initmarkup = initMarkup;
    mdp->termmarkup = termMarkup;
    mdp->contentflags |= contentflags;
    mdp->formatMask = formatMask;

    return mdp;
}

MarkupDesc* MarkupDesc::GetLast(){
    MarkupDesc *mdp = this;
            
    while(mdp->next){
        mdp = mdp->next;
    }
    
    return mdp;
}
