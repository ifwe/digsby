#ifndef Status_h
#define Status_h

#include <string>
using std::wstring;

/**
 * Return an integer for a status string.
 */
int numberForStatus(const wstring& status);

/**
 * Returns a group name for a status string.
 */
wstring groupNameForStatus(const wstring& status);

/**
 * cmp for two status strings.
 */
int compareStatuses(const wstring& a, const wstring& b);

#endif

