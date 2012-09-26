#ifndef merge_h
#define merge_h

#include <queue>
#include <vector>
using std::vector;
using std::pair;
using std::priority_queue;

/**
 * Less-than predicate for the priority_queue used in merge.
 */
template <typename Comparator, typename IterPair>
struct IteratorLessThan
{
    explicit IteratorLessThan(Comparator cmp)
    {
        m_cmp = cmp;
    }

    bool operator()(const IterPair& a, const IterPair& b)
    {
        return m_cmp(*(a.first), *(b.first));
    }

    Comparator m_cmp;
};


template <typename Comparator, typename N>
void merge(const vector< vector<N>* >& vectors, vector<N>& output, Comparator cmp)
{
	typedef vector< std::vector<N>* > VectorVector;
	typedef vector<N>::const_iterator Iter;	
	typedef pair<Iter, Iter> IterPair;
	typedef vector<IterPair> IterVec;
	typedef IteratorLessThan<Comparator, IterPair> LessThan;
	typedef priority_queue<IterPair, IterVec, LessThan> PQueue;

	LessThan lessThan(cmp);
	PQueue heap(lessThan);

    // Build the heap with (begin, end) pairs for each vector.
	for (VectorVector::const_iterator i = vectors.begin(); i != vectors.end(); ++i)
		heap.push(IterPair((*i)->begin(), (*i)->end()));

    while (heap.size()) {
        IterPair i = heap.top();
        N data = *i.first;
        heap.pop();

        i.first = i.first + 1;

        output.push_back(data);

        if (i.first != i.second)
            heap.push(IterPair(i.first, i.second));
    }
}

#endif
