#ifndef __SPLASH__
#define __SPLASH__

#include <windows.h>
#include <fstream>

#define PADDING 10


DWORD OnPaint(HWND hwnd);
DWORD InitSplash(HINSTANCE hInstance, const wchar_t *imagePath, const wchar_t *msg);
void CloseSplash();




#endif //__SPLASH__