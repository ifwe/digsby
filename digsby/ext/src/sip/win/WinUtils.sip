%ModuleHeaderCode
#include "WinUtils.h"
%End

bool glassExtendInto(wxWindow* win, int left = -1, int right =-1, int top = -1, int bottom = -1);
bool isGlassEnabled();
void setThreadName(unsigned long dwThreadID, const wxString& threadName);
void cls();
