#define WIN32_LEAN_AND_MEAN


#include <windows.h>
#include <shellapi.h>
#include <Psapi.h>
#include <Aclapi.h>

#include <stdlib.h>
#include <stdio.h>
#include <malloc.h>

#include <fstream>
using std::wifstream;

#include "logging.h"

#define SLEEP_MS 100
#define BU_EXT L".updateback"


#define DEL_STR     L"cmd.exe /D /C del /F /Q /S *%ws"
#define XCOPY_STR   L"xcopy \"%ws\\*\" . /S /E /Q /Y"
#define RMDIR_STR   L"cmd.exe /D /C rmdir /s /q \"%ws\""

#define DELETE_FILE L"deleteme.txt"
#define UPDATE_FILE L"updateme.txt"

#define LOG_FILE    L"digsby_updater.log"
#define LOG_FILE_2  L"digsby_updater(2).log"

#define CLONE_FILE  L"digsby.clone"
#define DUMMY_FILE  L"lib\\digsby.dummy"

#define MOVE_ARGS   (MOVEFILE_REPLACE_EXISTING | MOVEFILE_COPY_ALLOWED | MOVEFILE_WRITE_THROUGH)


//#define UPDATE_STR     L"Please wait, updating Digsby!"
//#define IMAGE_FILENAME L"res\\digsbybig.bmp"

// thanks http://www.kickingdragon.com/2006/07/04/run-batch-files-without-a-console-popup/ and others



int KillPID(DWORD pid){
    LogMsg(L"KillPID(%d)\n", pid);
    LogMsg(L"  calling OpenProcess(SYNCHRONIZE, FALSE, %d)\n", pid);

    HANDLE parent = OpenProcess(SYNCHRONIZE | PROCESS_TERMINATE, FALSE, (DWORD) pid);
    // May return NULL if the parent process has already gone away.
    // Otherwise, wait for the parent process to exit before starting the
    // update.
    if (parent) {
      LogMsg(L"  OpenProcess returned HANDLE\n");

      //fwprintf(log, L"  Calling WaitForSingleObject(HANDLE, 5000)...\n");
      //DWORD result = WaitForSingleObject(parent, 1000);
      //fwprintf(log, L"  result: %d\n", result);
      //fwprintf(log, L"  Calling CloseHandle(parent)\n");

      LogMsg(L"  Calling TerminateProcess\n");

      //TODO: We should probably check this for failure
      //returns a bool, nonzero is success
      BOOL termResult = TerminateProcess(parent, -1);
      LogMsg(L"  TerminateProcess returned %d\n", termResult);

      CloseHandle(parent);
    } else {
        LogMsg(L"  OpenProcess did not find a process handle for PID %d\n", pid);
    }

    LogMsg(L"  sleeping for %d ms\n", SLEEP_MS);
    Sleep(SLEEP_MS);
    LogMsg(L"    done sleeping.\n");

    return 0;
}

