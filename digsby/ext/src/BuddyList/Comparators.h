#ifndef Comparators_h
#define Comparators_h

#include "StringUtils.h"
#include <vector>

/*
#include <iostream>
#include <fstream>
using std::wofstream;
using std::endl;
using std::wclog;
*/

#include "SortBy.h"
#include "BuddyListCommon.h"
#include "Contact.h"

/**
 * Returns -1 if a < b, 0 if a == b, and 1 if a > b.
 *
 * Like Python's __cmp__.
 */
template <typename T>
static int cmp(T a, T b)
{
    if (a < b) return -1;
    else if (b < a) return 1;
    else return 0;
}

template <typename T> int by_name(const T& a, const T& b)
{
    return CaseInsensitiveCmp(a->name(), b->name());
}

#ifdef _CONTACT
#error "_CONTACT is already defined"
#endif 

#define _CONTACT(a, x) \
    if (!a->isLeaf()) return 0; \
    Contact* x = reinterpret_cast<Contact*>(a->data());

template <typename T> int by_alias(const T& a, const T& b) {
    _CONTACT(a, x);
    _CONTACT(b, y);
    return CaseInsensitiveCmp(x->alias(), y->alias());
}

template <typename T> int by_service(const T& a, const T& b) {
    _CONTACT(a, x);
    _CONTACT(b, y);
    return x->service().compare(y->service());
}

template <typename T> int by_status(const T& a, const T& b) {
    _CONTACT(a, x);
    _CONTACT(b, y);
    return x->status().compare(y->status());
}

template <typename T> int by_logsize(const T& a, const T& b) {
    _CONTACT(a, x);
    _CONTACT(b, y);
    return -cmp(x->logSize(), y->logSize());
}

template <typename T> int by_userorder(const T& a, const T& b) {
    return cmp(a->userOrder(), b->userOrder());
}

template <typename T> int by_customorder(const T& a, const T& b) {
    return cmp(a->customOrder(), b->customOrder());
}

template <typename T> int by_mobile(const T& a, const T& b) {
    _CONTACT(a, x);
    _CONTACT(b, y);
    return cmp(x->mobile(), y->mobile());
}

template <typename T> int by_online(const T& a, const T& b) {
    _CONTACT(a, x);
    _CONTACT(b, y);
    return -cmp(x->online(), y->online());
}

#undef _CONTACT

