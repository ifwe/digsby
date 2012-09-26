#ifndef NodePrivate_h
#define NodePrivate_h

#include <boost/bind.hpp>
#include <boost/function.hpp>
using boost::bind;
using boost::function;
// stores the result of key() functions in Groupers below
//
// a function type that returns a bucket Node*
typedef function<Node*(Node* data, Node* parent)> BucketFunction;


struct BucketResult
{
    BucketResult(int parentFlags_)
        : parentFlags(parentFlags_)
    {}

    /**
     * Returns true if the given flag is set in this BucketResult's
     * parentFlags field.
     */
    bool hasFlag(NodeFlag flag) const
    {
        return (parentFlags & flag) != 0;
    }

    wstring key;
    BucketFunction bucketFunc;
    int parentFlags;
};

#endif

