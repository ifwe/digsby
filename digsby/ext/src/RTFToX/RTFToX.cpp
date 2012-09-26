#include "RTFToX.h"

#if __WXMSW__
#include <windows.h>
#endif

#if DBG_TIMER
    #include "wx/stopwatch.h"
    wxStopWatch sw;
#endif

#include <map>

#include <string>
#include <wx/thread.h>
using std::map;

typedef map<wstring, wchar_t> SpecialCharMap;

static inline SpecialCharMap& getSpecialCharMap()
{
    static bool initializedSpecialCharMap = false;
    static SpecialCharMap specialchars;
    static wxMutex specialCharMutex;

    wxMutexLocker lock(specialCharMutex);
    if (!initializedSpecialCharMap) {
        initializedSpecialCharMap = true;

        specialchars[L"tab"]       = 0x0009;
        specialchars[L"emdash"]    = 0x2014;
        specialchars[L"endash"]    = 0x2013;
        specialchars[L"emspace"]   = 0x2003;
        specialchars[L"enspace"]   = 0x2002;
        specialchars[L"bullet"]    = 0x2022;
        specialchars[L"lquote"]    = 0x2018;
        specialchars[L"rquote"]    = 0x2019;
        specialchars[L"ldblquote"] = 0x201C;
        specialchars[L"rdblquote"] = 0x201D;
        specialchars[L"~"]         = 0x00A0;
        specialchars[L"-"]         = 0x002D;
        specialchars[L"_"]         = 0x2011;
    }

    return specialchars;
}

static inline wchar_t getSpecialChar(const wxString& lookup) {
    const SpecialCharMap& map = getSpecialCharMap();
    wxWCharBuffer buf(lookup.wc_str());
    SpecialCharMap::const_iterator i = map.find(buf.data());
    if (i == map.end())
        return 0;
    else
        return i->second;
}

//Lookup codepage from charset
//GetCodePage from http://www.codeproject.com/KB/recipes/RtfConverter.aspx
static unsigned int GetCodePage( long charSet ){
    switch(charSet){
        case 0:
            return 1252; //ANSI
        case 1:
            return 0; //Default
        case 2:
            return 42; //Symbol
        case 77:
            return 10000; //Mac Roman
        case 78:
            return 10001; //Mac Shift Jis
        case 79:
            return 10003; //Mac Hangul
        case 80:
            return 10008; //Mac GB2312
        case 81:
            return 10002; //Mac Big5
        case 82:
            return 0; //Mac Johab (old)
        case 83:
            return 10005; //Mac Hebrew
        case 84:
            return 10004; //Mac Arabic
        case 85:
            return 10006; //Mac Greek
        case 86:
            return 10081; //Mac Turkish
        case 87:
            return 10021; //Mac Thai
        case 88:
            return 10029; //Mac East Europe
        case 89:
            return 10007; //Mac Russian
        case 128:
            return 932; //Shift JIS
        case 129:
            return 949; //Hangul
        case 130:
            return 1361; //Johab
        case 134:
            return 936; //GB2312
        case 136:
            return 950; //Big5
        case 161:
            return 1253; //Greek
        case 162:
            return 1254; //Turkish
        case 163:
            return 1258; //Vietnamese
        case 177:
            return 1255; //Hebrew
        case 178:
            return 1256; //Arabic
        case 179:
            return 0; //Arabic Traditional (old)
        case 180:
            return 0; //Arabic user (old)
        case 181:
            return 0; //Hebrew user (old)
        case 186:
            return 1257; //Baltic
        case 204:
            return 1251; //Russian
        case 222:
            return 874; //Thai
        case 238:
            return 1250; //Eastern European
        case 254:
            return 437; //PC 437
        case 255:
            return 850; //OEM
    }

    return 0;
}

