#ifndef DEBUG_UTIL_H
#define DEBUG_UTIL_H

#if defined TEST

    #include <vector>

    #include "wx/String.h"
    #include "StyleDescs.h"

    using namespace std;

    #define DBG_PRNT_TBLS 1 //print font and color tables to console?
    #define DBG_TIMER     1 //Time the conversion with StopWatch
    #define DBG_CONSOLE   1 //Show a console

    
    //Print a StyleDesc
    void PrintStyle(unsigned char formatMask, StyleDesc &currentStyle);
    
    //Print a MarkupDesc
    void PrintMarkup(MarkupDesc &markup);
    
    //Print contentmask's bitflags as strings
    void PrintContentMask(unsigned int contentmask);
    
    //Print the contents of a RTF font table
    void PrintFontTable(vector<FontDesc> &fonts);
    
    //Print the contnets of a RTF color table in HEX
    void PrintColorTable(vector<Color> &colors);
    
    void PrintTextAttr(wxTextAttr &textattr);
    
#else //TEST

    //defaults
    #define DBG_PRNT_TBLS 0
    #define DBG_TIMER     0
    #define DBG_CONSOLE   0

#endif //TEST

#endif //DEBUG_UTIL_H