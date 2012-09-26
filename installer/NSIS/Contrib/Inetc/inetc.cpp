/*******************************************************
* FILE NAME: inetc.cpp
*
* Copyright 2004 - Present NSIS
*
* PURPOSE:
*    ftp/http file download plug-in
*    on the base of MS Inet API
*    todo: status write mutex (?)
*          4 GB limit (http support?)
*
* CHANGE HISTORY
*
* Author      Date  Modifications
* Takhir Bedertdinov
*     Nov 11, 2004  Original
*     Dec 17, 2004  Embedded edition -
*              NSISdl GUI style as default
*              (nsisdl.cpp code was partly used)
*     Dec 17, 2004  MSI Banner style
*     Feb 20, 2005  Resume download
*              feature for big files and bad connections
*     Mar 05, 2005  Proxy authentication
*              and /POPUP caption prefix option
*     Mar 25, 2005  Connect timeout option
*              and FTP switched to passive mode
*     Apr 18, 2005  Crack URL buffer size 
*              bug fixed (256->string_size)
*              HTTP POST added
*     Jun 06, 2005  IDOK on "Enter" key locked
*              POST HTTP header added 
*     Jun 22, 2005  non-interaptable mode /nocancel
*              and direct connect /noproxy
*     Jun 29, 2005  post.php written and tested
*     Jul 05, 2005  60 sec delay on WinInet detach problem
*              solved (not fine, but works including
*              installer exit and system reboot) 
*     Jul 08, 2005  'set foreground' finally removed
*     Jul 26, 2005  POPUP translate option
*     Aug 23, 2005  https service type in InternetConnect
*              and "ignore certificate" flags
*     Sep 30, 2005  https with bad certificate from old OS;
*              Forbidden handling
*     Dec 23, 2005  'put' entry point, new names, 12003 
*              ftp error handling (on ftp write permission)
*              405 http error (method not allowed)
*     Mar 12, 2006  Internal authorization via InternetErrorDlg()
*              and Unauthorized (401) handling.
*     Jun 10, 2006 Caption text option for Resume download
*              MessageBox
*     Jun 24, 2006 HEAD method, silent mode clean up
*     Sep 05, 2006 Center dialog code from Backland
*     Sep 07, 2006 NSISdl crash fix /Backland idea/
*     Sep 08, 2006 post as dll entry point.
*     Sep 21, 2006 parent dlg progr.bar style and font, 
*              nocancel via ws_sysmenu
*     Sep 22, 2006 current lang IDCANCEL text, /canceltext
*              and /useragent options
*     Sep 24, 2006 .onInit improvements and defaults
*     Nov 11, 2006 FTP path creation, root|current dir mgmt
*     Jan 01, 2007 Global char[] cleanup, GetLastError() to 
*              status string on ERR_DIALOG, few MSVCRT replaces
*     Jan 13, 2007 /HEADER option added
*     Jan 28, 2007 _open -> CreateFile and related
*     Feb 18, 2007 Speed calculating improved (pauses),
*              /popup text parameter to hide URL
*     Jun 07, 2007 Local file truncation added for download
*              (CREATE_ALWAYS)
*     Jun 11, 2007 FTP download permitted even if server rejects
*              SIZE request (ProFTPD). 
*     Aug 11, 2007 Backland' fix for progress bar redraw/style
*              issue in NSISdl display mode.
*******************************************************/


#define _WIN32_WINNT 0x0500

#include <windows.h>
#include <wininet.h>
#include <commctrl.h>
#include "..\exdll\exdll.h"
#include "resource.h"

#include <stdio.h>

// IE 4 safety and VS 6 compatibility
typedef BOOL (__stdcall *FTP_CMD)(HINTERNET,BOOL,DWORD,LPCSTR,DWORD,HINTERNET *);
FTP_CMD myFtpCommand;

#define PLUGIN_NAME "Inetc plug-in"
#define INETC_USERAGENT "NSIS_Inetc (Mozilla)"
#define PB_RANGE 400
#define PAUSE1_SEC 2 // transfer error indication time, for reget only
#define PAUSE2_SEC 3 // paused state time, increase this if need (60?)
#define PAUSE3_SEC 1 // pause after resume button pressed
#define NOT_AVAILABLE 0xffffffff
#define POST_HEADER "Content-Type: application/x-www-form-urlencoded"
#define INTERNAL_OK 0xFFEE
#define PROGRESS_MS 1000

enum STATUS_CODES {
   ST_OK = 0,
   ST_CONNECTING,
   ST_DOWNLOAD,
   ST_CANCELLED,
   ST_URLOPEN,
   ST_PAUSE,
   ERR_TERMINATED,
   ERR_DIALOG,
   ERR_INETOPEN,
   ERR_URLOPEN,
   ERR_TRANSFER,
   ERR_FILEOPEN,
   ERR_FILEWRITE,
   ERR_FILEREAD,
   ERR_REGET,
   ERR_CONNECT,
   ERR_OPENREQUEST,
   ERR_SENDREQUEST,
   ERR_CRACKURL,
   ERR_NOTFOUND,
   ERR_THREAD,
   ERR_PROXY,
   ERR_FORBIDDEN,
   ERR_NOTALLOWED,
   ERR_REQUEST,
   ERR_SERVER,
   ERR_AUTH,
   ERR_CREATEDIR,
   ERR_PATH
};


static char szStatus[][32] = {
   "OK", "Connecting", "Downloading", "Cancelled", "Connecting", //"Opening URL",
   "Reconnect Pause", "Terminated", "Dialog Error", "Open Internet Error",
   "Open URL Error", "Transfer Error", "File Open Error", "File Write Error", "File Read Error",
   "Reget Error", "Connection Error", "OpenRequest Error", "SendRequest Error",
   "URL Parts Error", "File Not Found (404)", "CreateThread Error", "Proxy Error (407)",
   "Access Forbidden (403)", "Not Allowed (405)", "Request Error", "Server Error",
   "Unauthorized (401)", "FtpCreateDir failed (550)", "Error FTP path (550)"};

HINSTANCE g_hInstance;
char fn[MAX_PATH]="",
     *url = NULL,
     *szPost = NULL,
     *szProxy = NULL,
     *szHeader = NULL,
     szCancel[64]="",
     szBanner[256]="",
     szAlias[256]="",
     szCaption[128]="",
     szUsername[128]="",
     szPassword[128]="",
     szUserAgent[128]="",
     szResume[256] = "Your internet connection seems to be not permitted or dropped out!\nPlease reconnect and click Retry to resume installation.";