template <typename T> class MultiComparator
{
private:
    MultiComparator();
    MultiComparator& operator=(const MultiComparator& x);
public:
	typedef int (*cmp_func)(const T& a, const T& b);    

    class Comparator
    {
    public:
        Comparator(SortBy sortBy, cmp_func func)
            : m_sortsBy(sortBy)
            , m_func(func)
        {
            BL_ASSERT(!cmpName(sortBy).empty());
            //printf("Comparator %ws %d\n", cmpName(sortBy).c_str(), sortBy);
        }

        int operator()(const T &a, const T &b) const
        {
            return m_func(a, b);
        }

        SortBy sortsBy() const { return m_sortsBy; }

        bool ok() const { return !cmpName(m_sortsBy).empty(); }

    protected:
        SortBy m_sortsBy;
        cmp_func m_func;
    };

    typedef std::vector<Comparator*> CompareFuncVector;

protected:
    /**
     * Returns a cmp_func (a less-than-predicate function) for a SortBy enum.
     */
    static cmp_func cmpFuncForSortBy(SortBy sortBy)
    {
        switch (sortBy) {
            case Alias:        return &by_alias;
            case Name:         return &by_name;
            case Service:      return &by_service;
            case Status:       return &by_status;
            case LogSize:      return &by_logsize;
            case UserOrdering: return &by_userorder;
            case CustomOrder:  return &by_customorder;
            case Mobile:       return &by_mobile;
            case Online:       return &by_online;
            default:
                BL_ASSERT_NOT_REACHABLE(0);
        }
    }

    static wstring cmpName(SortBy sortBy)
    {
        switch (sortBy) {
            case Alias:        return L"Alias";
            case Name:         return L"Name";
            case Service:      return L"Service";
            case Status:       return L"Status";
            case LogSize:      return L"LogSize";
            case UserOrdering: return L"UserOrdering";
            case CustomOrder:  return L"CustomOrder";
            case Mobile:       return L"Mobile";
            case Online:       return L"Online";
            default:
                BL_ASSERT_NOT_REACHABLE(L"");
        }
    }

public:
    /**
     * Returns true if this MultiComparator's comparisons are affected
     * by the attributes specified in flags.
     */
    int sortsBy(int flags) const { return (m_sortsBy & flags) != 0; }
    int sortsByFlags() const { return m_sortsBy; }

    /**
     * Returns a non-const reference to the vector of comparison functions
     * being used by this MultiComparator.
     */
    /* CompareFuncVector& compareFuncs() { return m_compareFuncs; }*/

    bool operator()(const T &a, const T &b) const
    {
        // wclog << L"comparing " << a->repr() << L" and " << b->repr() << L":" << endl;
        for (typename CompareFuncVector::const_iterator i = m_compareFuncs.begin();
             i != m_compareFuncs.end(); ++i)
        {
            // The functions in m_compareFuncs return -1, 0, or 1, but this function
            // needs to act like a less-than predicate. If compare function returns
            // -1 we return true; if it returns 0 we try the next one, and if it returns
            // 1 we stop and return false.
            int val = (*(*i))(a, b);

            SortBy s = (*i)->sortsBy();
            wstring name = cmpName(s);
            // wclog << "  " << name << ": " << val << endl;

            if (val < 0) {
                // wclog << L"  returning TRUE" << endl;
                return true;
            } else if (val > 0) {
                // wclog << L"  returning FALSE" << endl;
                return false;
            }
        }

        // wclog << L"  returning false" << endl;
        return false;
	}

    
    explicit MultiComparator(SortBy sorter)
    {
        m_compareFuncs.push_back(new Comparator(sorter, cmpFuncForSortBy(sorter)));
        _updateSortsBy();
    }

    /**
     * Constructor taking a vector of SortBy enums.
     */
    explicit MultiComparator(const std::vector<SortBy>& funcs)
    {
        for (std::vector<SortBy>::const_iterator i = funcs.begin();
             i != funcs.end(); ++i)
            m_compareFuncs.push_back(new Comparator(*i, cmpFuncForSortBy(*i)));

        _updateSortsBy();
    }

    ~MultiComparator()
    {
        for (typename CompareFuncVector::const_iterator i = m_compareFuncs.begin(); i != m_compareFuncs.end(); ++i)
            delete *i;
    }

    bool ok() const
    {
        for (typename CompareFuncVector::const_iterator i = m_compareFuncs.begin(); i != m_compareFuncs.end(); ++i)
            if (!(*i)->ok())
                return false;
        return true;
    }

    /**
     * Clears all comparison functions from this MultiComparator.
     */
    void clearFuncs()
    {
        for (typename CompareFuncVector::const_iterator i = m_compareFuncs.begin(); i != m_compareFuncs.end(); ++i)
            delete *i;
        m_compareFuncs.clear();
        _updateSortsBy();
    }

    // This copy constructor is strictly for the unit tests, which use
    // std::sort to verify the less-than property of MultiComparator.
    // std::sort copies its comparator--so we need this function.
    MultiComparator(const MultiComparator& m)
    {
        for (typename CompareFuncVector::const_iterator i = m.m_compareFuncs.begin(); i != m.m_compareFuncs.end(); ++i) {
            Comparator* c = *i;
            m_compareFuncs.push_back(new Comparator(*c));
        }

        m_sortsBy = m.m_sortsBy;
    }

protected:
    void _updateSortsBy()
    {
        // m_sortsBy is a bitfield with bits on for each attribute that "matters"
        // to any of our comparison functions
        m_sortsBy = 0;
        for (typename CompareFuncVector::const_iterator i = m_compareFuncs.begin(); i != m_compareFuncs.end(); ++i)
            m_sortsBy |= (*i)->sortsBy();
    }

    CompareFuncVector m_compareFuncs;
    int m_sortsBy;
};

#endif // Comparators_h
