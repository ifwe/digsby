#ifndef StringUtils_h
#define StringUtils_h

#include <string>
#include <algorithm>
#include <cctype>

std::wstring BL_EXPORT wstringToLower(const std::wstring& s);

/**
 * A case insensitive less-than operator for strings or wstrings.
 */
struct CaseInsensitiveLess
{
    template <typename T>
    bool operator()(const T& a, const T& b)
    {
        return std::tolower(a) < std::tolower(b);
    }
};

/**
 * Returns -1 if a < b, 1 if a > b, and 0 if a == b.
 *
 * Case insensitive.
 */

// TODO: lstrcmpi on windows is probably faster

template <typename T>
int CaseInsensitiveCmp(const T& a, const T& b)
{
    if (std::lexicographical_compare(a.begin(), a.end(), b.begin(), b.end(), CaseInsensitiveLess()))
        return -1;
    if (std::lexicographical_compare(b.begin(), b.end(), a.begin(), a.end(), CaseInsensitiveLess()))
        return 1;

    return 0;
}

template <typename T>
bool CaseInsensitiveEqual(const T& a, const T& b)
{
    return 0 == CaseInsensitiveCmp(a, b);
}


struct BL_EXPORT MostCapitalizedLess
{
    std::wstring m_lower;

    MostCapitalizedLess(const std::wstring& lower)
        : m_lower(lower)
    {}

    /**
     * Compares two strings (which must be equal to each other case insensitively).
     *
     * Returns true if a has less captial letters than b.
     */
    bool operator()(const std::wstring& a, const std::wstring& b);

    bool less(const std::wstring& a, const std::wstring& b)
    {
        return (*this)(a, b);
    }
};

std::wstring BL_EXPORT mostCapitalized(const std::wstring& lower, const std::vector<std::wstring>& strings);

#endif