static bool IsMultiByte(unsigned char byte, int codepage){
    switch(codepage){
        case 932:
            return (byte >= 0x81 && byte <= 0x9F) || byte >= 0xE0;
        case 936:
        case 949:
        case 950:
            return byte >= 0x81;
        default:
            return false;
    }
}


static wxString GetFontFamilyStr(int wxfamily){
    switch(wxfamily){
        case wxFONTFAMILY_DECORATIVE:
            return L"fdecor";
        case wxFONTFAMILY_ROMAN:
            return L"froman";
        case wxFONTFAMILY_SCRIPT:
            return L"fscript";
        case wxFONTFAMILY_SWISS:
            return L"fswiss";
        case wxFONTFAMILY_MODERN:
            return L"fmodern";
        case wxFONTFAMILY_TELETYPE:
            return L"ftech";
        default:
            return L"fnil";

    }
}



RTFToX::RTFToX(){
    Reset();
}


void
RTFToX::Reset(){
    //Reset the system to default state

    currentStyle.font = 0;
    currentStyle.size = 0;
    currentStyle.color = 0;
    currentStyle.bgcolor = 0;
    currentStyle.styleflags = 0;
    formatMask = 0;

    fonts.clear();
    colors.clear();

    convertedString.Clear();
    bufferString.Clear();

    squirrellyDepth = 0;
    ignoreSpace = false;
    acceptToken = true;
    basemarkup = true;
}

