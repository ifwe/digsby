#include "precompiled.h"
#include "config.h"
#include "Status.h"

#include <string>
using std::wstring;


int numberForStatus(const wstring& status)
{
    if (status == L"available")
        return 100;
    else if (status == L"away")
        return 50;
	else if (status == L"idle")
        return 40;
	else if (status == L"mobile")
        return 30;
    else if (status == L"offline")
        return 10;
    else if (status == L"unknown")
        return 0;
    else
        return 50;
}

wstring groupNameForStatus(const wstring& status)
{
    // TODO: if this function gets long enough, should we generate a perfect
    // hash?
    if (status == L"available")
        return L"Available";
    else if (status == L"away")
        return L"Away";
    else if (status == L"idle")
        return L"Idle";
    else if (status == L"mobile")
        return L"Mobile";
    else if (status == L"offline")
        return L"Offline";
    else if (status == L"unknown")
        return L"Offline";
    else
        // TODO: have IM services be able to register status strings here
        return L"Away";
}

static inline int cmp(int a, int b)
{
    if (a < b) return -1;
    else if (a > b) return 1;
    else return 0;
}

int compareStatuses(const wstring& a, const wstring& b)
{
    if (a == b)
        return 0;
    else
        return cmp(numberForStatus(a), numberForStatus(b));
}
