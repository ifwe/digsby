#include <windows.h>
#include <wincred.h>
#include <stdlib.h>
#include <stdio.h>
#include <malloc.h>

#include "splash.h"

#define UPDATE_STR            L"Updating Digsby. Please wait..."
#define IMAGE_FILENAME        L"res\\digsbybig.bmp"
#define LOCKFILE              L"LOCKFILE"

#define POST_UPDATE_FILE      L"Digsby Updater.exe"
#define DIGSBY_CALL_WIN       L"\"%ws\" --updated"
#define DIGSBY_CALL_FAIL      L"\"%ws\" --update_failed"

#define WRITE_RIGHTS ((STANDARD_RIGHTS_ALL)|(FILE_GENERIC_WRITE))

//===============================================================================

#include <shellapi.h>
#include <Psapi.h>
#include <Aclapi.h>
#define SLEEP_MS 100

int KillPID(DWORD pid){

    HANDLE parent = OpenProcess(SYNCHRONIZE | PROCESS_TERMINATE, FALSE, (DWORD) pid);
    // May return NULL if the parent process has already gone away.
    // Otherwise, wait for the parent process to exit before starting the
    // update.
    if (parent) {

      BOOL termResult = TerminateProcess(parent, -1);

      CloseHandle(parent);
    }
    
    Sleep(SLEEP_MS);

    return 0;
}

void KillDigsbys(){


    // Get the list of process identifiers.
    DWORD aProcesses[5000], cBytes, cProcesses;
    unsigned int i;

    if ( !EnumProcesses( aProcesses, sizeof(aProcesses), &cBytes ) )
        return;

    // Calculate how many process identifiers were returned.
    cProcesses = cBytes / sizeof(DWORD);

    // Print the name and process identifier for each process.
    for ( i = 0; i < cProcesses; i++ ) {
        if( aProcesses[i] != 0 ) {
            DWORD processID = aProcesses[i];

            TCHAR szProcessName[MAX_PATH] = TEXT("<unknown>");

            // Get a handle to the process.
            HANDLE hProcess = OpenProcess( PROCESS_QUERY_INFORMATION |
                                           PROCESS_VM_READ,
                                           FALSE, processID );
            // Get the process name.
            if (hProcess) {
                HMODULE hMod;
                DWORD cBytesNeeded;

                if ( EnumProcessModules( hProcess, &hMod, sizeof(hMod), &cBytesNeeded) )
                    GetModuleBaseName( hProcess, hMod, szProcessName, 
                                       sizeof(szProcessName)/sizeof(TCHAR) );
            
            }
            
            // kill the process if it is "digsby.exe" or "Digsby.exe"
            if (0 == wcscmp(L"digsby.exe", _wcslwr(szProcessName)) || 0 == wcscmp(L"digsby-app.exe", _wcslwr(szProcessName)))
                KillPID(processID);
            

            CloseHandle( hProcess );
        }
    }
}

//===============================================================================

DWORD ErrPop(DWORD errCode, const wchar_t *msg = 0, ...){

    va_list args;
    va_start( args, msg );
    
    //if error code look up error message and log it
    LPWSTR errStr = NULL;
    if(errCode){
        //look up error message
        DWORD success = FormatMessageW(FORMAT_MESSAGE_ALLOCATE_BUFFER
                                       | FORMAT_MESSAGE_IGNORE_INSERTS
                                       | FORMAT_MESSAGE_FROM_SYSTEM,
                                       NULL,
                                       errCode,
                                       0,
                                       (LPWSTR) &errStr,
                                       0,
                                       NULL);
    }
    
    // Show Dialog
        
    wchar_t title[256];
    title[0] = 0;
    
    wsprintf(title, L"Error Code %d", errCode);
    
    wchar_t errmsg[2000];
    errmsg[0] = 0;
    if(msg){
        wvsprintf(errmsg,msg,args);
    }
    
    if(msg && errStr){
        wcscat(errmsg,L"\n\n");
    }
    
    
    if(errStr){
        wcscat(errmsg,errStr);
    }
    
    MessageBox(NULL,
               errmsg,
               title,
               MB_OK|MB_ICONERROR);
    
    
    //cleanup
    va_end(args);
    if(errStr)
        LocalFree(errStr);
    
    return errCode;
    
}