int status;
DWORD cnt = 0,
      fs = 0,
      timeout = 0;
DWORD startTime, transfStart, openType;
bool silent, popup, resume, nocancel, noproxy;

HWND childwnd;
HWND hDlg;
bool fput = false, fhead = false;


/*****************************************************
 * FUNCTION NAME: sf(HWND)
 * PURPOSE: 
 *    moves HWND to top and activates it
 * SPECIAL CONSIDERATIONS:
 *    commented because annoying
 *****************************************************/
/*
void sf(HWND hw)
{
   DWORD ctid = GetCurrentThreadId();
   DWORD ftid = GetWindowThreadProcessId(GetForegroundWindow(), NULL);
   AttachThreadInput(ftid, ctid, TRUE);
   SetForegroundWindow(hw);
   AttachThreadInput(ftid, ctid, FALSE);
}
*/

static char szUrl[64] = "";
static char szDownloading[64] = "Downloading %s";
static char szConnecting[64] = "Connecting ...";
static char szSecond[64] = "second";
static char szMinute[32] = "minute";
static char szHour[32] = "hour";
static char szPlural[32] = "s";
static char szProgress[128] = "%dkB (%d%%) of %dkB @ %d.%01dkB/s";
static char szRemaining[64] = " (%d %s%s remaining)";



