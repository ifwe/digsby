#ifndef RTFTOX_H
#define RTFTOX_H

#include "wx/String.h"
#include <list>
#include <vector>



#include "wx/tokenzr.h"

#include "StringUtil.h"
#include "StyleDescs.h"
#include "Encoder.h"
#include "Debugutil.h"

using namespace std;

class RTFToX{
    private:
        StyleDesc currentStyle;
        unsigned char formatMask; //See StyleDesc.h for constants
        vector<FontDesc> fonts;
        vector<Color> colors;
        unsigned int defaultCodepage; 
        short squirrellyDepth; //How many {} nested are we?
        unsigned long uniAltLen; //Unicode chars have an alternate ASCII string in RTF, how many chars?
        
        wxString convertedString;
        wxString bufferString;
        bool basemarkup; //Is this the first peice if markup?
        
        list<MarkupDesc> markupStack; //All the markup already applied to the string, stores how to end each
        
        bool ignoreSpace; //Ignore the next space processed as it's part of a command
        bool acceptToken; //Next token is not part of a command
        
        void Reset();
        void ProcessCommand(const wxString &token, wxStringTokenizer &toker, const Encoder &encoder);
        void ProcessFontTable(wxStringTokenizer &toker);
        void ProcessColorTable(wxStringTokenizer &toker);
        void ProcessHyperlink(wxStringTokenizer &toker, const Encoder &encoder);
        void IgnoreLoop(wxStringTokenizer &toker);
        void ProcessToken(const wxString &token, const wxString &delimiter, const Encoder &encoder);
        void ProcessFormat(const Encoder &encoder);
        void FlushFormat();
        wxString ParseRTF(wxString &rtf, const Encoder &encoder);
        
    public:
        RTFToX();
        wxString Convert(const wxString &rtf, const Encoder &encoder, const wxString &inputFormat = wxT("rtf"), const wxTextAttr *style = 0);
        wxString ApplyStyleToText(const wxString text, const Encoder &encoder, const wxTextAttr &style);
};

#endif //RTFTOX_H
