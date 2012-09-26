#ifndef ENCODER_H
#define ENCODER_H

//Base class for the Encoders to convert the RTFToX information to other forms of markup
class Encoder{
    public:
        virtual ~Encoder() {}
        //Generate a MarkupDesc from a StyleDesc
        virtual MarkupDesc* GetMarkup(const StyleDesc& styleDesc, unsigned char dirtyMask, bool base) const = 0;
        
        //Prepare string for output escaping any reserved characters
        virtual wxString FormatString(const wxString& originalString) const = 0;
        
        //Create a link
        virtual wxString FormatLink(const wxString& target, const wxString& text) const = 0;
        
        //If there's a constant header for the encoded markup, return it, otherwise empty string
        virtual wxString GetHeader() const = 0;
        
        //If there's a constant footer for the encoded markup, return it, otherwise empty string
        virtual wxString GetFooter() const = 0;
        
        //Format a unicode character for the form of markup
        virtual wxString FormatUnicodeChar(unsigned long unichar) const = 0;
       
        //Given what styles are going to be applied, returns bitflags for what styles should be ended
        virtual unsigned int GetTerminalFlags(const StyleDesc& styleDesc, unsigned char dirtyMask) const = 0;
};


#endif //ENCODER_H