/*****************************************************
 * FUNCTION NAME: fileTransfer()
 * PURPOSE: 
 *    http/ftp file transfer itself
 *    for any protocol and both directions I guess
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
void fileTransfer(HANDLE localFile,
                  HINTERNET hFile)
{
   byte data_buf[1024*8];
   byte *dw;
   DWORD rslt = 0;
   DWORD bytesDone;

   status = ST_DOWNLOAD;
   while(status == ST_DOWNLOAD)
   {
      if(fput)
      {
         if(!ReadFile(localFile, data_buf, rslt = sizeof(data_buf), &bytesDone, NULL))
         {
            status = ERR_FILEREAD;
            break;
         }
         if(bytesDone == 0) // EOF reached
         {
               status = ST_OK;
               break;
         }
         while(bytesDone > 0)
         {
            dw = data_buf;
            if(!InternetWriteFile(hFile, dw, bytesDone, &rslt) || rslt == 0)
            {
               status = ERR_TRANSFER;
               break;
            }
            dw += rslt;
            cnt += rslt;
            bytesDone -= rslt;
         }
      }
      else
      {
         if(!InternetReadFile(hFile, data_buf, sizeof(data_buf), &rslt))
         {
            status = ERR_TRANSFER;
            break;
         }
         if(rslt == 0) // EOF reached
         {
               status = ST_OK;
               break;
         }
         if(!WriteFile(localFile, data_buf, rslt, &bytesDone, NULL) ||
            rslt != bytesDone)
         {
               status = ERR_FILEWRITE;
               break;
         }
         cnt += rslt;
      }
   }
}

/*****************************************************
 * FUNCTION NAME: mySendRequest()
 * PURPOSE: 
 *    HttpSendRequestEx() sends headers only - for PUT
 *    We can use InetWriteFile for POST headers I guess
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
int mySendRequest(HINTERNET hFile)
{
   INTERNET_BUFFERS BufferIn = {0};
   if(fput)
   {
      BufferIn.dwStructSize = sizeof( INTERNET_BUFFERS );
      BufferIn.dwBufferTotal = fs;
      return HttpSendRequestEx( hFile, &BufferIn, NULL, HSR_INITIATE, 0);
   }
   return HttpSendRequest(hFile, NULL, 0, szPost, szPost ? lstrlen(szPost) : 0);
}

/*****************************************************
 * FUNCTION NAME: queryStatus()
 * PURPOSE: 
 *    http status code comes before download (get) and
 *    after upload (put), so this is called from 2 places
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
void queryStatus(HINTERNET hFile)
{
   char buf[256] = "";
   DWORD rslt;
   if(HttpQueryInfo(hFile, HTTP_QUERY_STATUS_CODE,
                    buf, &(rslt = sizeof(buf)), NULL))
   {
      buf[3] = 0;
      if(lstrcmp(buf, "401") == 0)
                     status = ERR_AUTH;
      else if(lstrcmp(buf, "403") == 0)
                     status = ERR_FORBIDDEN;
      else if(lstrcmp(buf, "404") == 0)
                     status = ERR_NOTFOUND;
      else if(lstrcmp(buf, "407") == 0)
                     status = ERR_PROXY;
      else if(lstrcmp(buf, "405") == 0)
                     status = ERR_NOTALLOWED;
      else if(*buf == '4')
      {
         status = ERR_REQUEST;
         wsprintf(szStatus[status] + lstrlen(szStatus[status]), " (%s)", buf);
      }
      else if(*buf == '5')
      {
         status = ERR_SERVER;
         wsprintf(szStatus[status] + lstrlen(szStatus[status]), " (%s)", buf);
      }
   }
}

/*****************************************************
 * FUNCTION NAME: openInetFile()
 * PURPOSE: 
 *    file open, size request, re-get lseek
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
HINTERNET openInetFile(HINTERNET hConn,
                       INTERNET_SCHEME nScheme,
                       char *path)
{
   char buf[256] = "", *movp;
   HINTERNET hFile;
   DWORD rslt, err, gle;
   bool req_sent_ok = false;
   status = ST_URLOPEN;
   if(nScheme == INTERNET_SCHEME_FTP)
   {
/* reads connection / auth responce info and cleares buffer this way */
      InternetGetLastResponseInfo(&err, buf, &(rslt = sizeof(buf)));
      if(cnt == 0)
      {
         if(!fput) // we know local file size already
         {
/* too clever myFtpCommand returnes false on the valid "550 Not found/Not permitted" server answer,
   to read answer I had to ignory returned false (!= 999999) :-( 
   GetLastError also possible, but MSDN description of codes is very limited */
            wsprintf(buf, "SIZE %s", path + 1);
            if(myFtpCommand != NULL &&
               myFtpCommand(hConn, false, FTP_TRANSFER_TYPE_ASCII, buf, 0, &hFile) != 9999 &&
               memset(buf, 0, sizeof(buf)) != NULL &&
               InternetGetLastResponseInfo(&err, buf, &(rslt = sizeof(buf))))
            {
               if(strstr(buf, "213 "))
               {
                  fs = strtol(strchr(buf, ' ') + 1, NULL, 0);
               }
/* stupied ProFTPD
               else if(strstr(buf, "550 "))
               {
                  status = ERR_SIZE_NOT_PERMITTED;
                  return NULL;
               }
*/
            }
            if(fs == 0)
            {
               fs = NOT_AVAILABLE;
            }

         }
      }
      else
      {
         wsprintf(buf, "REST %d", cnt);
         if(myFtpCommand == NULL ||
            !myFtpCommand(hConn, false, FTP_TRANSFER_TYPE_BINARY, buf, 0, &hFile) ||
            memset(buf, 0, sizeof(buf)) == NULL ||
            !InternetGetLastResponseInfo(&err, buf, &(rslt = sizeof(buf))) ||
            (strstr(buf, "350") == NULL && strstr(buf, "110") == NULL))
         {
            status = ERR_REGET;
            return NULL;
         }
      }
      if((hFile = FtpOpenFile(hConn, path + 1, fput ? GENERIC_WRITE : GENERIC_READ,
            FTP_TRANSFER_TYPE_BINARY|INTERNET_FLAG_RELOAD,0)) == NULL)
      {
         gle = GetLastError();
         *buf = 0;
         InternetGetLastResponseInfo(&err, buf, &(rslt = sizeof(buf)));
// wrong path - dir may not exist
         if(fput && strstr(buf, "550") != NULL)
         {

		      movp = path + 1;
            if(*movp == '/') movp++; // don't need to creat root
		      while(strchr(movp, '/'))
            {
               *strchr(movp,'/') = 0;
			      FtpCreateDirectory(hConn, path + 1);
			      InternetGetLastResponseInfo(&err, buf, &(rslt = sizeof(buf)));
               *(movp + lstrlen(movp)) = '/';
			      movp = strchr(movp, '/') + 1;
		      }
            if(status != ERR_CREATEDIR &&
               (hFile = FtpOpenFile(hConn, path + 1, GENERIC_WRITE,
               FTP_TRANSFER_TYPE_BINARY|INTERNET_FLAG_RELOAD,0)) == NULL)
	         {
               status = ERR_PATH;
         		if(InternetGetLastResponseInfo(&err, buf, &(rslt = sizeof(buf))))
                  lstrcpyn(szStatus[status], buf, 31);
	         }         
         }
// firewall related error, let's give user time to disable it
         else if(gle == 12003)
         {
            status = ERR_SERVER;
            if(*buf)
               lstrcpyn(szStatus[status], buf, 31);
         }
// timeout (firewall or dropped connection problem)
         else if(gle == 12002)
         {
            if(!silent)
               resume = true;
            status = ERR_URLOPEN;
         }
      }
   }
   else
   {
      if((hFile = HttpOpenRequest(hConn, fput ? "PUT" : (fhead ? "HEAD" : (szPost ? "POST" : NULL)),
         path, NULL, NULL, NULL,
         INTERNET_FLAG_RELOAD | INTERNET_FLAG_KEEP_CONNECTION | 
         (nScheme == INTERNET_SCHEME_HTTPS ? INTERNET_FLAG_SECURE |
         INTERNET_FLAG_IGNORE_CERT_CN_INVALID | INTERNET_FLAG_IGNORE_CERT_DATE_INVALID |
         INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP | INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS : 0), 0)) != NULL)
      {

         if(*szUsername != 0)
            InternetSetOption(hFile, INTERNET_OPTION_PROXY_USERNAME, szUsername, lstrlen(szUsername) + 1);
         if(*szPassword != 0)
            InternetSetOption(hFile, INTERNET_OPTION_PROXY_PASSWORD, szPassword, sizeof(szPassword));
         if(szPost != NULL)
            HttpAddRequestHeaders(hFile, POST_HEADER, lstrlen(POST_HEADER),
               HTTP_ADDREQ_FLAG_ADD | HTTP_ADDREQ_FLAG_REPLACE);
         if(szHeader != NULL)
            HttpAddRequestHeaders(hFile, szHeader, lstrlen(szHeader),
               HTTP_ADDREQ_FLAG_ADD | HTTP_ADDREQ_FLAG_REPLACE);
         if(fput)
         {
            wsprintf(buf, "Content-Type: octet-stream\nContent-Length: %d", fs);
            /*MessageBox(childwnd, buf, "", 0);*/
            HttpAddRequestHeaders(hFile, buf, lstrlen(buf),
               HTTP_ADDREQ_FLAG_ADD | HTTP_ADDREQ_FLAG_REPLACE);
         }
// on Win98 security flags may be setten after first (failed) Send only. XP works without this.
         if(nScheme == INTERNET_SCHEME_HTTPS)
         {
            if(!mySendRequest(hFile))
            {
               InternetQueryOption (hFile, INTERNET_OPTION_SECURITY_FLAGS,
                  (LPVOID)&rslt, &(err = sizeof(rslt)));
               rslt |= SECURITY_FLAG_IGNORE_UNKNOWN_CA | SECURITY_FLAG_IGNORE_REVOCATION;
               InternetSetOption (hFile, INTERNET_OPTION_SECURITY_FLAGS,
                              &rslt, sizeof(rslt) );
            }
            else req_sent_ok = true;
         }
// Request answer may be after optional second Send
resend:
         if(req_sent_ok || mySendRequest(hFile))
         {
            if(!fput)
            {
               if(cnt == 0)
               {
                  queryStatus(hFile);
                  if(HttpQueryInfo(hFile, HTTP_QUERY_CONTENT_LENGTH, buf,
                                   &(rslt = sizeof(buf)), NULL))
                     fs = strtoul(buf, NULL, 0);
                  else fs = NOT_AVAILABLE;
               }
               else
               {
                  if(!InternetSetFilePointer(hFile, cnt, NULL, FILE_BEGIN, 0))
                  {
                     status = ERR_REGET;
                  }
               }
            }
         }
         else
         {
            status = ERR_SENDREQUEST;
         }
         if(!silent && (status == ERR_PROXY || status == ERR_AUTH))
         {
            rslt = InternetErrorDlg(hDlg, hFile, ERROR_SUCCESS, 
                           FLAGS_ERROR_UI_FILTER_FOR_ERRORS | 
                           FLAGS_ERROR_UI_FLAGS_CHANGE_OPTIONS |
                           FLAGS_ERROR_UI_FLAGS_GENERATE_DATA,
                           NULL);
            if (rslt != ERROR_CANCELLED)
            {
               status = ST_URLOPEN;
               req_sent_ok = false;
               goto resend;
            }
         }
      }
      else status = ERR_OPENREQUEST;
   }
   if(status != ST_URLOPEN && hFile != NULL)
   {
      InternetCloseHandle(hFile);
      hFile = NULL;
   }
   return hFile;
}

