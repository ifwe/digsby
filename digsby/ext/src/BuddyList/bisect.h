#ifndef Bisect_h
#define Bisect_h

#include <vector>
using std::vector;

/**
 * Returns the index at which elem can be inserted into vec so that vec remains
 * sorted by cmp. Insertion would be right of any elements equal to elem.
 */
template <class Iter, class Value, typename CMP>
Iter bisect_right(Iter begin, Iter end, const Value& val, CMP cmp)
{
    Iter mid;
    while (begin < end) {
        mid = begin + (end - begin) / 2;
        if ((*cmp)(val, *mid))
            end = mid;
        else
            begin = mid + 1;
    }

    return begin;
}

/**
 * Returns the index at which elem can be inserted into vec so that vec remains
 * sorted by cmp. Insertion would be left of any elements equal to elem.
 */
template <typename Iter, typename Value, typename CMP>
Iter bisect_left(Iter begin, Iter end, const Value& val, CMP cmp)
{
    Iter mid;
    while (begin < end) {
        mid = begin + (end - begin) / 2;
        if ((*cmp)(*mid, val))
            begin = mid + 1;
        else
            end = mid;
    }

    return begin;
}

/**
 * Inserts elem into vec. vec must already be sorted by cmp.
 */
template <typename T, typename CMP>
void insort_right(vector<T>& vec, const T& elem, CMP cmp)
{
    vec.insert(bisect_right(vec.begin(), vec.end(), elem, cmp), elem);
}

#endif
