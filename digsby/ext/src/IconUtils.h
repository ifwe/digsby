#ifndef _CGUI_ICON_UTILS_H
#define _CGUI_ICON_UTILS_H

#include <wx/wx.h>

bool tempImageFile(const wxString& path, const wxString& prefix, const wxBitmap& bitmap, wxString& filename, wxBitmapType = wxBITMAP_TYPE_ICO);

#endif // _CGUI_ICON_UTILS_H