/*****************************************************
 * FUNCTION NAME: inetTransfer()
 * PURPOSE: 
 *    http/ftp file transfer
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
DWORD __stdcall inetTransfer(void *hw)
{
   HINTERNET hSes, hConn, hFile;
   HINSTANCE hInstance = NULL;
   HANDLE localFile = NULL;
   HWND hDlg = (HWND)hw;
   DWORD lastCnt, rslt;
   char hdr[2048];
   char *host = (char*)GlobalAlloc(GPTR, g_stringsize),
        *path = (char*)GlobalAlloc(GPTR, g_stringsize),
        *user = (char*)GlobalAlloc(GPTR, g_stringsize),
        *passwd = (char*)GlobalAlloc(GPTR, g_stringsize),
        *params = (char*)GlobalAlloc(GPTR, g_stringsize);

   URL_COMPONENTS uc = {sizeof(URL_COMPONENTS), NULL, 0,
      (INTERNET_SCHEME)0, host, g_stringsize, 0 , user, g_stringsize,
      passwd, g_stringsize, path, g_stringsize, params, g_stringsize};

   if((hSes = InternetOpen(*szUserAgent == 0 ? INETC_USERAGENT : szUserAgent, openType, szProxy, NULL, 0)) != NULL)
   {
      if(InternetQueryOption(hSes, INTERNET_OPTION_CONNECTED_STATE, &(rslt=0),
         &(lastCnt=sizeof(DWORD))) &&
         (rslt & INTERNET_STATE_DISCONNECTED_BY_USER))
      {
         INTERNET_CONNECTED_INFO ci = {INTERNET_STATE_CONNECTED, 0};
         InternetSetOption(hSes, 
            INTERNET_OPTION_CONNECTED_STATE, &ci, sizeof(ci));
      }
      if(timeout > 0)
         lastCnt = InternetSetOption(hSes, INTERNET_OPTION_CONNECT_TIMEOUT, &timeout, sizeof(timeout));
// 60 sec WinInet.dll detach delay on socket time_wait fix
//      if(hInstance = GetModuleHandle("wininet.dll"))
      if(hInstance = LoadLibrary("wininet.dll"))
         myFtpCommand = (FTP_CMD)GetProcAddress(hInstance, "FtpCommandA");
      while(!popstring(url) && lstrcmpi(url, "/end") != 0)
      {
//         sf(hDlg);
         if(popstring(fn) != 0 || lstrcmpi(url, "/end") == 0) break;
         status = ST_CONNECTING;
         cnt = fs = *host = *user = *passwd = *path = *params = 0;
         PostMessage(hDlg, WM_TIMER, 1, 0); // show url & fn, do it sync
         if((localFile = CreateFile(fn, fput ? GENERIC_READ : GENERIC_WRITE, FILE_SHARE_READ,
            NULL, fput ? OPEN_EXISTING : CREATE_ALWAYS, 0, NULL)) != NULL)
         {
            uc.dwHostNameLength = uc.dwUserNameLength = uc.dwPasswordLength =
               uc.dwUrlPathLength = uc.dwExtraInfoLength = g_stringsize;
            if(fput)
            {
               GetFileSize(localFile, &fs);
            }
            if(InternetCrackUrl(url, 0, ICU_ESCAPE , &uc))
            {
               lstrcat(path, params);
               transfStart = GetTickCount();
               do
               {
// re-PUT to already deleted tmp file on http server is not possible.
// the same with POST - must re-send data to server. for 'resume' loop
                  if((fput && uc.nScheme != INTERNET_SCHEME_FTP) || szPost)
                  {
                     cnt = 0;
                     SetFilePointer(localFile, 0, NULL, SEEK_SET);
                  }
                  status = ST_CONNECTING;
                  lastCnt = cnt;
                  if((hConn = InternetConnect(hSes, host, uc.nPort,
                     lstrlen(user) > 0 ? user : NULL,
                     lstrlen(passwd) > 0 ? passwd : NULL,
                     uc.nScheme == INTERNET_SCHEME_FTP ? INTERNET_SERVICE_FTP : INTERNET_SERVICE_HTTP,
                     uc.nScheme == INTERNET_SCHEME_FTP ? INTERNET_FLAG_PASSIVE : 0, 0)) != NULL)
                  {
                     if((hFile = openInetFile(hConn, uc.nScheme, path)) != NULL)
                     {
                        if(fhead)
                        {// repeating calls clears headers..
                            HttpQueryInfo(hFile, HTTP_QUERY_RAW_HEADERS_CRLF, hdr, &(rslt=2048), NULL);
                            WriteFile(localFile, hdr, rslt, &lastCnt, NULL);
                            status = ST_OK;
                        }
                        else
                        {
                           fileTransfer(localFile, hFile);
                           if(fput && uc.nScheme != INTERNET_SCHEME_FTP)
                           {
                              HttpEndRequest(hFile, NULL, 0, 0);
                              queryStatus(hFile);
                           }
                        }
                        InternetCloseHandle(hFile);
                     }
                     InternetCloseHandle(hConn);
                  }
                  else
                  {
                     rslt = GetLastError();
                     if((rslt == 12003 || rslt == 12002) && !silent)
                        resume = true;
                     status = ERR_CONNECT;
                  }
// Sleep(2000);
               } while(((!fput || uc.nScheme == INTERNET_SCHEME_FTP) &&
                  cnt > lastCnt &&
                  status == ERR_TRANSFER &&
                  SleepEx(PAUSE1_SEC * 1000, false) == 0 &&
                  (status = ST_PAUSE) != ST_OK &&
                  SleepEx(PAUSE2_SEC * 1000, false) == 0)
                  || (resume &&
                  status != ST_OK &&
                  status != ST_CANCELLED &&
                  status != ERR_NOTFOUND &&
                  ShowWindow(hDlg, SW_HIDE) != -1 &&
//                  MessageBox(hDlg, szResume, szCaption, MB_RETRYCANCEL|MB_ICONWARNING) == IDRETRY &&
                  MessageBox(GetParent(hDlg), szResume, szCaption, MB_RETRYCANCEL|MB_ICONWARNING) == IDRETRY &&
                  (status = ST_PAUSE) != ST_OK &&
                  ShowWindow(hDlg, silent ? SW_HIDE : SW_SHOW) == false &&
                  SleepEx(PAUSE3_SEC * 1000, false) == 0));
            }
            else status = ERR_CRACKURL;
            CloseHandle(localFile);
            if(!fput && status != ST_OK)
            {
               DeleteFile(fn);
               break;
            }
         }
         else status = ERR_FILEOPEN;
      }
      InternetCloseHandle(hSes);
   }
   else status = ERR_INETOPEN;
   GlobalFree(host);
   GlobalFree(path);
   GlobalFree(user);
   GlobalFree(passwd);
   GlobalFree(params);
   if(IsWindow(hDlg))
      PostMessage(hDlg, WM_COMMAND, MAKELONG(IDOK, INTERNAL_OK), 0);
   return status;
}

/*****************************************************
 * FUNCTION NAME: fsFormat()
 * PURPOSE: 
 *    formats DWORD (max 4 GB) file size for dialog, big MB
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
void fsFormat(DWORD bfs,
              char *b)
{
   if(bfs == NOT_AVAILABLE)
      lstrcpy(b, "???");
   else if(bfs == 0)
      lstrcpy(b, "0");
   else if(bfs < 10 * 1024)
      wsprintf(b, "%u bytes", bfs);
   else if(bfs < 10 * 1024 * 1024)
      wsprintf(b, "%u kB", bfs / 1024);
   else wsprintf(b, "%u MB", (bfs / 1024 / 1024));
}


/*****************************************************
 * FUNCTION NAME: progress_callback
 * PURPOSE: 
 *    old-style progress bar text updates
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/

void progress_callback(void)
{
   char buf[1024] = "", b[1024] = "";
   int time_sofar = max(1, (GetTickCount() - transfStart) / 1000);
   int bps = cnt / time_sofar;
   int remain = (cnt > 0 && fs != NOT_AVAILABLE) ? (MulDiv(time_sofar, fs, cnt) - time_sofar) : 0;
   char *rtext=szSecond;
   if(remain < 0) remain = 0;
   if (remain >= 60)
   {
      remain/=60;
      rtext=szMinute;
      if (remain >= 60)
      {
         remain/=60;
         rtext=szHour;
      }
   }
   wsprintf(buf,
            szProgress,
            cnt/1024,
            fs > 0 && fs != NOT_AVAILABLE ? MulDiv(100, cnt, fs) : 0,
            fs != NOT_AVAILABLE ? fs/1024 : 0,
            bps/1024,((bps*10)/1024)%10
            );
   if (remain) wsprintf(buf+lstrlen(buf),
                        szRemaining,
                        remain,
                        rtext,
                        remain==1?"":szPlural
                        );
   SetDlgItemText(hDlg, IDC_STATIC1, (cnt == 0 || status == ST_CONNECTING) ? szConnecting : buf);
   SendMessage(GetDlgItem(hDlg, IDC_PROGRESS1), PBM_SETPOS, fs > 0 && fs != NOT_AVAILABLE ?
      MulDiv(cnt, PB_RANGE, fs) : 0, 0);
   wsprintf(buf,
            szDownloading,
            strchr(fn, '\\') ? strrchr(fn, '\\') + 1 : fn
            );
   HWND hwndS = GetDlgItem(childwnd, 1006);
   if(!silent && hwndS != NULL && IsWindow(hwndS))
   {
      GetWindowText(hwndS, b, sizeof(b));
      if(lstrcmp(b, buf) != 0)
         SetWindowText(hwndS, buf);
   }
}

/*****************************************************
 * FUNCTION NAME: onTimer()
 * PURPOSE: 
 *    updates text fields every second
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
void onTimer(HWND hDlg)
{
   char b[128];
   DWORD ct = (GetTickCount() - transfStart) / 1000,
      tt = (GetTickCount() - startTime) / 1000;
// dialog window caption
   wsprintf(b,  "%s - %s", szCaption, szStatus[status]);
   if(fs > 0 && fs != NOT_AVAILABLE && status == ST_DOWNLOAD)
   {
      wsprintf(b + lstrlen(b), " %d%%", MulDiv(100, cnt, fs));
   }
   if(*szBanner == 0) SetWindowText(hDlg, b);
// current file and url
   SetDlgItemText(hDlg, IDC_STATIC1, *szAlias ? szAlias : url);
   SetDlgItemText(hDlg, IDC_STATIC2, /*strchr(fn, '\\') ? strrchr(fn, '\\') + 1 : */fn);
