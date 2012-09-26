#ifndef STRING_UTIL_H
#define STRING_UTIL_H

#include "wx/String.h"
#include "wx/tokenzr.h"

//Make a wxString internet safe
wxString URLEncode(wxString input);

//Test to see if a wxString contains any digits
bool HasDigits(const wxString &string);

//If the string contains digits returns True and modifies command and arg so that:
//  command contains the first section of the string
//  arg contains the second section of the string
//  split before the first digit in the string
bool GetDigits(const wxString &string, wxString &command, wxString &arg);

bool IsRTF(const wxString &string);

wxString EscapeUnicode(const wxString &string, wxString (*FormatUnicodeChar)(unsigned long));

wxString HTMLEscapeUnicode(unsigned long unichar);

#endif //STRING_UTIL_H