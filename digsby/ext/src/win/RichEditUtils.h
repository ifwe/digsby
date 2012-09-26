#ifndef __CGUI_RICHEDIT_UTILS_H__
#define __CGUI_RICHEDIT_UTILS_H__

#include <wx/textctrl.h>

int GetRichEditParagraphAlignment(wxTextCtrl* textCtrl);
bool SetRichEditParagraphAlignment(wxTextCtrl* textCtrl, int alignment);

#endif // __CGUI_RICHEDIT_UTILS_H__

