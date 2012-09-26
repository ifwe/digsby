#include "IconUtils.h"

#include <wx/filename.h>

bool tempImageFile(const wxString& path, const wxString& prefix, const wxBitmap& bitmap, wxString& filename, wxBitmapType type)
{
    // ensure directory exists
    if (path && !wxFileName::Mkdir(path, 0777, wxPATH_MKDIR_FULL))
        return false;

    filename = wxFileName(path, prefix).GetFullPath();

    wxBitmap saveBitmap(bitmap);

    // To save icon files with transparency we need the bitmap to have a mask.
    if (type == wxBITMAP_TYPE_ICO && !saveBitmap.GetMask()) {
        wxImage img(saveBitmap.ConvertToImage());
        img.ConvertAlphaToMask();
        saveBitmap = wxBitmap(img);
    }

    if (!saveBitmap.SaveFile(filename, type))
        return false;

    return true;
}

