//
// debugapp.h
//

#ifndef __DEBUG_APP_H__
#define __DEBUG_APP_H__

#ifdef __WXMSW__

/**
 * Returns a std::vector<DWORD> of all thread IDs for a given process.
 *
 * If pid is 0 (the default) your current process ID is used.
 */
std::vector<unsigned long> get_thread_ids(unsigned long pid = 0);

#endif // __WXMSW__

#endif