void
RTFToX::ProcessCommand(const wxString &token, wxStringTokenizer &toker, const Encoder &encoder){
   //Process RTF format commands, these are denoted by a leading '/'

   wxString command;
   wxString arg;

#if __WXMSW__
    // FIXME: Do we need to run similar code under other platforms?
    if(token.StartsWith(L"'", &arg)){
        //Grrr, Exetended ASCII, needs to be converted to unicode then processed with the encoder

        
        ProcessFormat(encoder);

        wxString hexstring;
        wxString extstring;
        unsigned long ansiint;
        unsigned char ansichar[2];
        unsigned long unichar = 0;
        int bytecount = 1;

        hexstring = arg.Left(2);
        hexstring.ToULong(&ansiint, 16);
        ansichar[0] = (unsigned char)ansiint;
        
        if(IsMultiByte(ansichar[0], currentStyle.font->codepage)){
        
            if(toker.GetNextToken().StartsWith(L"'", &arg)){
                bytecount = 2;
                hexstring = arg.Left(2);
                hexstring.ToULong(&ansiint, 16);
                ansichar[1] = (unsigned char)ansiint;
            }else{
                
                bufferString.Append(encoder.FormatString(L"?"));
                bufferString.Append(encoder.FormatString(extstring));
                ignoreSpace = false;
                acceptToken = true;
                
                return;
            }
        }
        
        extstring = arg.Right(arg.Len()-2);
        
        MultiByteToWideChar(currentStyle.font->codepage,    //UINT CodePage,
                            0,                              //DWORD dwFlags,
                            (LPCSTR)&ansichar,              //LPCSTR lpMultiByteStr,
                            bytecount,                      //int cbMultiByte,
                            (LPWSTR)&unichar,               //LPWSTR lpWideCharStr,
                            2);                             //int cchWideChar


        bufferString.Append(encoder.FormatUnicodeChar(unichar));
        bufferString.Append(encoder.FormatString(extstring));

        ignoreSpace = false;
        acceptToken = true;

        return;


    } else
#endif

    if(token.StartsWith(L"~", &arg)){
    
        ProcessFormat(encoder);
        
        bufferString.Append(encoder.FormatString(L"\x00A0"));
        bufferString.Append(encoder.FormatString(arg));
        
        ignoreSpace = false;
        acceptToken = true;
        
        return;
    
    }else if(GetDigits(token, command, arg)){
        //Command contains numbers, so check certain supset

        if(token==L"b0"){
            //Trun off bold

            currentStyle.styleflags = currentStyle.styleflags & ~STYLEBOLD;
            formatMask |= STYLEBOLD;

        }else if(token==L"i0"){
            //Turn off italics

            currentStyle.styleflags = currentStyle.styleflags & ~STYLEITAL;
            formatMask |= STYLEITAL;

        }else if(token==L"ul0"){
            //Turn off Underline

            currentStyle.styleflags = currentStyle.styleflags & ~STYLEUNDL;
            formatMask |= STYLEUNDL;

        }else if(command==L"ansicpg"){
            //Set the ANSI code page
            arg.ToULong((unsigned long*)&defaultCodepage);

        }else if(command==L"uc"){
            //Set the unicode character code leangth
            arg.ToULong(&uniAltLen);

        }else if(command==L"u"){
            //Unicode character, process with encoder

            unsigned long unichar;
            arg.ToULong(&unichar);

            ProcessFormat(encoder);
            bufferString.Append(encoder.FormatUnicodeChar(unichar));

            wxString numstring;
            numstring.Printf(L"%d", unichar);

            wxString leftovers(arg.substr(numstring.Length() + 1));

            bufferString.Append(leftovers);
            
            ignoreSpace = false;
            acceptToken = true;
            

            return;

        }else if(command==L"fs"){
            //Set Font Size, this number is 2x pt size

            unsigned long size;
            arg.ToULong(&size);
            currentStyle.size = size;
            formatMask |= STYLESIZE;

        }else if(command==L"f"){
            //Set font from font table

            unsigned long i;
            arg.ToULong(&i);
            currentStyle.font = &fonts[i];
            formatMask |= STYLEFONT;

        }else if(command==L"cf"){
            //Set font color from color table

            unsigned long i;
            arg.ToULong(&i);
            currentStyle.color = (i >= 0 && i < colors.size()) ? &colors[i] : Color::BLACK();
            formatMask |= STYLECOLOR;

        }else if(command==L"highlight"){
            //Set font background color from color table

            unsigned long i;
            arg.ToULong(&i);
            currentStyle.bgcolor = i ? &colors[i] : Color::WHITE();
            formatMask |= STYLEBGCLR;

        }
    }else{
        //command doesn't contain numbers

        if(token==L"*"){
            //Editor specific meta info and commands, ignoreable
            IgnoreLoop(toker);
        }

        if(token==L"fonttbl"){
            //Make a font table
            ProcessFontTable(toker);

        }else if(token==L"colortbl"){
            //Make a color table
            ProcessColorTable(toker);

        }else if(token==L"b"){
            //Turn bold on
            currentStyle.styleflags |= STYLEBOLD;
            formatMask |= STYLEBOLD;

        }else if(token==L"i"){
            //Turn Italics on
            currentStyle.styleflags |= STYLEITAL;
            formatMask |= STYLEITAL;

        }else if(token==L"ul"){
            //Turn Underline on
            currentStyle.styleflags |= STYLEUNDL;
            formatMask |= STYLEUNDL;

        }else if(token==L"ulnone"){
            //Turn underline off
            currentStyle.styleflags = currentStyle.styleflags & ~STYLEUNDL;
            formatMask |= STYLEUNDL;

        }else if(token==L"line" || token==L"par"){
            //Insert NewLine
			ProcessFormat(encoder);
            bufferString.Append(encoder.FormatString(wxString(L"\n")));
            acceptToken = true;
            return;
            
        }else if(token==L"hl"){
            ProcessHyperlink(toker, encoder);
        }else if(wchar_t unichr = getSpecialChar(token)) {
            ProcessFormat(encoder);
            bufferString.Append(encoder.FormatUnicodeChar(unichr));
        }
    }
    
    acceptToken = false;
    return;
}

