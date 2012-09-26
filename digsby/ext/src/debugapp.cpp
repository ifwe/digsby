//
// debugapp.cpp
//

#ifdef __WXMSW__

#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>

#include <vector>

/**
 * Returns a std::vector<DWORD> of all thread IDs for a given process.
 *
 * If pid is 0 (the default) your current process ID is used.
 */
std::vector<unsigned long> get_thread_ids(unsigned long pid = 0)
{
	std::vector<DWORD> threadIds;
    THREADENTRY32 threadEntry;
    threadEntry.dwSize = sizeof(THREADENTRY32);

    // if not specified, default to THIS process
	if (!pid) pid = GetCurrentProcessId();

	// toolhelp: m$ft's most poorly named library?
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if(snapshot == INVALID_HANDLE_VALUE)
        return threadIds;

    if(!Thread32First(snapshot, &threadEntry)) {
        fprintf(stderr, "Thread32First: err code %d", GetLastError());
        CloseHandle(snapshot);
        return threadIds;
    }

    // find all threads matching pid
    do {
        if (threadEntry.th32OwnerProcessID == pid)
        	threadIds.push_back(threadEntry.th32ThreadID);
    } while(Thread32Next(snapshot, &threadEntry));

    CloseHandle(snapshot);
    return threadIds;
}

#endif