void KillDigsbys(){

    /*MessageBox(NULL,
               L"KillDigsbys() bypassed for testing!",
               L"WARNING",
               MB_OK|MB_ICONINFORMATION);
    return;*/


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

int RunProcess(wchar_t* cmd, bool show = false, bool wait = true)
{
    LogMsg(L"\nRunProcess(cmd = \"%ws\", show = %d, wait = %d)\n", cmd, show, wait);

    STARTUPINFO si = { sizeof(STARTUPINFO) };

    if (!show) {
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_HIDE;
    }

    PROCESS_INFORMATION pi;

    int retVal = 0;

    LogMsg(L"  Calling CreateProcessA\n");
    if (!CreateProcessW( NULL, cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        LogErr(GetLastError(),0,L"  error: Could not run \"%ws\"\n", cmd);
        return 1;
    } else {
        LogMsg(L"  CreateProcessA ok\n");
    }

    if (wait) {
        LogMsg(L"  wait specified, calling WaitForSingleObject\n");
        DWORD result = WaitForSingleObject( pi.hProcess, INFINITE );
        LogMsg(L"  WaitForSingleObject returned with code %d\n", result);

        LogMsg(L"  CloseHandle( pi.hProcess )\n");
        CloseHandle( pi.hProcess );
        LogMsg(L"  CloseHandle( pi.hThread )\n");
        CloseHandle( pi.hThread );
    }

    return 0;
}

bool IsDirectory(wchar_t *path) {
    WIN32_FIND_DATA filedata;
    
    HANDLE h = FindFirstFile(path, &filedata);
    if (h == INVALID_HANDLE_VALUE)
        return false;

    FindClose(h);
    
    return filedata.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY;
}


DWORD ForgePath(const wchar_t *path, bool hasFileName = true){

    wchar_t *fullPath=0, *workingPath=0, *current=0;
    
    int endex = wcslen(path);    
    
    //strip the filename if it has one
    if (hasFileName)
        while (!(path[endex] == L'\\'))
            if (--endex < 0)
                return LogErr(0, 0, L"Invalid path: hasFileName was given, but path did not contain a slash.\n");
    
    //local copy of the path becsause wcstok() modifies it
    fullPath =    (wchar_t*)alloca((endex+1)*sizeof(wchar_t));
    
    //This is the path that is curently being created
    workingPath = (wchar_t*)alloca((endex+1)*sizeof(wchar_t));
    
    //copy the relevant path to the local copy
    wcsncpy(fullPath, path, endex);
    
    //manualy set null bytes because they aren't there yet
    fullPath[endex] = L'\0';
    workingPath[0] = L'\0';
    
    //while the path still has more depth, keep creating directories
    for(current = wcstok(fullPath, L"\\");
        current;
        current = wcstok(0, L"\\"), wcsncat(workingPath, L"\\", endex - wcslen(workingPath))){
            
            
        wcscat(workingPath, current);
        if(!IsDirectory(workingPath)){
            LogMsg(L"Creating dir: %ws;", workingPath);
            if(!CreateDirectoryW(workingPath, 0)){
                DWORD errCode = GetLastError();
                return LogErr(errCode, 0, L" Fail\n");
            }else{
                LogMsg(L" OK\n");
            }
        }
    }
    
    return 0;
}



DWORD StripDACL(const wchar_t *filename){

    PACL acl = (ACL*)alloca(sizeof(ACL));
    InitializeAcl(acl, sizeof(ACL), ACL_REVISION);
    
    DWORD errCode = SetNamedSecurityInfo((LPWSTR)filename,
                                         SE_FILE_OBJECT,
                                         UNPROTECTED_DACL_SECURITY_INFORMATION|DACL_SECURITY_INFORMATION,
                                         NULL,
                                         NULL,
                                         acl,
                                         NULL);
                                         
    if(errCode)
        LogErr(errCode,LE_POPUP,L"Could not update permissions.");
        
                                         
    return errCode;
}



//Move file from temp directory to the working directory
DWORD UpdateFile(const wchar_t* filename, const wchar_t* tmpDir){

    DWORD errCode = 0;
    
    //reserve space for new string
    size_t l = wcslen(filename) + wcslen(tmpDir) + 2;
    wchar_t *tmpPath = (wchar_t*) alloca(sizeof(wchar_t)*l);
    
    //merge strings into knew string
    wcscpy(tmpPath, tmpDir);
    wcscat(tmpPath, L"\\");
    wcscat(tmpPath, filename);
    
    //Try moving file, if fail Log error and return errCode
    for(bool tryagain = true; true; tryagain = false){
        LogMsg(L"Updating from temp dir: %ws;  ", filename);
        if(!MoveFileExW(tmpPath, filename, MOVE_ARGS)){
            errCode = GetLastError();
            if(errCode == ERROR_PATH_NOT_FOUND && tryagain){
                LogMsg(L"  FAIL\n\tDirectory not found, creating path\n");
                errCode = ForgePath(filename);
                if (errCode)
                    return LogErr(errCode, 0, L"Failed creating path.\n");

                continue;
            }
            return LogErr(errCode);
        }else{
            errCode = StripDACL(filename);
            if(errCode){
                return LogErr(errCode,0,L"Failed to reset DACL\n");
            }else{
                LogMsg(L"OK\n");
            }
        }
        
        break;
    }
        
    return 0;
}

//opens a text file and calls UpdateFile for every filename in it
DWORD UpdateFiles(const wchar_t* updateFileName, const wchar_t* tmpDir){

    LogMsg(L"\nreading %ws for files to be updated...\n", updateFileName);
    
    //open file (must be ASCII)
    wifstream fin(updateFileName);
    if (!fin.is_open())
        return LogErr(GetLastError(), 0, L"Error opening %ws\n", updateFileName);
    
    //for filename in file, update file
    wchar_t filename[MAX_PATH];
    while (fin.getline(filename, MAX_PATH)){
        DWORD errCode = UpdateFile(filename, tmpDir);
        if (errCode){
            fin.close();
            return errCode;
        }
    }
    
    fin.close();
    return 0;
}


//restores file from filename.extension.backup to filename.extension
DWORD RestoreFile(const wchar_t* filename) {

    //reserve space for backup filename
    size_t l = wcslen(filename) + wcslen(BU_EXT) + 1;
    wchar_t *backupName = (wchar_t*) alloca(sizeof(wchar_t)*l);
    
    //create backupfilename
    wcscpy(backupName, filename);
    wcscat(backupName, BU_EXT);

    LogMsg(L"restoring from backup: %ws;  ", filename);
    
    //move file to new name
    if (!MoveFileExW(backupName, filename, MOVE_ARGS)){
        DWORD errCode = LogErr(GetLastError());
        if(errCode == ERROR_FILE_NOT_FOUND)
            LogMsg(L"\tLikely not a real error. Most probably a new file.\n\n");
        else
            return errCode;
    } else
        LogMsg(L"OK\n");
    
    return 0;
}

//opens a text file and calls RestoreFile for every filename in it
DWORD RestoreFiles(const wchar_t* restoreFileName){

    LogMsg(L"\nreading %ws for files to be restored...\n", restoreFileName);
    
    //Open file
    wifstream fin(restoreFileName);
    if(!fin.is_open())
        return LogErr(0, 0, L"Error opening %ws\n", restoreFileName);
    
    //call RestoreFile for filename in the textfile
    wchar_t filename[MAX_PATH];
    while (fin.getline(filename, MAX_PATH)){
        DWORD errCode = RestoreFile(filename);
        if(errCode) {
            fin.close();
            return errCode;
        }
    }
    
    fin.close();
    return 0;
}

//Back move a file, changing it's extension to .backup
DWORD BackupFile(const wchar_t* filename){
    
    //Resrve space for backup name
    size_t l = wcslen(filename) + wcslen(BU_EXT) + 1;
    wchar_t *backupName = (wchar_t*) alloca(sizeof(wchar_t)*l);
    
    //create new filename
    wcscpy(backupName, filename);
    wcscat(backupName, BU_EXT);

    //Move file to new filename, if failed once try again, if faild twice return with error
    for (bool tryagain = true; true; tryagain = false) {
        LogMsg(L"backing up file %ws;  ", filename);
        if (!MoveFileExW(filename, backupName, MOVE_ARGS)){
            DWORD errCode = LogErr(GetLastError());
            if (errCode != ERROR_FILE_NOT_FOUND && errCode != ERROR_PATH_NOT_FOUND && errCode != ERROR_SUCCESS){
                if (tryagain) {
                    KillDigsbys();
                    LogMsg(L"Attempt 2 of ");
                    continue;
                }
                LogMsg(L"Failed all attempts, returning\n");

                return errCode;
            }
            LogMsg(L"\tLikely not a real error. Most probably a new file.\n\n");
        } else
            LogMsg(L"OK\n");
            
        break;
    }
    
    return 0;
}

//Call backup for all filenames listed in the txt file
DWORD BackupFiles(const wchar_t* backupFileName){

    LogMsg(L"\nreading %ws for files to be backed up...\n", backupFileName);
    
    //open file
    wifstream fin(backupFileName);
    if (!fin.is_open())
        return LogErr(GetLastError(), 0, L"Error opening %ws\n", backupFileName);
    
    //call BackupFile for filename in text file
    wchar_t filename[MAX_PATH];
    while (fin.getline(filename,MAX_PATH)){
        DWORD errCode = BackupFile(filename);
        if (errCode) {
            fin.close();
            return errCode;
        }
    }
    fin.close();  
    return 0;
}

//2 strings enter, one string leaves
//takes a 2 strings, and merges them into a new sring separated by '\', returns the new string
//requirs memory be freed later
wchar_t* MakePathStr(const wchar_t *dir,const wchar_t *file){
    
    //allocates space for string
    size_t dirLen = wcslen(dir);
    wchar_t *path = (wchar_t*) malloc(sizeof(wchar_t) * (dirLen + wcslen(file) + 2) );

    //merges the other strings into this string
    wcscpy(path, dir);
    wsprintf(&path[dirLen], L"\\%s", file);
    
    return path;
}

bool ReplaceFileXtreme(const wchar_t *oldFile, const wchar_t *newFile, const wchar_t *backupFile = 0, bool copy = false){
    if(backupFile){
        if(!MoveFileExW(oldFile, backupFile, MOVE_ARGS)){
            LogErr(0, 0, L"Error moving %ws to %ws", oldFile, backupFile);
            return false;
        }
    }
    
    if(!(copy? CopyFile(newFile, oldFile, FALSE) : MoveFileExW(newFile, oldFile, MOVE_ARGS))){
        LogErr(0, 0, L"Error moving %ws to %ws", newFile, oldFile);
        if(backupFile){
            if(!MoveFileExW(backupFile, oldFile, MOVEFILE_REPLACE_EXISTING | MOVEFILE_COPY_ALLOWED | MOVEFILE_WRITE_THROUGH)){
                LogErr(0, 0, L"Interesting error with ReplaceFileXtreme(), backup of %ws to %ws was successfull, but an error occured moving %ws to %ws and then another error restoring %ws to %ws",oldFile,backupFile,newFile,oldFile,backupFile,oldFile);
            }
        }
        return false;
    }
    
    return true;

}

//swaps the executible for a simple dummy one, perventing the user from starting another digsby instance
DWORD SwapExe(const wchar_t *digsbyexe) {
    
    //Try to replace exe with dummy, if fails twice error out
    for (bool tryagain = true; true; tryagain = false) {
        LogMsg(L"\nSwapping out digsby.exe for digsby.dummy;");
        
        //digsby.exe is renamed to digsby.clone
        //digsby.dummy is renamed to digsby.exe
        if(!ReplaceFileXtreme(digsbyexe, DUMMY_FILE, CLONE_FILE, true)){
            DWORD errCode = LogErr(GetLastError(), 0, L"\nCould not back up %ws", digsbyexe);
            if(tryagain){
                KillDigsbys();
                LogMsg(L"\n\tTrying again...\n");
                continue;
            }
            LogMsg(L"\n\tAborting!\n");
            return errCode;
        }
        LogMsg(L" OK!\n");
        return 0;
    }
}

//Swaps Back exe to be the normal one and the dummy back to .dummy
DWORD ReSwapExe(const wchar_t *digsbyexe){
    
    //try to swap exe back in for dummy, if fail twice error out
    for(bool tryagain = true; true; tryagain = false){
        LogMsg(L"\nEmergency restore of digsby.exe;");
        
        // digsby.clone is renamed to digsby.exe
        if(!ReplaceFileXtreme(digsbyexe, CLONE_FILE)){
            DWORD errCode = LogErr(GetLastError(), 0, L"\nCould not restore %ws", digsbyexe);
            if (tryagain) {
                KillDigsbys();
                LogMsg(L"\n\tTrying again...\n");
                continue;
            }
            LogMsg(L"\n\tAborting!\n");
            return errCode;
        }
        LogMsg(L" OK!\n");
        return 0;
    }
}

//if a new exe is provided, swaps that with the old one, then swaps the dummy out with the real exe
DWORD TryUpdateAndSwapExe(const wchar_t *tempDir, const wchar_t *digsbyexe){
    
    //allocate space for string
    size_t l = wcslen(tempDir) + wcslen(digsbyexe) + 2;
    wchar_t *newExe = (wchar_t*) alloca( sizeof(wchar_t) * l );
    
    //merge strings into the new one
    wcscpy(newExe, tempDir);
    wcscat(newExe, L"\\");
    wcscat(newExe, digsbyexe);
    
    DWORD errCode = 0;

    //Try updating digsby.exe
    LogMsg(L"\nAttemping to update %ws;", digsbyexe);
    if(!ReplaceFileXtreme(CLONE_FILE, newExe))
        errCode = LogErr(GetLastError(), 0, L"\nCan not copy %ws;", newExe);
        if (errCode == ERROR_FILE_NOT_FOUND) {
            errCode = 0;
            LogMsg(L"\tLikely not a real error. Most probably no update needed.\n\n");
        }
    else
        errCode = StripDACL(CLONE_FILE);
        if(errCode){
            return LogErr(errCode,0,L"Failed to reset DACL.");
        }else{
            LogMsg(L" OK\n");
        }
    
    //Restore Exe from clone
    for (bool tryagain = true; true; tryagain=false) {
        LogMsg(L"\nRestoring %ws;", digsbyexe);
        if (!ReplaceFileXtreme(digsbyexe, CLONE_FILE)) {
            errCode = LogErr(GetLastError(), 0, L"\nFailed to restore %ws;", digsbyexe);
            if (tryagain) {
                errCode = 0;
                LogMsg(L"Make sure Digsby process is dead:\n");
                KillDigsbys();
                LogMsg(L"Trying again...\n");
                continue;
            } else
                LogMsg(L"Aborting!\n");
        } else
            LogMsg(L" OK\n");
        break;
    }
    
    
    return errCode;
}

//==Restore block==============================================================
DWORD Restore(const wchar_t* digsbyexe, const wchar_t* updateBuffer, const wchar_t* deleteBuffer) {
    DWORD revErrCode = 0;
    
    // If updateBuffer is given, we need to revert ALL files.
    if (updateBuffer)
        revErrCode = RestoreFiles(updateBuffer);
    
    if (!revErrCode)
        revErrCode = RestoreFiles(deleteBuffer);

    if (!revErrCode)
        revErrCode = ReSwapExe(digsbyexe);
    
    if (revErrCode)
        LogErr(revErrCode, LE_POPUP, L"Error reverting to original files.\nA reinstall may be necessary.");
    else
        LogPop(L"Exiting Safely", L"Revert successful, you can restart Digsby.\nTo ensure a successful update, please update Digsby as a user with write permissions to the Digsby install directory and be sure no other logged in users currently have Digsby running.");
    
    return revErrCode;
}



int APIENTRY wWinMain(HINSTANCE  hInstance,
                      HINSTANCE  hPrevInstance,
                      LPWSTR     lpwCmdLine,
                      int        nCmdShow){
    
    DWORD errCode = 0, revErrCode = 0;
    
    bool verbose = false;
    
    
//==Handling the command line args============================================
    LPWSTR *argv;
    int argc;
    
    //get traditional arguements from the string (filename is not part of the
    //command line)
    argv = CommandLineToArgvW(lpwCmdLine, &argc);
    if (!argv) {
        OpenLog(LOG_FILE);
        LogMsg(L"digsby_updater %ws\n\n", lpwCmdLine);
        errCode = LogErr(GetLastError(), 0, L"CommandLineToArgvW failed\n");
        LogErr(errCode,LE_POPUP,L"Update failed, please check your digsby directory for %ws and email it to bugs@digsby.com", LOG_FILE);
        goto close_log_and_exit;
    }

    //Make sure there's enough arguments
    if ( argc != 3 ) { // supersecret USERDIR DIGSBYEXE
        OpenLog(LOG_FILE);
        LogMsg(L"digsby_updater %ws\n\n", lpwCmdLine);
        errCode = LogErr(0, 0, L"invalid number of arguments: you gave %d\n", argc - 1);
        LogErr(errCode,LE_POPUP,L"Update failed, please check your digsby directory for %ws and email it to bugs@digsby.com", LOG_FILE);
        goto close_log_and_exit;
    }

    //make sure the super seceret arguement is correct
    if (wcscmp(argv[0], L"supersecret") && wcscmp(argv[0], L"supersecretverbose")) {
        OpenLog(LOG_FILE);
        LogMsg(L"digsby_updater %ws\n\n", lpwCmdLine);
        errCode = LogErr(0, 0, L"invalid secret argument\n");
        LogErr(errCode,LE_POPUP,L"Update failed, please check your digsby directory for %ws and email it to bugs@digsby.com", LOG_FILE);
        goto close_log_and_exit;
    }
    
//==Set up directories from the args===========================================

    const wchar_t *userDir = argv[1];
    const wchar_t *digsbyexe = argv[2];
    
    size_t tempDirLen = wcslen(userDir) + wcslen(L"\\temp") + 1;
    wchar_t *tempDir = (wchar_t*)alloca(sizeof(wchar_t) * tempDirLen);
    wcscpy(tempDir,userDir);
    wcscat(tempDir,L"\\temp");
    
    size_t logDirLen = wcslen(userDir) + wcslen(L"\\Logs")+ 1;
    wchar_t *logDir = (wchar_t*)alloca(sizeof(wchar_t) * logDirLen);
    wcscpy(logDir,userDir);
    wcscat(logDir,L"\\Logs");
    
//==Open log file in user dir==================================================

    if(!OpenLog(logDir, LOG_FILE)){
        errCode = ForgePath(logDir, false);
        if(errCode){
            if(OpenLog(LOG_FILE)){
                LogMsg(L"logdir: %ws\n\n", logDir);
                LogErr(errCode, 0, L"Unable to create primary log directory. Secondary log created. Continuing anyway.\n");
            }else{
                LogErr(0, LE_POPUP, L"Unable to create log files. Continuing anyway.\n");
            }
            errCode = 0;
        }
        else if(!OpenLog(logDir, LOG_FILE)){
            if(!OpenLog(logDir, LOG_FILE_2)){
                if(OpenLog(LOG_FILE)){
                    LogMsg(L"logdir: %ws\n\n", logDir);
                    LogErr(0, 0, L"Unable to create primary log file. Secondary log created. Continuing anyway.\n");
                }else{
                    LogErr(0, LE_POPUP, L"Unable to create log files. Continuing anyway.\n");
                }
            }
        }
    }
    
    
    DWORD workingDirLen = GetCurrentDirectory(0,NULL);
    wchar_t *workingDir = (wchar_t*)alloca(sizeof(wchar_t)*workingDirLen);
    GetCurrentDirectory(workingDirLen,workingDir);
    
    LogMsg(L"digsby_updater %ws\n", lpwCmdLine);
    LogMsg(L"Working Directory: %ws\n\n",workingDir);


//==Create a console if verbose mode===========================================
    
    //Set verbose
    verbose = !wcscmp(argv[0], L"supersecretverbose");
    SetVerbose(verbose);

    if (verbose) {
        // show a console in verbose mode
        AllocConsole();
        freopen("CONIN$",  "rb", stdin);
        freopen("CONOUT$", "wb", stdout);
        freopen("CONOUT$", "wb", stderr);
        LogMsg(L"verbose... yes\n");
    } else {
        LogMsg(L"verbose... no\n");
    }
    
//==Kill all running digsby instances==========================================

    KillDigsbys();
    
//==Swap our the digsby exetcutabel for a dummy one============================
    
    errCode = SwapExe(digsbyexe);
    if (errCode) {
        LogMsg(L"\n\n");
        LogErr(errCode, LE_POPUP, L"Critical error in backing up %ws. Exiting.", digsbyexe);
        goto close_log_and_exit;//close_splash_and_exit
    }

//==Backup all files that will be deleted or replaced==========================    
    wchar_t *deleteBuffer = MakePathStr(tempDir, DELETE_FILE);
    wchar_t *updateBuffer = MakePathStr(tempDir, UPDATE_FILE);
    
    errCode = BackupFiles(deleteBuffer);
    if (errCode) {
        LogMsg(L"\n\n");
        LogErr(errCode, LE_POPUP, L"Critical error in backing up files. Click OK to revert.");
        
        Restore(digsbyexe, 0, deleteBuffer);// Restore partial
        goto cleanup;
    }
    
    errCode = BackupFiles(updateBuffer);
    if (errCode) {
        LogMsg(L"\n\n");
        LogErr(errCode, LE_POPUP, L"Critical error in backing up files. Click OK to revert.");

        Restore(digsbyexe, updateBuffer, deleteBuffer);
        goto cleanup;
    }

//==Update files and executable, swap excutable back in for dummy==============

    errCode = UpdateFiles(updateBuffer, tempDir);
    if (errCode) {
        LogMsg(L"\n\n");
        LogErr(errCode, LE_POPUP, L"Critical error in writing new files. Click OK to revert.");
        Restore(digsbyexe, updateBuffer, deleteBuffer);
        goto cleanup;
    }
    
    errCode = TryUpdateAndSwapExe(tempDir, digsbyexe);
    if (errCode) {
        LogMsg(L"\n\n");
        LogErr(errCode, LE_POPUP, L"Critical error in restoring %ws.\nTry renaming %ws to %ws. A reinstall might be needed.", digsbyexe, CLONE_FILE, digsbyexe);
        goto cleanup;
    }
   
//==Cleanup temp directory and backuped files, then start program==============

    wchar_t cmd_buffer[1024];
    //removing temp diretory
    swprintf_s(cmd_buffer, RMDIR_STR, tempDir);
    RunProcess(cmd_buffer);
    
    //deleting backup files
    swprintf_s(cmd_buffer, DEL_STR, BU_EXT);
    RunProcess(cmd_buffer);

//==Cleanup====================================================================
 
    LogMsg(L"\nFinished all tasks, exiting cleanly\n");

cleanup:                //Start cleanup here if the Buffer strings have been created
    LogMsg(L"\nCleanup and Exit\n");

    free(deleteBuffer);
    free(updateBuffer);
    
close_log_and_exit:     //Start cleanup here if log is the only thing
    CloseLog();
    
    if (verbose)
        system("pause");
        
    return errCode;
}

