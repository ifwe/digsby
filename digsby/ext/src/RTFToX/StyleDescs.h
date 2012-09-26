#ifndef STYLEDESCS_H
#define STYLEDESCS_H

#include "wx/wx.h"
#include "wx/String.h"

#define STYLECLEAR  0
#define STYLEBOLD   1
#define STYLEITAL   2
#define STYLEUNDL   4
#define STYLEFONT   8
#define STYLESIZE   16
#define STYLECOLOR  32
#define STYLEBGCLR  64

//Stores a color as RGB
class Color
{
    private:
        wxString hex, format;
    public:
        long r, g, b;
        Color(long red, long green, long blue);
        Color(const wxColor &wxcolor);
        
        //Generates a string containing the hex digits in the order diplayed in format
        //r,g,b, and a are valid in the format string
        wxString ToHex(const wxString format = L"rgb");
        
        bool IsWhite(){
            return r == 255 && g == 255 && b == 255;
        }

    static Color* WHITE()
    {
        static Color white(255L, 255L, 255L);
        return &white;
    }

    static Color* BLACK()
    {
        static Color black(0L, 0L, 0L);
        return &black;
    }
};

//Structured interpretation of a RTF fonttable entry
struct FontDesc{
    wxString name;
    wxString family;
    int codepage;
    int charset;
};

//Structured interpretation of RTF format state
struct StyleDesc{
    FontDesc *font;
    unsigned long size;
    short styleflags;
    Color *color;
    Color *bgcolor;
};

//Container for the:
//      -start markup
//      -end markup
//      -flags for the content types the markup contains that can be ended
//      -flags for markup types that where changed
//      -pointer to a posible nested set of markup
class MarkupDesc{
    public:
        unsigned int contentflags;
        wxString initmarkup;
        wxString termmarkup;
        MarkupDesc *next;
        unsigned char formatMask;
        
        MarkupDesc();
        ~MarkupDesc();

        MarkupDesc* NewDesc(const wxString& initMarkup = wxEmptyString,
                            const wxString& termMarkup = wxEmptyString,
                            unsigned int contentflags = 0,
                            unsigned char formatMask = 0);
                            
        MarkupDesc* GetLast();
};

#endif //STYLEDESCS_H
