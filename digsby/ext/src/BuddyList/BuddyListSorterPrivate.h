#ifndef BuddyListSorterPrivate_h
#define BuddyListSorterPrivate_h

#include "StringUtils.h"

#include <vector>
#include <string>

#include <boost/function.hpp>

//
// an "adapter" for a vector that provdes a special push_back
// function that notices adjacent elements with equal keys.
//
// a callback is given (begin(), end()) iterator pairs for each range
// of similar elements.
//
template <typename T>
class GroupByKey
{
private:
    GroupByKey();
    GroupByKey(const GroupByKey&);

public:
    typedef typename std::vector<T>::const_iterator Iter;
    typedef boost::function<void(const Iter&, const Iter&)> Callback;

    GroupByKey(std::vector<T>* vec, unsigned int reserve, Callback callback)
        : m_vec(vec)
        , m_firstValid(false)
        , m_callback(callback)
    {
        vec->reserve(reserve);
    }

    void push_back(T data)
    {
        std::wstring key = data->key();

        // Use a case insensitive comparison here to make groups with similar names
        // merge. 
        if (CaseInsensitiveCmp(key, m_key) != 0) {
            _group(key);
            m_vec->push_back(data);
            m_first = m_vec->end() - 1;
            m_firstValid = true;
        } else
            m_vec->push_back(data);
    }

    void finish(const std::wstring& key = L"")
    {
        _group(key);
    }

    void _group(const std::wstring& key)
    {
        if (!m_key.empty() && m_firstValid)
            m_callback(m_first, m_vec->end());
        m_key = key;
    }

protected:
    std::wstring m_key;
    std::vector<T>* m_vec;
    Iter m_first;
    bool m_firstValid;
    Callback m_callback;
};

#endif

