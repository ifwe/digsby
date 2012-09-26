#include <windows.h>

#define DIGSBYAPP_EXE L"lib\\digsby-app.exe"

LPWSTR get_cwd(){
	DWORD workingDirLen = GetCurrentDirectory(0,NULL);
	WCHAR *workingDir = (WCHAR*)malloc(sizeof(WCHAR)*(workingDirLen+1));
	GetCurrentDirectory(workingDirLen,workingDir);
	return workingDir;
}

LPWSTR get_exe_name(){
	DWORD exeNameLen = 1024;
	WCHAR* filename = (WCHAR*)malloc(sizeof(WCHAR)*exeNameLen); 
	GetModuleFileName(NULL, filename, exeNameLen);
	
	return filename;
}

LPWSTR get_parent_dir(LPWSTR filename) {
	int sz = 1024;
	LPTSTR path = (WCHAR*)malloc(sizeof(WCHAR)*sz); 
	LPTSTR file = 0; //(WCHAR*)malloc(sizeof(WCHAR)*sz);
	GetFullPathName(filename, sz, path, &file);

	int parentDirLen = wcslen(path)-wcslen(file);
	size_t parentDirSz = sizeof(WCHAR)*(parentDirLen+1);
	LPTSTR parentDir = (WCHAR*)malloc(parentDirSz);
	wcsncpy(parentDir, filename, parentDirLen);
	parentDir[parentDirLen] = 0;
	free(path); path = 0; file = 0;
	return parentDir;
}

int APIENTRY wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPWSTR lpwCmdLine, int nCmdShow){
	LPWSTR cmdBuffer, exename, parentdir;
	exename = get_exe_name();
	parentdir = get_parent_dir(exename);
	
	size_t cmdBufferLen = wcslen(parentdir) + wcslen(DIGSBYAPP_EXE) + 4 + wcslen(lpwCmdLine);
	cmdBuffer = (WCHAR*)malloc(sizeof(WCHAR)*cmdBufferLen);
	
	wsprintf(cmdBuffer, L"\"%ws%ws\" %ws", parentdir, DIGSBYAPP_EXE, lpwCmdLine);

	PROCESS_INFORMATION pi;
	STARTUPINFO si = { sizeof(STARTUPINFO) };
	CreateProcessW( NULL, cmdBuffer, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi);
	free(exename); exename = 0;
	free(parentdir); parentdir = 0;
	return 0;
}