/**
 * Returns true if Vista or newer
 */
bool IsVista(){
    OSVERSIONINFO osver;

    osver.dwOSVersionInfoSize = sizeof( OSVERSIONINFO );

    return GetVersionEx(&osver) && osver.dwPlatformId == VER_PLATFORM_WIN32_NT && osver.dwMajorVersion >= 6;

}

bool HasUAC(){
    //HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\EnableLUA
    
    HKEY key;
    BYTE *uac;
    DWORD sizeofuac = sizeof(uac);
    
    DWORD errCode;
    
    errCode = RegOpenKeyEx(HKEY_LOCAL_MACHINE,
                           L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
                           0,
                           KEY_READ,
                           &key);
                           
    if(errCode != ERROR_SUCCESS){
        ErrPop(errCode,L"Error opening registry key for UAC check!");
    }
    
    RegQueryValueEx(key,
                    L"EnableLUA",
                    NULL,
                    NULL,
                    NULL,
                    &sizeofuac);
                              
    uac = (BYTE*)malloc(sizeof(BYTE)*sizeofuac);
                              
    errCode = RegQueryValueEx(key,
                              L"EnableLUA",
                              NULL,
                              NULL,
                              uac,
                              &sizeofuac);
                              
    if(errCode != ERROR_SUCCESS){
        ErrPop(errCode,L"Error Querying registry value for UAC check!");
    }
    
    RegCloseKey(key);
    
    return *uac? true : false;
}

int HasWriteAccess(HINSTANCE  hInstance, wchar_t *dir = 0){

//==Find Directory=============================================================
    if(!dir){
        int dirLen = GetCurrentDirectory(NULL,0) + 1;
        dir = (wchar_t*)alloca(sizeof(wchar_t) * dirLen);
        GetCurrentDirectory(dirLen,dir);
    }

//==Get a Security Description=================================================


    BOOL  success = true;
    BYTE  *secDesc;
    DWORD sizeNeeded = 0;

    success = GetFileSecurityW(dir,
                               DACL_SECURITY_INFORMATION,
                               NULL,
                               0,
                               &sizeNeeded);
    
    /*if(!success)
        return ErrPop(GetLastError());*/

    secDesc = (BYTE*)alloca(sizeof(BYTE) * sizeNeeded);

    success = GetFileSecurityW(dir,
                               DACL_SECURITY_INFORMATION,
                               secDesc,
                               sizeNeeded,
                               &sizeNeeded);
                               
    
    if(!success)
        return ErrPop(GetLastError(),L"Error getting permision info for directory: \n%s",dir);

//==Get DACL from Security Description=========================================

    PACL dacl;
    BOOL daclPresent, daclDefaulted;

    success = GetSecurityDescriptorDacl((SECURITY_DESCRIPTOR*)secDesc,
                                        &daclPresent,
                                        &dacl,
                                        &daclDefaulted);
    if(!success)
        return ErrPop(GetLastError(), L"Error getting DACL for directory: \n%s",dir);

    if (dacl == NULL) // a NULL dacl allows all access to an object
        return true;
    
//==Get Security Token=========================================================

    HANDLE *token = 0;

    success = OpenProcessToken(hInstance, TOKEN_READ, token);
    
    
    /*if(!success)
        return ErrPop(GetLastError());*/

//==Get and check ACEs from DACL===============================================

    DWORD allowed = 0;

    for(USHORT i = 0; i < dacl->AceCount; ++i){

        void *ace;
        BOOL isRelavent;

        success = GetAce(dacl, i, &ace);
        
        if(!success)
            continue;
        
        
        
        if(((ACE_HEADER*)ace)->AceType == ACCESS_ALLOWED_ACE_TYPE){
        
            ACCESS_ALLOWED_ACE *aAce = (ACCESS_ALLOWED_ACE*)ace;
            
            CheckTokenMembership(token,(PSID)&aAce->SidStart,&isRelavent);
            
            if(isRelavent){
                ACCESS_MASK mask = aAce->Mask;
                allowed |= mask;
                if ((allowed & WRITE_RIGHTS) == WRITE_RIGHTS)
                    return true;
            }


        }else if(((ACE_HEADER*)ace)->AceType == ACCESS_DENIED_ACE_TYPE){
        
            ACCESS_DENIED_ACE *dAce = (ACCESS_DENIED_ACE*)ace;
            
            
            CheckTokenMembership(token,(PSID)&dAce->SidStart,&isRelavent);
            
            if(isRelavent){
                ACCESS_MASK mask = dAce->Mask;
                if (mask & WRITE_RIGHTS)
                    return false;
            }

        }
        
    }

    return false;
}

