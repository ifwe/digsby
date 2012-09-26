#ifndef __CGUI_WINUTIL_H_
#define __CGUI_WINUTIL_H_

#include <wx/dynlib.h>

//
// loads a DLL only once, even if there's an error
//
// example:
// static wxOnceOnlyDLLLoader wxGDI32DLL(_T("gdi32"));
//
class DLLLoader
{
    // stolen from src/msw/dc.cpp

public:
    // ctor argument must be a literal string as we don't make a copy of it!
    DLLLoader(const wxChar *dllName);
    void *GetSymbol(const wxChar *name);

private:
    wxDynamicLibrary m_dll;
    const wxChar *m_dllName;
};

bool glassExtendInto(wxWindow* win, int left = -1, int right =-1, int top = -1, int bottom = -1);
bool isGlassEnabled();

void setThreadName(unsigned long dwThreadID, const wxString& threadName);

void cls();

#endif // __CGUI_WINUTIL_H_
