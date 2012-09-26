#ifndef __LOGGING__
#define __LOGGING__

#include <windows.h>
#include <stdlib.h>
#include <stdio.h>
#include <malloc.h>
#include <stdarg.h>

#define LE_POPUP 0x00000010

void SetVerbose(bool on);
void vLogMsg(const wchar_t *msg, va_list args);
void LogMsg(const wchar_t *msg, ...);
void LogPop(const wchar_t *title, const wchar_t *msg, ...);
DWORD LogErr(DWORD errCode = 0, DWORD flags=0, const wchar_t *msg = 0, ...);
bool OpenLog(const wchar_t *logDir, const wchar_t *logfile);
bool OpenLog(const wchar_t *logFile);
void CloseLog();

#endif //__LOGGING__