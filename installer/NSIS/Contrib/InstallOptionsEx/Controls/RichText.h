#define _RICHEDIT_VER 0x0200
#include <richedit.h>
#undef _RICHEDIT_VER

int nRichTextVersion;
static DWORD dwRead;

DWORD CALLBACK FIELD_RICHTEXT_StreamIn(DWORD dwCookie, LPBYTE pbBuff, LONG cb, LONG *pcb)
{
  strncpy((char*)pbBuff,(char*)dwCookie+dwRead,cb);
  *pcb=strlen((char*)pbBuff);
  dwRead+=*pcb;
  return 0;
}

DWORD CALLBACK FIELD_RICHTEXT_StreamOut(DWORD dwCookie, LPBYTE pbBuff, LONG cb, LONG *pcb)
{
  if(dwRead+1 > (UINT)g_nBufferSize)
   return 1;

  if(dwRead+cb+1 <= (UINT)g_nBufferSize)
    strcpy((char*)dwCookie+dwRead,(char*)pbBuff);
  else
    strncpy((char*)dwCookie+dwRead,(char*)pbBuff, (UINT)g_nBufferSize - dwRead+1);
  *pcb=strlen((char*)dwCookie);
  dwRead+=*pcb;
  return 0;
}