// bytes done and rate
   if(cnt > 0)
   {
      fsFormat(cnt, b);
      if(ct > 1 && status == ST_DOWNLOAD)
      {
         lstrcat(b, "   ( ");
         fsFormat(cnt / ct, b + lstrlen(b));
         lstrcat(b, "/sec )");
      }
   }
   else *b = 0;
   SetDlgItemText(hDlg, IDC_STATIC3, b);
// total download time
   wsprintf(b, "%d:%02d:%02d", tt / 3600, (tt / 60) % 60, tt % 60);
   SetDlgItemText(hDlg, IDC_STATIC6, b);
// file size, time remaining, progress bar
   if(fs == NOT_AVAILABLE)
   {
      SetWindowText(GetDlgItem(hDlg, IDC_STATIC5), "Not Available");
      SetWindowText(GetDlgItem(hDlg, IDC_STATIC4), "Unknown");
//      ShowWindow(GetDlgItem(hDlg, IDC_PROGRESS1), SW_HIDE);
      SendDlgItemMessage(hDlg, IDC_PROGRESS1, PBM_SETPOS, 0, 0);
   }
   else if(fs > 0)
   {
      fsFormat(fs, b);
      SetDlgItemText(hDlg, IDC_STATIC5, b);
      ShowWindow(GetDlgItem(hDlg, IDC_PROGRESS1), SW_NORMAL);
      SendDlgItemMessage(hDlg, IDC_PROGRESS1, PBM_SETPOS, MulDiv(cnt, PB_RANGE, fs), 0);
      if(cnt > 5000)
      {
         ct = MulDiv(fs - cnt, ct, cnt);
         wsprintf(b, "%d:%02d:%02d", ct / 3600, (ct / 60) % 60, ct % 60);
      }
      else *b = 0;
      SetWindowText(GetDlgItem(hDlg, IDC_STATIC4), b);
   }
   else
   {
      SetDlgItemText(hDlg, IDC_STATIC5, "");
      SetDlgItemText(hDlg, IDC_STATIC4, "");
      SendDlgItemMessage(hDlg, IDC_PROGRESS1, PBM_SETPOS, 0, 0);
   }
}