int RunCmd(wchar_t *cmd, bool wait = true){

    STARTUPINFO si = { sizeof(STARTUPINFO) };
    PROCESS_INFORMATION pi;

    BOOL success = CreateProcessW( NULL, cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi);
    
    if(!success)
        return ErrPop(GetLastError(), L"Could not start update process.");

    DWORD result = 0;
    if(wait){
        WaitForSingleObject( pi.hProcess, INFINITE );
        GetExitCodeProcess(pi.hProcess, &result);
    }
    
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return result;
}

// Instead of linking against credui.lib, we get its functions via LoadLibrary
// and GetProcAddress so that this executable can run on Windows 2000.

typedef DWORD (WINAPI *pCredUIPromptForCredentials_t)(PCREDUI_INFO, PCTSTR, PCtxtHandle, DWORD, PCTSTR, ULONG, PCTSTR, ULONG, PBOOL, DWORD);
typedef DWORD (WINAPI *pCredUIParseUserName_t)(
  PCTSTR pszUserName,
  PTSTR pszUser,
  ULONG ulUserMaxChars,
  PTSTR pszDomain,
  ULONG ulDomainMaxChars
);

static pCredUIPromptForCredentials_t pCredUIPromptForCredentials = 0;
static pCredUIParseUserName_t pCredUIParseUserName = 0;

DWORD RunAsAdmin( HWND hWnd, LPTSTR file, LPTSTR parameters ){

    //http://msdn2.microsoft.com/en-us/library/bb756922.aspx

    SHELLEXECUTEINFO   sei;
    ZeroMemory(&sei, sizeof(sei));

    sei.cbSize          = sizeof(SHELLEXECUTEINFOW);
    sei.hwnd            = hWnd;
    sei.fMask           = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_FLAG_DDEWAIT | SEE_MASK_FLAG_NO_UI;
    sei.lpVerb          = L"runas";
    sei.lpFile          = file;
    sei.lpParameters    = parameters;
    sei.nShow           = SW_SHOWNORMAL;
    
        
    DWORD workingDirLen = GetCurrentDirectory(0,NULL);
    wchar_t *workingDir = (wchar_t*)alloca(sizeof(wchar_t) * workingDirLen);
    GetCurrentDirectory(workingDirLen,workingDir);

    
    sei.lpDirectory = workingDir;

    if (!ShellExecuteEx(&sei)){
        return ErrPop(GetLastError(), L"Could not start update process.");
    }
    
    
    DWORD result = 0;
    DWORD errCode = WaitForSingleObject( sei.hProcess, INFINITE );
    if(errCode){
        if(errCode == -1)
            errCode = GetLastError();
        
        return ErrPop(errCode,L"Error waiting for update process.");
    }
    GetExitCodeProcess(sei.hProcess, &result);
    
    CloseHandle(sei.hProcess);
    
    return result;
}


struct UserCredentials{
    wchar_t username[CREDUI_MAX_USERNAME_LENGTH + 1];
    wchar_t password[CREDUI_MAX_PASSWORD_LENGTH + 1];
};

