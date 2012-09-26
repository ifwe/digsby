#ifdef TEST
#include "DebugUtil.h"

void PrintStyle(unsigned char formatMask, StyleDesc &currentStyle){
    printf("===PrintStyle======\n");
    
    printf("\tFormat Mask: ");
    PrintContentMask(formatMask);
    
    wxString stylestr;
    if(currentStyle.styleflags){
        if(currentStyle.styleflags & STYLEBOLD) stylestr.append(L"Bold");
        if(currentStyle.styleflags & STYLEITAL) stylestr.append(stylestr.IsEmpty()? L"Italic" : L", Italic");
        if(currentStyle.styleflags & STYLEUNDL) stylestr.append(stylestr.IsEmpty()? L"Underline" : L", Underline");
        
    }else stylestr = L"None";
    printf("\tstlye: %s\n", stylestr.ToAscii());
    
    if(currentStyle.font){
        printf("\tFont: %s\n", currentStyle.font->name.ToAscii());
        printf("\tCodepage: %03d\n", currentStyle.font->codepage);
    }
    printf("\tSize: %d\n", currentStyle.size);
    
    if(currentStyle.color) printf("\tColor: %s\n", currentStyle.color->ToHex().ToAscii());
    if(currentStyle.bgcolor) printf("\tBG Color: %s\n", currentStyle.bgcolor->ToHex().ToAscii());
    printf("\n");
}

void PrintMarkup(MarkupDesc &markup){
    printf("===PrintMarkup======\n");
    printf("\tInit Markup: %s\n", markup.initmarkup.ToAscii());
    printf("\tTerm Markup: %s\n", markup.termmarkup.ToAscii());
    printf("\tFormat Mask: ");
    PrintContentMask(markup.formatMask);
    printf("\tContent Flags: ");
    PrintContentMask(markup.contentflags);
    printf("\tHas next: %s\n", markup.next? "True" : "False");
    printf("\n");
}

void PrintContentMask(unsigned int contentmask){
    
    wxString content;
    
    if(contentmask & STYLEBOLD) content.Append(L"bold; ");
    if(contentmask & STYLEITAL) content.Append(L"itaic; ");
    if(contentmask & STYLEUNDL) content.Append(L"underline; ");
    if(contentmask & STYLEFONT) content.Append(L"fontname; ");
    if(contentmask & STYLESIZE) content.Append(L"size; ");
    if(contentmask & STYLECOLOR) content.Append(L"color; ");
    if(contentmask & STYLEBGCLR) content.Append(L"bgcolor; ");
    
    printf("%s\n", content.ToAscii());
}

void PrintFontTable(vector<FontDesc> &fonts){

    printf("\n\n===Font Table==========================\n");
    printf("  CPage CSet Family  Name\n");
    
    for(vector<FontDesc>::iterator font = fonts.begin(); font != fonts.end(); ++font){
        printf("  %05d %04d %-7s %s\n", font->codepage, font->charset, font->family.ToAscii(), font->name.ToAscii());
    }
    
    printf("=======================================\n\n\n");
}


void PrintColorTable(vector<Color> &colors){
    
    printf("\n\n===Color Table=========================\n");
    
    for(vector<Color>::iterator color = colors.begin(); color != colors.end(); ++color){
        printf("  %s\n", color->ToHex().ToAscii());
    }
    
    printf("=======================================\n\n\n");
    
}

void PrintTextAttr(wxTextAttr &textattr){
        wxFont font = textattr.GetFont();
        printf("TextAttr is:\n");
        printf("\tName: %s\n", font.GetFaceName().ToAscii());
        printf("\tSize: %d\n", font.GetPointSize());
        printf("\tStyle:%s%s%s\n", font.GetWeight() == wxFONTWEIGHT_BOLD?  " Bold"       : "",
                                   font.GetStyle()  == wxFONTSTYLE_ITALIC? " Itallic"    : "",
                                   font.GetUnderlined()?                   " Underlined" : "");
        
        wxColor textcolor = textattr.GetTextColour();
        wxColor bgcolor   = textattr.GetBackgroundColour();
        
        printf("\ttextcolor: %02x%02x%02x\n", textcolor.Red(), textcolor.Green(), textcolor.Blue());
        printf("\tbgcolor: %02x%02x%02x\n",     bgcolor.Red(),   bgcolor.Green(),   bgcolor.Blue());
    }

#endif // TEST