/*****************************************************
 * FUNCTION NAME: timeRemaining()
 * PURPOSE: 
 *    Returns a string of the remaining time for the
 *	  download.
 *
 *****************************************************/
extern "C"
void __declspec(dllexport) timeRemaining(HWND hwndParent,
										 int string_size,
                                         char *variables,
                                         stack_t **stacktop,
                                         extra_parameters *extra
										)
{ 
   char b[128];
   DWORD ct = (GetTickCount() - transfStart) / 1000;

   EXDLL_INIT();

   wsprintf(b, "%d, %d, %d", fs, cnt, ct);
   pushstring(b);
   if((fs != NOT_AVAILABLE) && (fs > 0) && (cnt > 5000))
   {
		ct = MulDiv(fs - cnt, ct, cnt);
        wsprintf(b, "%d:%02d:%02d", ct / 3600, (ct / 60) % 60, ct % 60);
	    pushstring(b);

   } else  pushstring("Unknown");
}

extern "C"
void __declspec(dllexport) cancel(HWND hwndParent,
										 int string_size,
                                         char *variables,
                                         stack_t **stacktop,
                                         extra_parameters *extra
										)
{
    status = ST_CANCELLED;
}

/*****************************************************
 * FUNCTION NAME: centerDlg()
 * PURPOSE: 
 *    centers dlg on NSIS parent 
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
void centerDlg(HWND hDlg)
{
   HWND hwndParent = GetParent(hDlg);
   RECT nsisRect, dlgRect, waRect;
   int dlgX, dlgY, dlgWidth, dlgHeight;

   if(hwndParent == NULL || silent)
      return;
   if(popup)
      GetWindowRect(hwndParent, &nsisRect);
   else GetClientRect(hwndParent, &nsisRect);
   GetWindowRect(hDlg, &dlgRect);

   dlgWidth = dlgRect.right - dlgRect.left;
   dlgHeight = dlgRect.bottom - dlgRect.top;
   dlgX = (nsisRect.left + nsisRect.right - dlgWidth) / 2;
   dlgY = (nsisRect.top + nsisRect.bottom - dlgHeight) / 2;

   if(popup)
   {
	   SystemParametersInfo(SPI_GETWORKAREA, 0, &waRect, 0);
      if(dlgX > waRect.right - dlgWidth)
         dlgX = waRect.right - dlgWidth;
      if(dlgX < waRect.left) dlgX = waRect.left;
      if(dlgY > waRect.bottom - dlgHeight)
         dlgY = waRect.bottom - dlgHeight;
      if(dlgY < waRect.top) dlgY = waRect.top;
   }
   else dlgY += 20;

   SetWindowPos(hDlg, HWND_TOP, dlgX, dlgY, 0, 0, SWP_NOSIZE);
}

/*****************************************************
 * FUNCTION NAME: onInitDlg()
 * PURPOSE: 
 *    dlg init
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
void onInitDlg(HWND hDlg)
{
   HFONT hFont;
   HWND hPrbNew;
   HWND hPrbOld;
   HWND hCan = GetDlgItem(hDlg, IDCANCEL);
//   char s[32];

   if(childwnd)
   {
      hPrbNew = GetDlgItem(hDlg, IDC_PROGRESS1);
      hPrbOld = GetDlgItem(childwnd, 0x3ec);

// Backland' fix for progress bar redraw/style issue.
// Original bar may be hidden because of interfernce with other plug-ins.
		LONG prbStyle = WS_VISIBLE | WS_CHILD | WS_CLIPSIBLINGS | WS_CLIPCHILDREN;
		if(hPrbOld != NULL/* && GetClassName(hPrbOld, s, sizeof(s)) > 0 && lstrcmpi(s, "msctl_progress32") == 0*/) 
		{ 
			prbStyle |= GetWindowLong(hPrbOld, GWL_STYLE); 
		} 
		SetWindowLong(hPrbNew, GWL_STYLE, prbStyle); 

      if(!popup)
      {
         if((hFont = (HFONT)SendMessage(childwnd, WM_GETFONT, 0, 0)) != NULL)
         {
            SendDlgItemMessage(hDlg, IDC_STATIC1, WM_SETFONT, (WPARAM)hFont, 0);
            SendDlgItemMessage(hDlg, IDCANCEL, WM_SETFONT, (WPARAM)hFont, 0);
         }
         if(*szCancel == 0)
            GetWindowText(GetDlgItem(GetParent(childwnd), IDCANCEL), szCancel, sizeof(szCancel));
         SetWindowText(hCan, szCancel);
         SetWindowPos(hPrbNew, HWND_TOP, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE);
      }
   }

   if(nocancel)
   {
      if(hCan != NULL)
         ShowWindow(hCan, SW_HIDE);
      if(popup)
         SetWindowLong(hDlg, GWL_STYLE, GetWindowLong(hDlg, GWL_STYLE) ^ WS_SYSMENU);
   }
   SendDlgItemMessage(hDlg, IDC_PROGRESS1, PBM_SETRANGE,
         0, MAKELPARAM(0, PB_RANGE));
   if(*szBanner != 0)
   {
      SendDlgItemMessage(hDlg, IDC_STATIC13, STM_SETICON,
            (WPARAM)LoadIcon(GetModuleHandle(NULL), MAKEINTRESOURCE(103)), 0);
      SetDlgItemText(hDlg, IDC_STATIC12, szBanner);
      if(*szCaption != 0) SetWindowText(hDlg, szCaption);
   }
   SetTimer(hDlg, 1, 1000, NULL);
   if(*szUrl != 0)
   {
      SetDlgItemText(hDlg, IDC_STATIC20, szUrl);
      SetDlgItemText(hDlg, IDC_STATIC21, szDownloading);
      SetDlgItemText(hDlg, IDC_STATIC22, szConnecting);
      SetDlgItemText(hDlg, IDC_STATIC23, szProgress);
      SetDlgItemText(hDlg, IDC_STATIC24, szSecond);
      SetDlgItemText(hDlg, IDC_STATIC25, szRemaining);
   }
}

/*****************************************************
 * FUNCTION NAME: dlgProc()
 * PURPOSE: 
 *    dlg message handling procedure
 * SPECIAL CONSIDERATIONS:
 *    todo: better dialog design
 *****************************************************/
