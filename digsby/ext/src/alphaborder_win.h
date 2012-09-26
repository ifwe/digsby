//
// alphaborder_win.h
//

#ifndef _ALPHABORDER_WIN_H_
#define _ALPHABORDER_WIN_H_

#include <wx/window.h>

bool SetLayered(wxWindow* window, bool layered);
bool ApplyAlpha(wxWindow* window, wxBitmap& bitmap, unsigned char alpha = 255);

#ifndef NDEBUG
class DbgGuiLeak
{
public:
    explicit DbgGuiLeak (const char* funcname, const char* file, int line);
    ~DbgGuiLeak ();
private:
    const char* _funcname;
    const char* _file;
    const int _line;
    unsigned _guiResCount;
};

#define GDITRACK DbgGuiLeak __dbgGuiLeak(__FUNCTION__, __FILE__, __LINE__);
#endif

#endif
