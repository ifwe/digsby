#include "MiscUI.h"

#ifdef __WXMSW__
#include <windows.h>

// Returns the time since last user input, in milliseconds.
unsigned int GetUserIdleTime()
{
    LASTINPUTINFO inputInfo = { sizeof(LASTINPUTINFO) };

    if (GetLastInputInfo(&inputInfo))
        return GetTickCount() - inputInfo.dwTime;
    else
        return 0;
}
#endif