void
RTFToX::ProcessFontTable(wxStringTokenizer &toker){
    //Makes the font table

    wxString token;
    wxString delimiter;

    wxString fontarg;

    wxString fontname;
    wxString fontfamily;

    long charset = 0;
    unsigned int codepage = 0;

    short depth = squirrellyDepth;

    //Font table ends when the squirrelly depths drops out of where the table starts
    while(squirrellyDepth >= depth && toker.HasMoreTokens()){
        delimiter = toker.GetLastDelimiter();
        token = toker.GetNextToken();

        if(delimiter == L"\\"){
            if(token.StartsWith(L"fcharset", &fontarg)){
                fontarg.ToLong(&charset);
                codepage = GetCodePage(charset);
            }else if(wxString(L"fnil froman fswiss fmodern fscript fdecor ftech fbidi").Contains(token)){
                //Oh look, it's a Font Family

                fontfamily = token;
                //Font Families:
                //fnil  	Unknown or default fonts (the default)
                //froman 	Roman, proportionally spaced serif fonts            Times New Roman, Palatino
                //fswiss 	Swiss, proportionally spaced sans serif fonts 	    Arial
                //fmodern 	Fixed-pitch serif and sans serif fonts              Courier New, Pica
                //fscript 	Script fonts                                        Cursive
                //fdecor 	Decorative fonts                                    Old English, ITC Zapf Chancery
                //ftech 	Technical, symbol, and mathematical fonts           Symbol
                //fbidi 	Arabic, Hebrew, or other bidirectional font         Miriam
            }
        }else if(delimiter == L" "){
            //Space means we're looking at the Font Name
            if(fontname.Len() != 0) fontname.Append(L" ");
            fontname.Append(token);

        }else if(delimiter == L";"){
            //This means we're done with the entry
            FontDesc font;

            font.name = fontname;
            font.family = fontfamily;
            font.codepage = codepage;
            font.charset = charset;

            fonts.push_back(font);

            fontname.Clear();
            codepage = defaultCodepage;




        }else if(delimiter == L"{"){
            ++squirrellyDepth;

        }else if(delimiter == L"}"){
            --squirrellyDepth;
        }
    }

    #if DBG_PRNT_TBLS
        //Print the table for debugging
        PrintFontTable(fonts);
    #endif

}

void
RTFToX::ProcessColorTable(wxStringTokenizer &toker){
    //Makes the color table

    wxString token;
    wxString delimiter;
    wxString command;
    wxString colorarg;
    long r=0, g=0, b=0;

    const short thisDepth = squirrellyDepth;

    while(squirrellyDepth >= thisDepth && toker.HasMoreTokens()){
        delimiter = toker.GetLastDelimiter();
        token = toker.GetNextToken();

        if(delimiter == L"\\"){
            //This means it's time to do a color channel

            GetDigits(token, command, colorarg);

            if(command == L"red"){
                colorarg.ToLong(&r);
            }else if(command == L"green"){
                colorarg.ToLong(&g);
            }else if(command == L"blue"){
                colorarg.ToLong(&b);
            }

        }else if(delimiter == L";"){
            //This means the color is done

            Color color(r, g, b);

            colors.push_back(color);
            r = g = b = 0;



        }else if(delimiter == L"}"){
            --squirrellyDepth;
            //printf("--squirrellyDepth == %d\n", squirrellyDepth);

        }

    }

    #if DBG_PRNT_TBLS
        PrintColorTable(colors);
    #endif
}

void
RTFToX::ProcessHyperlink(wxStringTokenizer &toker, const Encoder &encoder){

    wxString token;
    wxString delimiter;
    wxString command;

    wxString source;
    wxString location;
    wxString text;
    wxString extra;

    wxString *field = &extra;

    const short depth = squirrellyDepth;

    while(squirrellyDepth >= depth && toker.HasMoreTokens()){
        delimiter = toker.GetLastDelimiter();
        token = toker.GetNextToken();

        if(delimiter == L"\\"){
            if(token == L"hlloc")
                field = &location;
            else if(token == L"hlfr")
                field = &text;
            else if(token == L"hlsrc")
                field = &source;

        }else if(delimiter == L" " && !token.IsEmpty() && squirrellyDepth > depth){
            while(delimiter != L"}"){
                if(delimiter == L"\\"){
                    delimiter = toker.GetLastDelimiter();
                    token = toker.GetNextToken();
                }

                field->Append(delimiter);
                field->Append(token);

                delimiter = toker.GetLastDelimiter();
                token = toker.GetNextToken();

            }

            --squirrellyDepth;

            field = &extra;

        }else if(delimiter == L"{"){
            ++squirrellyDepth;
        }else if(delimiter == L"}"){
            --squirrellyDepth;
        }

    }

    bufferString.Append(encoder.FormatLink(location, text));

    acceptToken = true;

}

