#include "logging.h"

FILE *log = 0; //file used for log
bool verbose = true; //print to console

//turn on verbose mode
void SetVerbose(bool on){
    verbose = on;
}

//print to log and console if verbose
void vLogMsg(const wchar_t *msg, va_list args){
    if(!log){
        //OpenLog("log.log");
        if(verbose)
            printf("Error: no log file not open");
        return;
    }
    
    //ZOMG!! variable arg list-file-wide character-print-formated to log
    vfwprintf(log, msg, args);
    
    if(verbose){
        //Convert string form wide to ascii?
        char *msgASCII = (char*)malloc(sizeof(char)*(wcslen(msg)+1));
        sprintf(msgASCII, "%ws", msg);
        
        //Print to console
        vprintf(msgASCII, args );
        
        //free memory
        free(msgASCII);
    }
}

//Log a simple message
void LogMsg(const wchar_t *msg, ...){
    
    va_list args;
    va_start(args, msg);
    
    vLogMsg(msg, args);
    
    va_end(args);
}

//Log a message and display an info dialog
void LogPop(const wchar_t *title, const wchar_t *msg, ...){

    //args for a variable argument method
    va_list args;
    va_start( args, msg );
    
    //Log it
    vLogMsg(msg,args);
    
    //format message for dialog
    wchar_t popmsg[2000];
    if(msg){
        wvsprintf(popmsg,msg,args);
        //wcscat(popmsg,L"\n\n"); //TODO: Remove this line???
    }
    
    //Display Dialog
    MessageBox(NULL,
               popmsg,
               title,
               MB_OK|MB_ICONINFORMATION);
    
    //end the args list
    va_end(args);
}

//log an error, optional msg and error code, flag can be used to display error dialog
DWORD LogErr(DWORD errCode, DWORD flags, const wchar_t *msg, ...){
    
    //Get varialble args list
    va_list args;
    va_start( args, msg );
    
    //if mesage, log it
    if(msg){
        vLogMsg(msg,args);
    }
    
    //if error code look up error message and log it
    LPWSTR errStr = NULL;
    if(errCode){
        LogMsg(L"\n\tError %d: ", errCode);
        
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
                                       
        //if error message log it, else log "Unknown Error"
        if (success){
            fwprintf(log, L"%ws", errStr);
            if(verbose) printf("%ws", errStr);
        }
        else{
            fwprintf(log, L"Unknown Error\n\n");
            if(verbose) printf("Unknown Error\n\n");
        }
    }
    
    // Show Dialog if popup flag
    if(flags & LE_POPUP){
        
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
        
    }

    
    //cleanup
    va_end(args);
    if(errStr)
        LocalFree(errStr);
    
    return errCode;
    
}

//open log file
bool OpenLog(const wchar_t *logDir, const wchar_t *logFile){
    //if there already is an open log file, close it
    if(log && log != stderr)
        fclose(log);
    
    size_t logPathLen = wcslen(logDir) + wcslen(logFile) + 2;
    wchar_t *logPath = (wchar_t*)alloca(sizeof(wchar_t) * logPathLen);
    wcscpy(logPath,logDir);
    wcscat(logPath,L"\\");
    wcscat(logPath,logFile);
        
    //open file
    log = _wfopen(logPath, L"w,ccs=UTF-16LE");
    if (!log){
        log = stderr;
        return false;
    }
    
    return true;
}

bool OpenLog(const wchar_t *logFile){
    //if there already is an open log file, close it
    if(log && log != stderr)
        fclose(log);
    
    //open file
    log = _wfopen(logFile, L"w,ccs=UTF-16LE");
    if (!log){
        log = stderr;
        return false;
    }
    
    return true;
}

//close log file
void CloseLog(){
    if(log && log != stderr)
        fclose(log);
}