DWORD UserPasswordPrompt(UserCredentials* creds){
    // thanks http://msdn2.microsoft.com/en-us/library/ms717794(VS.85).aspx


    BOOL fSave;
    DWORD dwErr;
    
    CREDUI_INFO cui;

    cui.cbSize = sizeof(cui);
    cui.hwndParent = NULL;
    cui.pszMessageText = L"Please enter administrator account information";
    cui.pszCaptionText = L"Digsby Autoupdate";
    cui.hbmBanner = NULL;

    fSave = FALSE;
    
    wcscpy(creds->username,L"");
    wcscpy(creds->password,L"");
    //SecureZeroMemory(creds->username, sizeof(creds->username));
    //SecureZeroMemory(creds->password, sizeof(creds->password));

    dwErr = pCredUIPromptForCredentials(&cui,                                // CREDUI_INFO structure
                                        L"DigsbyUpdater",                    // Target for credentials (usually a server)
                                        NULL,                                // Reserved
                                        0,                                   // Reason
                                        creds->username,                     // User name
                                        CREDUI_MAX_USERNAME_LENGTH+1,        // Max number of char for user name
                                        creds->password,                     // Password
                                        CREDUI_MAX_PASSWORD_LENGTH+1,        // Max number of char for password
                                        &fSave,                              // State of save check box
                                        CREDUI_FLAGS_GENERIC_CREDENTIALS |   // flags
                                        CREDUI_FLAGS_ALWAYS_SHOW_UI |
                                        CREDUI_FLAGS_DO_NOT_PERSIST |
                                        CREDUI_FLAGS_REQUEST_ADMINISTRATOR);

    return dwErr;
}


/**
 * Run a command as the user specified in creds.
 *
 * Returns nonzero if successful. Use GetLastError to determine an error state.
 */
int RunCmdAs(wchar_t *cmd, UserCredentials *creds, bool wait = true){
    // thanks http://msdn2.microsoft.com/en-us/library/ms682431(VS.85).aspx
    
    DWORD result;

    wchar_t user[CREDUI_MAX_USERNAME_LENGTH], domain[CREDUI_MAX_DOMAIN_TARGET_LENGTH];
    
    DWORD err = pCredUIParseUserName(creds->username,
                                    user,
                                    CREDUI_MAX_USERNAME_LENGTH,
                                    domain,
                                    CREDUI_MAX_DOMAIN_TARGET_LENGTH);
                                    
    if(err){
        wcscpy(user,creds->username);
        wcscpy(domain,L".");
    }
    
    
    
    PROCESS_INFORMATION pi;
    STARTUPINFO si = { sizeof(STARTUPINFO) };
    si.cb = sizeof(STARTUPINFO);

    
    DWORD workingDirLen = GetCurrentDirectory(0,NULL);
    wchar_t *workingDir = (wchar_t*)alloca(sizeof(wchar_t) * workingDirLen);
    GetCurrentDirectory(workingDirLen,workingDir);

    BOOL success = CreateProcessWithLogonW(user,
                                           domain,
                                           creds->password,                    
                                           0,                      // logon flags
                                           NULL,                  // application name
                                           cmd,                    // command line
                                           0,                    // creation flags
                                           0,                    // environment (0 means inherit)
                                           workingDir,            // working directory (0 means inherit)
                                           &si,
                                           &pi);
        
    // on success, we must clean up opened handles
    if (success) {
        if(wait){
            WaitForSingleObject( pi.hProcess, INFINITE );
            GetExitCodeProcess(pi.hProcess, &result);
        }else{
            result = 0;
        }
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }else{
        
        result = ErrPop(GetLastError(),L"Could not start update process as %ws.",creds->username);
        
    }

    return result;
}

bool GetSILock(HANDLE &lockHandle, wchar_t *lockfilepath){
    lockHandle = CreateFile(lockfilepath, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0);
    return lockHandle != INVALID_HANDLE_VALUE;
}

bool ReleaseSILock(HANDLE &lockHandle){
    return CloseHandle(lockHandle) == TRUE;
}