void
RTFToX::IgnoreLoop(wxStringTokenizer &toker){
    //Just continues parsing the RTF until it dorps out of the current squirelly depth

    wxString token;
    wxString delimiter;

    const short thisDepth = squirrellyDepth;
    while(squirrellyDepth >= thisDepth && toker.HasMoreTokens()){

        delimiter = toker.GetLastDelimiter();
        token = toker.GetNextToken();

        if(delimiter == L"{"){
            ++squirrellyDepth;
        }else if(delimiter == L"}"){
            --squirrellyDepth;
            acceptToken = true;
        }
    }
}

void
RTFToX::ProcessFormat(const Encoder &encoder){
    //We're about to process some more text so should take care of the markup we have queued up

    if(formatMask){

        //Using the new markup, what previous markup types should we end
        unsigned int tflags = encoder.GetTerminalFlags(currentStyle, formatMask);

        if(!markupStack.empty()){
            list<MarkupDesc>::iterator pastMarkup = markupStack.begin();
            unsigned int pastCFlags;
            unsigned int lastCFlags;

            //Scan over the markup stack
            while(pastMarkup != markupStack.end()){

                pastCFlags = pastMarkup->contentflags;

                //If content type of something in the stack is in the terminal flags
                if(pastMarkup->contentflags & tflags){

                    //Terminate all markup between top and detected node
                    do{
                        formatMask |= markupStack.front().formatMask;
                        convertedString.Append(markupStack.front().termmarkup);
                        lastCFlags = markupStack.front().contentflags;
                        markupStack.pop_front();
                    }while(!markupStack.empty() && (lastCFlags != pastCFlags));

                    pastMarkup = markupStack.begin();

                    continue;
                }

                ++pastMarkup;
            }
        }


        MarkupDesc *mdp = encoder.GetMarkup(currentStyle, formatMask, basemarkup);
        MarkupDesc *md0 = mdp;

        basemarkup = false;

        //Could be multiple MarkupDescs chained, apply each and push onto stack
        do{

            convertedString.Append(mdp->initmarkup);
            markupStack.push_front(*mdp);
            markupStack.front().next = 0;
            mdp = mdp->next;

        }while(mdp != 0);

        delete md0;

        //New format applied, reset mask
        formatMask = 0;


    }
}

void
RTFToX::ProcessToken(const wxString &token, const wxString &delimiter, const Encoder &encoder){
    //Push token and/or delimiter to the buffer string

    ProcessFormat(encoder);

    if(!ignoreSpace){
        bufferString.append(encoder.FormatString(delimiter));
    }else{
        ignoreSpace = false;
    }

    acceptToken = true;


    if(!token.IsEmpty()){
        bufferString.Append(encoder.FormatString(token));
    }
}

void
RTFToX::FlushFormat(){
    while(!markupStack.empty()){
        //Close open markup and clear the stack
        formatMask |= markupStack.front().formatMask;
        convertedString.Append(markupStack.front().termmarkup);
        markupStack.pop_front();
    }
}

