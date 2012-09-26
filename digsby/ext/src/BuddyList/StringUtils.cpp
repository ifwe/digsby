#include "precompiled.h"
#include "config.h"
#include "StringUtils.h"

#include <algorithm>

std::wstring wstringToLower(const std::wstring& s)
{
#ifdef WIN32
    // on Windows use LCMapString to handle internationalized-aware lowercasing
    if (s.empty())
        return s;
        
    const wchar_t* inBuf = s.c_str();

    // Find the size of the buffer we need.
    size_t bufSize = LCMapString(LOCALE_USER_DEFAULT, LCMAP_LOWERCASE, inBuf, s.size(), 0, 0);
    BL_ASSERT(bufSize);

    // Allocate buffer on the stack.
    wchar_t* buf = reinterpret_cast<wchar_t*>(_alloca(bufSize * sizeof(wchar_t)));

    // Get lowercased string.
    size_t written = LCMapString(LOCALE_USER_DEFAULT, LCMAP_LOWERCASE, inBuf, s.size(), buf, bufSize);
    BL_ASSERT(written);

    return std::wstring(buf, bufSize);
#else
    // Not international-aware
    std::wstring r(s);
    // Not sure if the code below is the best solution, for more see:
    // http://bytes.com/topic/c/answers/60652-tolower-used-transform
    std::transform(r.begin(), r.end(), r.begin(), (int(*)(int))std::tolower);
    return r;
#endif

}

std::wstring mostCapitalized(const std::wstring& lower, const std::vector<std::wstring>& strings)
{
    std::vector<std::wstring> v(strings);
    std::sort(v.begin(), v.end(), MostCapitalizedLess(lower));
    return v.back();
}


bool MostCapitalizedLess::operator()(const std::wstring& a, const std::wstring& b)
{
    if (a.size() != b.size())
        return false;

    int x = 0;

    for (size_t i = 0; i < a.size(); ++i) {
        if (b[i] < a[i]) {
            x -= 1;
        } else if (a[i] < b[i]) {
            x += 1;
        }
    }

    return x < 0;
}