int APIENTRY wWinMain(HINSTANCE  hInstance,
                      HINSTANCE  hPrevInstance,
                      LPWSTR     lpwCmdLine,
                      int        nCmdShow){

//==Show the updating banner==================================================
    InitSplash(hInstance, (wchar_t*)&IMAGE_FILENAME, (wchar_t*)&UPDATE_STR);

//==Handling the command line args============================================
    LPWSTR *argv;
    int argc;

    //get traditional arguements from the string (filename is not part of the
    //command line)
    argv = CommandLineToArgvW(lpwCmdLine, &argc);

    if (!argv) {
        return ErrPop(GetLastError());
    }

    //Make sure there's enough arguments
    if ( argc != 3 ) { // supersecret USERDIR DIGSBYEXE
        return ErrPop(0,L"Incorect parameters");
    }

    KillDigsbys();

    const wchar_t *secretArg = argv[0];
    const wchar_t *userDir   = argv[1];
    const wchar_t *digsbyexe = argv[2];
    
    wchar_t *lockfilePath = (wchar_t*)alloca(sizeof(wchar_t) * (wcslen(userDir) + wcslen(LOCKFILE) + 2));
    wcscpy(lockfilePath, userDir);
    wcscat(lockfilePath, L"\\");
    wcscat(lockfilePath, LOCKFILE);
    
    HANDLE lockHandle;
    if(!GetSILock(lockHandle, lockfilePath)){
        ErrPop(0, L"Update lock already reserved, aborting! If you see this message and update fails, please contact bugs@digsby.com for assistance.");
        return -1;
    }


//==Determine Elevation Requirements===========================================
    bool needsElevation = !HasWriteAccess(hInstance);

    // try getting CredUIPromptForCredentials
    HMODULE credUI = LoadLibrary(L"credui.dll");
    if (credUI) {
        pCredUIPromptForCredentials = (pCredUIPromptForCredentials_t)GetProcAddress(credUI, "CredUIPromptForCredentialsW");
        pCredUIParseUserName = (pCredUIParseUserName_t)GetProcAddress(credUI, "CredUIParseUserNameW");
    }

//==Run Post Update============================================================
    size_t postUpdateLen = wcslen(userDir) + wcslen(POST_UPDATE_FILE) + 3;
    wchar_t *postUpdate = (wchar_t*)alloca(sizeof(wchar_t) * postUpdateLen);
    wcscpy(postUpdate, userDir);
    wcscat(postUpdate, L"\\");
    wcscat(postUpdate, POST_UPDATE_FILE);



    wchar_t cmd_buffer[1024];
    cmd_buffer[0] = 0;
    swprintf_s(cmd_buffer,  L"\"%ws\" \"%ws\" \"%ws\" \"%ws\"", postUpdate, secretArg, userDir, digsbyexe);
    
    int err = NO_ERROR;

    //TODO: Only really need pCredUIPromptForCredentials if UAC is not availible
    if(pCredUIPromptForCredentials && needsElevation){
    
        if(IsVista() && HasUAC()){
            
            swprintf_s(cmd_buffer,  L"\"%ws\" \"%ws\" \"%ws\"", secretArg, userDir, digsbyexe);
        
            err = RunAsAdmin(NULL,postUpdate,cmd_buffer);
        
        }else{
            UserCredentials creds;
            DWORD errCode = UserPasswordPrompt(&creds);
            if (errCode) {
                return ErrPop(errCode);
            }
            
            err = RunCmdAs(cmd_buffer, &creds);

            // ensure username and password are securely erased from memory
            SecureZeroMemory(&creds, sizeof(creds));
        }
    }else{
        err = RunCmd(cmd_buffer);
    }


//==Run Digsby=================================================================

    swprintf_s(cmd_buffer, err? DIGSBY_CALL_FAIL : DIGSBY_CALL_WIN, digsbyexe);
    RunCmd(cmd_buffer, false);

//==Close GUI and Exit=========================================================
    CloseSplash();
    
    ReleaseSILock(lockHandle);
    
    return 0;

}
