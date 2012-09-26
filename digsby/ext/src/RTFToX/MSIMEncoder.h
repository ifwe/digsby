#ifndef MSIMENCODER_H
#define MSIMENCODER_H

#include "wx/String.h"
#include "StyleDescs.h"
#include "Encoder.h"

class MSIMEncoder: public Encoder{
    public:
         MarkupDesc* GetMarkup(const StyleDesc& styleDesc, unsigned char dirtyMask, bool base) const;
         wxString FormatString(const wxString& originalString) const;
         wxString FormatLink(const wxString& target, const wxString& text) const;
         wxString GetHeader() const;
         wxString GetFooter() const;
         unsigned int GetTerminalFlags(const StyleDesc& styleDesc, unsigned char dirtyMask) const;
         wxString FormatUnicodeChar(unsigned long unichar) const;
};

#endif //MSIMENCODER_H