wxString
RTFToX::ParseRTF(wxString &rtf, const Encoder &encoder){

    //all desired newlines are marked with \par or \line no need for these
    rtf.Replace(L"\n", L" ");


    //remove trailing "/par "}
    rtf.RemoveLast(rtf.Len() - rtf.rfind(L"\\par"));
    rtf.Append(L"}");



    wxString token;
    wxString delimiter;

    wxStringTokenizer toker(rtf, L"\\;{} \t");

    while(toker.HasMoreTokens()){
        delimiter = toker.GetLastDelimiter();
        token = toker.GetNextToken();

        if(delimiter == L"\\"){
            //next token is either a command or a escaped character

            //Space used to denote the end of a command, so ignore the next one
            ignoreSpace = true;

            if(!token.IsEmpty()){
                //if Token isn't empty, send it off to command procesing

                ProcessCommand(token, toker, encoder);
                

                if(formatMask && bufferString.Len()){
                    //a command just got processed
                    //dump the buffered data into the converted string before processing more

                    convertedString.Append(bufferString);
                    bufferString.Clear();
                }

            }else{
                //Token is empty, so it must be escaping the next delimiter

                delimiter = toker.GetLastDelimiter();
                token = toker.GetNextToken();

                ProcessToken(delimiter + token, delimiter, encoder);
            }



        }else if(delimiter == L";"){
            //if we're in a command then this is ignored
            //otherwise it's part of the string and should be appended

            if(acceptToken){
                ProcessToken(token, delimiter, encoder);
            }

            acceptToken = true;

        }else if(delimiter == L"{"){
            ++squirrellyDepth;

        }else if(delimiter == L"}"){
            --squirrellyDepth;

        }else if(delimiter == L" "){
            //Space means we're back in the string, process it
            ProcessToken(token, delimiter, encoder);

        }

    }

    //Out of tokens to process

    if(bufferString.Len()){
        //If there's text in the buffer, now is a good time to flush

        convertedString.Append(bufferString);
        bufferString.Clear();
    }

    FlushFormat();

    return convertedString;

}

wxString
RTFToX::ApplyStyleToText(const wxString text, const Encoder &encoder, const wxTextAttr &style){

    wxFont wxfont = style.GetFont();

    FontDesc font = {wxfont.GetFaceName(), GetFontFamilyStr(wxfont.GetFamily()), 0, 0};
    Color fgcolor(style.GetTextColour());
    Color bgcolor(style.GetBackgroundColour());

    short styleflags = 0;
    if(wxfont.GetWeight() == wxFONTWEIGHT_BOLD)  styleflags |= STYLEBOLD;
    if(wxfont.GetStyle()  == wxFONTSTYLE_ITALIC) styleflags |= STYLEITAL;
    if(wxfont.GetUnderlined())                   styleflags |= STYLEUNDL;

    currentStyle.font = &font;
    currentStyle.size = wxfont.GetPointSize()*2;
    currentStyle.styleflags = styleflags;
    currentStyle.color = &fgcolor;
    currentStyle.bgcolor = &bgcolor;

    formatMask = 0xff;
    ProcessFormat(encoder);
    convertedString.Append(encoder.FormatString(text));
    FlushFormat();

    return convertedString;

}

wxString
RTFToX::Convert(const wxString &text, const Encoder &encoder, const wxString &inputFormat, const wxTextAttr *style){

    #if DBG_TIMER
        sw.Start();
    #endif

    wxString text2(text);
    wxString output;

    //let's just use unix style newlines.
    text2.Replace(L"\r", L"");

    output.Append(encoder.GetHeader());


    //TODO: Replace with type lookup map later for pluginable input types
    //TODO: Also abstarct all RTF specific code
    if(inputFormat == L"rtf"){
        output.Append(ParseRTF(text2, encoder));
    }else if(style){
        output.Append(ApplyStyleToText(text2, encoder, *style));
    }else{
        output.Append(encoder.FormatString(text2));
    }


    //Add the footer if there is one
    output.Append(encoder.GetFooter());


    Reset();


    #if DBG_TIMER
        sw.Pause();
        printf("Time to process: %dms;\n\n\n", sw.Time());
    #endif

    return output;


}