BOOL WINAPI dlgProc(HWND hDlg,
                    UINT message,
                    WPARAM wParam,
                    LPARAM lParam )  {
   switch(message)    {
   case WM_INITDIALOG:
      onInitDlg(hDlg);
      centerDlg(hDlg);
      break;
   case WM_PAINT:
/* child dialog redraw problem. return false is important */
      RedrawWindow(GetDlgItem(hDlg, IDC_STATIC1), NULL, NULL, RDW_INVALIDATE);
      RedrawWindow(GetDlgItem(hDlg, IDCANCEL), NULL, NULL, RDW_INVALIDATE);
      RedrawWindow(GetDlgItem(hDlg, IDC_PROGRESS1), NULL, NULL, RDW_INVALIDATE);
      UpdateWindow(GetDlgItem(hDlg, IDC_STATIC1));
      UpdateWindow(GetDlgItem(hDlg, IDCANCEL));
      UpdateWindow(GetDlgItem(hDlg, IDC_PROGRESS1));
      return false;
   case WM_TIMER:
      if(!silent && IsWindow(hDlg))
      {
//  long connection period and paused state updates
         if(status != ST_DOWNLOAD && GetTickCount() - transfStart > PROGRESS_MS)
            transfStart += PROGRESS_MS;
         if(popup) onTimer(hDlg);
         else progress_callback();
         RedrawWindow(GetDlgItem(hDlg, IDC_STATIC1), NULL, NULL, RDW_INVALIDATE);
         RedrawWindow(GetDlgItem(hDlg, IDCANCEL), NULL, NULL, RDW_INVALIDATE);
         RedrawWindow(GetDlgItem(hDlg, IDC_PROGRESS1), NULL, NULL, RDW_INVALIDATE);
      }
      break;
   case WM_COMMAND:
      switch(LOWORD(wParam))
      {
      case IDCANCEL:
         if(nocancel) break;
         status = ST_CANCELLED;
      case IDOK:
         if(status != ST_CANCELLED && HIWORD(wParam) != INTERNAL_OK) break;
// otherwise in the silent mode next banner windows may go to background
//         if(silent) sf(hDlg);
//         Sleep(3000);
         KillTimer(hDlg, 1);
         DestroyWindow(hDlg);
         break;
      }
   default: return false;
   }
   return true;
}

 /*****************************************************
 * FUNCTION NAME: get()
 * PURPOSE: 
 *    http/https/ftp file download entry point
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
extern "C"
void __declspec(dllexport) get(HWND hwndParent,
                                int string_size,
                                char *variables,
                                stack_t **stacktop,
                                extra_parameters *extra
                                )
{
   HANDLE hThread;
   DWORD dwThreadId, dwStyle = 0;
   MSG msg;

   EXDLL_INIT();
   if(szPost)
      popstring(szPost);

// for /nounload plug-un calls - global vars clean up
   silent = popup = resume = nocancel = noproxy = false;
   myFtpCommand = NULL;
   openType = INTERNET_OPEN_TYPE_PRECONFIG;
   status = ST_CONNECTING;
   *szBanner = *szCaption = *szUsername = *szPassword = *szCancel = *szUserAgent = *szAlias = 0;

   url = (char*)GlobalAlloc(GPTR, string_size);
// global silent option
   if(extra->exec_flags->silent != 0)
      silent = true;
// we must take this from stack, or push url back
   while(!popstring(url) && *url == '/')
   {
      if(lstrcmpi(url, "/silent") == 0)
         silent = true;
      else if(lstrcmpi(url, "/caption") == 0)
         popstring(szCaption);
      else if(lstrcmpi(url, "/username") == 0)
         popstring(szUsername);
      else if(lstrcmpi(url, "/password") == 0)
         popstring(szPassword);
      else if(lstrcmpi(url, "/nocancel") == 0)
         nocancel = true;
      else if(lstrcmpi(url, "/noproxy") == 0)
         openType = INTERNET_OPEN_TYPE_DIRECT;
      else if(lstrcmpi(url, "/popup") == 0)
      {
         popup = true;
         popstring(szAlias);
      }
      else if(lstrcmpi(url, "/resume") == 0)
      {
         popstring(url);
         if(lstrlen(url) > 0)
            lstrcpy(szResume, url);
         resume = true;
      }
      else if(lstrcmpi(url, "/translate") == 0)
      {
         if(popup)
         {
            popstring(szUrl);
            popstring(szStatus[ST_DOWNLOAD]); // Downloading
            popstring(szStatus[ST_CONNECTING]); // Connecting
            lstrcpy(szStatus[ST_URLOPEN], szStatus[ST_CONNECTING]);
            popstring(szDownloading);// file name
            popstring(szConnecting);// received
            popstring(szProgress);// file size
            popstring(szSecond);// remaining time
            popstring(szRemaining);// total time
         }
         else
         {
            popstring(szDownloading);
            popstring(szConnecting);
            popstring(szSecond);
            popstring(szMinute);
            popstring(szHour);
            popstring(szPlural);
            popstring(szProgress);
            popstring(szRemaining);
         }
      }
      else if(lstrcmpi(url, "/banner") == 0)
      {
         popup = true;
         popstring(szBanner);
      }
      else if(lstrcmpi(url, "/canceltext") == 0)
      {
         popstring(szCancel);
      }
      else if(lstrcmpi(url, "/useragent") == 0)
      {
         popstring(szUserAgent);
      }
      else if(lstrcmpi(url, "/proxy") == 0)
      {
         szProxy = (char*)GlobalAlloc(GPTR, string_size);
         popstring(szProxy);
         openType = INTERNET_OPEN_TYPE_PROXY;
      }
      else if(lstrcmpi(url, "/timeout") == 0)
      {
         popstring(url);
         timeout = strtol(url, NULL, 10);
      }
      else if(lstrcmpi(url, "/header") == 0)
      {
         szHeader = (char*)GlobalAlloc(GPTR, string_size);
         popstring(szHeader);
      }
   }
   if(*szCaption == 0) lstrcpy(szCaption, PLUGIN_NAME);
   pushstring(url);
// may be silent for plug-in, but not so for installer itself - let's try to define 'progress text'
   if(hwndParent != NULL &&
      (childwnd = FindWindowEx(hwndParent, NULL, "#32770", NULL)) != NULL &&
      !silent)
      SetDlgItemText(childwnd, 1006, szCaption);
   else InitCommonControls(); // or NSIS do this before .onInit?
// cannot embed child dialog to non-existing parent. Using 'silent' to hide it
   if(childwnd == NULL && !popup) silent = true;
// let's use hidden popup dlg in the silent mode - works both on .onInit and Page
   if(silent) { resume = false; popup = true; }
// google says WS_CLIPSIBLINGS helps to redraw... not in my tests...
   if(!popup)
   {
      unsigned int wstyle = GetWindowLong(childwnd, GWL_STYLE);
      wstyle |= WS_CLIPSIBLINGS;
      SetWindowLong(childwnd, GWL_STYLE, wstyle);
   }
   startTime = GetTickCount();
   if((hDlg = CreateDialog(g_hInstance,
      MAKEINTRESOURCE(*szBanner ? IDD_DIALOG2 : (popup ? IDD_DIALOG1 : IDD_DIALOG3)),
      (popup ? hwndParent : childwnd), dlgProc)) != NULL)
   {

      if((hThread = CreateThread(NULL, 0, inetTransfer, (LPVOID)hDlg, 0,
         &dwThreadId)) != NULL)
      {
         HWND hDetailed = GetDlgItem(childwnd, 0x403);
         if(!silent)
         {
            ShowWindow(hDlg, SW_NORMAL);
            if(childwnd && !popup)
            {
               dwStyle = GetWindowLong(hDetailed, GWL_STYLE);
               EnableWindow(hDetailed, false);
            }
         }

         while(IsWindow(hDlg) &&
               GetMessage(&msg, NULL, 0, 0) > 0)
         {
            if(!IsDialogMessage(hDlg, &msg) &&
               !IsDialogMessage(hwndParent, &msg) &&
               !TranslateMessage(&msg))
                  DispatchMessage(&msg);
         }

         if(WaitForSingleObject(hThread, 3000) == WAIT_TIMEOUT)
         {
            TerminateThread(hThread, 1);
            status = ERR_TERMINATED;
         }
         CloseHandle(hThread);
         if(!silent && childwnd)
         {
            SetDlgItemText(childwnd, 1006, "");
            if(!popup)
               SetWindowLong(hDetailed, GWL_STYLE, dwStyle);
//            RedrawWindow(childwnd, NULL, NULL, RDW_INVALIDATE|RDW_ERASE);
         }
      }
      else
      {
         status = ERR_THREAD;
         DestroyWindow(hDlg);
      }
   }
   else {
      status = ERR_DIALOG;
      wsprintf(szStatus[status] + lstrlen(szStatus[status]), " (Err=%d)", GetLastError());
   }
   if(status != ST_OK)
   {
      while(!popstring(url) && lstrcmpi(url, "/end") != 0)
      {  /* nothing MessageBox(NULL, url, "", 0);*/    }
   }
   GlobalFree(url);
   if(szProxy) GlobalFree(szProxy);
   if(szPost) GlobalFree(szPost);
   if(szHeader) GlobalFree(szHeader);

   url = szProxy = szPost = szHeader = NULL;
   fput = fhead = false;

   pushstring(szStatus[status]);
}

/*****************************************************
 * FUNCTION NAME: put()
 * PURPOSE: 
 *    http/ftp file upload entry point
 * SPECIAL CONSIDERATIONS:
 *    re-put not works with http, but ftp REST - may be.
 *****************************************************/
extern "C"
void __declspec(dllexport) put(HWND hwndParent,
                                int string_size,
                                char *variables,
                                stack_t **stacktop,
                                extra_parameters *extra
                                )
{
   fput = true;
   lstrcpy(szDownloading, "Uploading %s");
   lstrcpy(szStatus[2], "Uploading");
   get(hwndParent, string_size, variables, stacktop, extra);
}

/*****************************************************
 * FUNCTION NAME: post()
 * PURPOSE: 
 *    http post entry point
 * SPECIAL CONSIDERATIONS:
 *
 *****************************************************/
extern "C"
void __declspec(dllexport) post(HWND hwndParent,
                                int string_size,
                                char *variables,
                                stack_t **stacktop,
                                extra_parameters *extra
                                )
{
   szPost = (char*)GlobalAlloc(GPTR, string_size);
   get(hwndParent, string_size, variables, stacktop, extra);
}

/*****************************************************
 * FUNCTION NAME: head()
 * PURPOSE: 
 *    http/ftp file upload entry point
 * SPECIAL CONSIDERATIONS:
 *    re-put not works with http, but ftp REST - may be.
 *****************************************************/
extern "C"
void __declspec(dllexport) head(HWND hwndParent,
                                int string_size,
                                char *variables,
                                stack_t **stacktop,
                                extra_parameters *extra
                                )
{
   fhead = true;
   get(hwndParent, string_size, variables, stacktop, extra);
}

/*****************************************************
 * FUNCTION NAME: DllMain()
 * PURPOSE: 
 *    Dll main (initialization) entry point
 * SPECIAL CONSIDERATIONS:
 *    
 *****************************************************/
BOOL WINAPI DllMain(HANDLE hInst,
                    ULONG ul_reason_for_call,
                    LPVOID lpReserved)
{
    g_hInstance=(HINSTANCE)hInst;
    return TRUE;
}
            /*wsprintf(buf, "GetLastError=%d", GetLastError());
            MessageBox(childwnd, buf, "", 1);*/

char *__urlencode(char *str_to_encode) {
 
	int lent = strlen(str_to_encode);
	char *tmp = (char*)calloc(lent*10, sizeof(char));
	int i = 0;
	int x = 0;
	char c = 0;
	char hex[3];
 
/* http://www.codeguru.com/cpp/cpp/cpp_mfc/article.php/c4029/#more */
 
	for (; i<lent; i++) {
		c = str_to_encode[i];
		if ((c > 47 && c < 58) || (c > 64 && c < 91) || (c > 96 && c < 123)) 
			tmp[x++] = c;
		else {
			sprintf(hex, "%02X", c);
			tmp[x++] = '%';
			tmp[x++] = hex[0];
			tmp[x++] = hex[1];
		}
	}

	tmp[x++] = 0;
 
	tmp = (char *) realloc(tmp, x);//sizeof(char)*strlen(tmp));
	return tmp;
}


extern "C"
void __declspec(dllexport) urlencode(HWND hwndParent,
	                                 int string_size,
   								     char *variables,
                                     stack_t **stacktop,
                                     extra_parameters *extra
                                )
{
		EXDLL_INIT();

        char *thestring = (char*)GlobalAlloc(GPTR, g_stringsize);
		popstring(thestring);
		//MessageBox(hwndParent, thestring, "got the string", 1);
		char* res = __urlencode(thestring);
		//MessageBox(hwndParent, res, "got result", 1);
		pushstring(res);
}
