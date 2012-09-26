#include "precompiled.h"
#include "config.h"

#include "BuddyListSorter.h"
#include "Account.h"
#include "Group.h"

#include <boost/bind.hpp>
using boost::bind;
using boost::function;

#include <queue>
#include <string>
#ifdef __GNUC__
#include <ext/hash_map>
#else
#include <hash_map>
#endif
#include <iostream>

using stdext::hash_map;
using std::wstring;
using std::pair;
using std::wcout;
using std::endl;
using std::priority_queue;

/*
#include <fstream>
using std::wofstream;
using std::wclog;
*/

#include "NodePrivate.h"
#include "Sorters.h"
#include "Comparators.h"
#include "BuddyListSorterPrivate.h"
#include "Status.h"
#include "bisect.h"
#include "StringUtils.h"

typedef pair<Node::VecIter, Node::VecIter> IterPair;

/**
 * An adapter for ElemNodeComparator that acts as a less-than function for two
 * iterators pointing at vectors of Node*. The value of each iterator is considered
 * to be the value of the first Node* at the position in the vector pointed to
 * by the iterator.
 */
struct iter_pair_less
{
    explicit iter_pair_less(ElemNodeComparator cmp)
    {
        m_cmp = cmp;
    }

    bool operator()(const IterPair& a, const IterPair& b)
    {
        // swapping a and b here is intentional. we want the minimum element
        // to be at the top() of our priority_queue, but by default it does
        // max element.
        return (*m_cmp)(*(b.first), *(a.first));
    }

    ElemNodeComparator m_cmp;
};

typedef MultiComparator<const Node*> NodeMultiComparator;

BuddyListSorter::BuddyListSorter()
    : m_root(0)
    , m_rootElem(0)
    , m_pruneEmpty(false)
{
/*
    static bool didInitLog = false;
    if (!didInitLog) {
        wofstream* out = new wofstream("c:\\log.txt");
        BL_ASSERT(*out);
        wclog.rdbuf(out->rdbuf());
    }
*/    
    // default to sorting by Name
    vector<SortBy> defaultCompares;
    defaultCompares.push_back(CustomOrder);
    defaultCompares.push_back(Name);
    m_cmp = new NodeMultiComparator(defaultCompares);
    m_contacts = new Contacts();
    _updateSortsBy();
}

BuddyListSorter::~BuddyListSorter()
{
    clearSorters();

    delete m_cmp;

    // Must delete Groups before Contacts, since they have references to Contacts
    // but not vice versa.
    clearNodes();

    if (m_contacts)
        delete m_contacts;
}

void BuddyListSorter::clearNodes()
{
    if (m_root) {
        delete m_root;
        m_root = 0;
    }

    if (m_rootElem) {
        delete m_rootElem;
        m_rootElem = 0;
    }
}

void BuddyListSorter::setComparators(const vector<SortBy>& cmps)
{
    if (m_cmp)
        delete m_cmp;

    m_cmp = new NodeMultiComparator(cmps);
    _updateSortsBy();
}

void BuddyListSorter::_updateSortsBy()
{
    m_sortsByFlags = m_cmp->sortsByFlags();

    m_hasFakeRoot = false;
    m_fakeRootName = L"";

    foreach (Grouper* g, m_groupers) {
        m_sortsByFlags |= g->sortsByFlags();
        if (g->hasFakeRoot()) {
            m_hasFakeRoot = true;
            m_fakeRootName = reinterpret_cast<ByFakeRoot*>(g)->fakeRootName();
        }
    }

    m_contacts->setDirty(true);
}

void BuddyListSorter::addSorter(Grouper* grouper)
{
    m_groupers.push_back(grouper);
    _updateSortsBy();
}

void BuddyListSorter::clearSorters()
{
    foreach(Grouper* g, m_groupers)
        delete g;
    m_groupers.clear();
    _updateSortsBy();
}

/**
 * Make a copy of an Elem tree. All Groups are copied; all Contact and Buddy objects
 * are not.
 */
static Group* copyGroups(Group* g)
{
    Group* copy = g->copy();

    foreach (Elem* child, g->children()) {
        BL_ASSERT(child != g);
        Group* groupChild = child->asGroup();
        if (groupChild)
            copy->addChild(copyGroups(groupChild));
        else
            copy->addChild(child);
    }

    return copy;
}

void BuddyListSorter::setRoot(Elem* rootElem)
{
    Group* group = rootElem->asGroup();
    BL_ASSERT(group);

    if (m_root)
        delete m_root;
    if (m_rootElem)
        delete m_rootElem;

    m_rootElem = copyGroups(group);
    m_root = toNode(m_rootElem);
}

static bool _shouldUseFakeRootKey(Node* node, const wstring& fakeRootName)
{
    while (Node* parent = node->parent())
        if (parent->data() && CaseInsensitiveEqual(parent->name(), fakeRootName))
            return true;
        else
            node = parent;

    return false;
}

Node* BuddyListSorter::toNode(Elem* elem, Node* parent)
{
    int nodeFlags = 0;

    // Turn buddies into their contacts
    if (Buddy* b = elem->asBuddy()) {
        elem = b->contact();
        nodeFlags |= FlagLeaf;
    } else if (Group* g = elem->asGroup()) {
        if (g->root())
            nodeFlags |= FlagRootGroup;
    }

    Node* node = new Node(elem, parent);
    node->addFlags(nodeFlags);
    if (hasFakeRoot() && _shouldUseFakeRootKey(node, fakeRootName()))
        node->setUserOrder(m_contacts->userOrder(node, fakeRootName(), fakeRootGroupKey()));
    else
        node->setUserOrder(m_contacts->userOrder(node, fakeRootName()));

    if (Group* g = elem->asGroup())
        foreach(Elem* child, g->children())
            insort(node, toNode(child, node));

    return node;
}

void BuddyListSorter::insort(Node* node, Node* child, int parentFlags)
{
    // as an optimization, we pass a parentFlags bitfield down through the
    // recusive insorts. each Grouper can modify and look at result->parentFlags
    // and make decisions based on its value.
    BucketResult result(parentFlags);
    bool newNode = true;

    if (key(node, child, &result)) {
        // child will go into m_map
        newNode = false;
        Node* bucketNode = node->insertBucketNode(child, &result, newNode);

        if (bucketNode != child) {
            if (!bucketNode->hasFlag(FlagSkipGroup))
                updateUserOrder(bucketNode);

            if (child->setParent(bucketNode))
                updateUserOrder(child);

            this->insort(bucketNode, child, result.parentFlags);
        }
        child = bucketNode;
    }

    // child always goes into m_list (note that child may be different
    // than it was at the start of the function)
    if (newNode)
        _sortedInsert(node, child, listCompare(node));
}

bool BuddyListSorter::key(Node* node, Node* child, BucketResult* result)
{
    // Each Grouper object gets a chance to look at the node we're insorting
    // and decide whether it wants to do something about it. If one of them
    // does, its key method will return true and the BucketResult will
    // contain information about what to do next.
    foreach (Grouper* g, m_groupers)
        if (g->key(node, child, result))
            return true;

    return false;
}

// merging is implemented via two passes down and up the tree:
//
// pass 1) _merge and _merge_children apply any necessary "skip node"
//         transformations to the tree by bringing up children. nodes
//         with equal keys are put into their parent Nodes' m_map
//         together (no actual merge happens yet)
//
//         this pass makes a copy--the original tree is untouched

Node* BuddyListSorter::gather()
{
    BL_ASSERT(root());

    // pass 1
    Node* realparent = root()->copy(NULL);
    _merge(root()->children(), realparent);

    // pass 2: see the comment below
    _descendMerge(realparent);

    // The conditions for pruning some nodes are not known until all passes are done.
    _finalPrune(realparent);

    return realparent;
}

void BuddyListSorter::_finalPrune(Node* node)
{
    Node::Vector& children = node->children();
    Node::Vector::iterator i = children.begin();
    while (i != children.end()) {
        Node* child = *i;
        if (shouldPruneNode(child, 2)) {
            i = children.erase(i);
            delete child;
        } else {
            _finalPrune(child);
            ++i;
        }
    }
}

Node* BuddyListSorter::_findParent(Node* realparent, Node* child)
{
    // The FlagGroupInRoot flag means that the child Node should be merged into
    // the root Node's children.
    if (child->hasFlag(FlagGroupInRoot))
        return realparent->root();
    else
        return realparent;
}

/**
 * Used to compare node names and keep the most capitalized one.
 */
struct NodeNameCaseInsensitiveLess : public MostCapitalizedLess
{
    NodeNameCaseInsensitiveLess(const wstring& lower)
        : MostCapitalizedLess(lower)
    {}

    bool operator()(Node* a, Node* b)
    {
        return MostCapitalizedLess::less(a->name(), b->name());
    }
};

void BuddyListSorter::updateUserOrder(Node* n)
{
    n->setUserOrder(m_contacts->userOrder(n, fakeRootName()));
}

void BuddyListSorter::_merge(const Node::Vector& mergeNodes, Node* realparent)
{
#if 0
    printf("*****\n");
    printf("merge("); wcout << *realparent; printf(" <- [\n"); dumpNodeList(mergeNodes);
    printf("])\n");
#endif

    typedef hash_map<wstring, Node::Vector> BucketMap;
    typedef pair<wstring, Node::Vector> BucketMapItem;

    Node::Vector skipNodes;
    BucketMap map;

    foreach (Node* subNode, mergeNodes) {
        // If the Node has FlagPruneTree then we abandon it here.
        if (shouldPruneNode(subNode)) {
            realparent->addMissing(subNode);
            continue;
        }

        if (shouldSkipNode(subNode)) {
            // "skipping" a Node means that all of its children get reinserted
            // one level up.
            skipNodes.push_back(subNode);
        } else {
            if (subNode->hasKey()) {
                // Here we lowercase the key to merge Groups with similar names that
                // vary by case.
                map[wstringToLower(subNode->key())].push_back(subNode);
            } else {
                // _findParent may return a different Node to do a sorted insertion
                // on than realparent, depending on subNode's flags.
                Node* p = _findParent(realparent, subNode);

                Node* newChild = subNode->copy(realparent);
                updateUserOrder(newChild);
                _sortedInsert(p, newChild, listCompare(p));
            }
        }
    }

    // Merge children of nodes with the same key into one new Node for each key.
    foreach (BucketMapItem item, map) {
        const Node::Vector& vec = item.second;
        if (!vec.empty()) {
            Node* node = vec[0]->copy(realparent);
            updateUserOrder(node);

            // Keep the most cApiTaliZed Group name.
            Node* mostCapitalizedNode = *std::max_element(vec.begin(), vec.end(), NodeNameCaseInsensitiveLess(wstringToLower(node->name())));
            node->setName(mostCapitalizedNode->name());

            _merge_children(item.second, node, true);
            Node* p = _findParent(realparent, node);

            _mergeInsert(p, node, listCompare(p));

            // If we've taken moved a subgroup, then mark missing children
            // in the original parent.
            if (p != realparent)
                realparent->addMissing(node);
        }
    }

    // Insert all child nodes of nodes we decided to skip above into realparent.
    if (!skipNodes.empty())
        _merge_children(skipNodes, realparent);
}

void BuddyListSorter::_merge_children(const Node::Vector& nodes, Node* realparent, bool firstIsCopy)
{
#if 0
    printf("merging children: [\n");
    foreach(Node* c, nodes)
        wcout << "    " << *c << endl;
    printf("]\n");
#endif

    Node::Vector children;
    int n = 0;
    foreach(Node* keyNode, nodes) {
        if (!firstIsCopy || n > 0) {
            realparent->mergeElem(keyNode);
        }

        foreach(Node* child, keyNode->children())
            children.push_back(child);

        ++n;
    }
    _merge(children, realparent);
}

// merge
//
// pass 2) on this pass any Nodes with multiple elements in an m_map get
//         those elements merged
//
//         this pass is destructive--the tree passed to _descendMerge is
//         modified
//
void BuddyListSorter::_descendMerge(Node* node)
{
    // if any Node* child has more than one element in an m_map
    // bucket, give the range to _sorted_merge
    foreach(Node::MapItem item, node->map())
        if (item.second.size() > 1)
            _sorted_merge(item.second.begin(), item.second.end());
}

void BuddyListSorter::_sorted_merge(const Node::VecIter& begin, const Node::VecIter& end)
{
    // If there is only one, or no Nodes to merge, just return.
    if (end - begin <= 1)
        return;

    typedef Node::VecIter Iter;
    typedef vector<IterPair> IterVec;

    // here we're sorting n sorted lists with priority_queue, which
    // is a heap backed by a vector
    //
    // the heap is of iterator pairs <iterator, end_iterator>,
    // sorted by value of element pointed to by the first iterator
    //
    // TODO: replace this function with the generic one in merge.h

    Node* firstNode = *begin;
    iter_pair_less iterLess(listCompare(firstNode));
    priority_queue<IterPair, IterVec, iter_pair_less> heap(iterLess);

    // build the heap
    int total = 0;
    for(Node::Vector::const_iterator i = begin; i != end; ++i) {
        Node* node = *i;
        //merge flags from merged nodes, they may be needed later
        //specific case: fake root group needs to merge based on key
        //has the same name, but different flags.
        firstNode->addFlags(node->flags());
        if (i != begin)
            firstNode->copyMissing(node);

        // recurse here to merge similar keys deeper in the tree
        _descendMerge(node);

        Node::Vector& children = node->children();
#if 0
        wcout << node << " [" << endl;
        dumpNodeList(children);
        wcout << "]" << endl;
#endif
        if (children.size()) {
            heap.push(IterPair(children.begin(), children.end()));
            total += children.size();
        }
    }

    // grouper will notice adjacent Nodes with equal keys and recurse
    // _sorted_merge with them
    Node::Vector newChildren;
    GroupByKey<Node*> grouper(&newChildren, total,
            bind(&BuddyListSorter::_sorted_merge, this, _1, _2));

    // 1) pop an iterator pair off the heap, adding the first one's
    //    elem as a child
    // 2) increment the 1st iterator. if it's not == end() (the 2nd),
    //    push it back onto the heap (the elem it NOW points to will
    //    be the value used during the heapify)
    // 3) repeat
    Node* lastNode = NULL;
    while (heap.size()) {
        IterPair i = heap.top();
        Node* child = *(i.first);
        heap.pop();
        i.first = i.first + 1;

        // Adjacent leaves may need merging.
        if (lastNode && shouldMergeLeaves(lastNode, child)) {
            delete child;
            lastNode = NULL;
        } else {
            // grouper.push_back will call _sorted_merge with a new range
            // from newChildren if it finds adjacent equal keys
            grouper.push_back(child);
            if (child->setParent(firstNode))
                updateUserOrder(child);
            lastNode = child;
        }

        if (i.first != i.second)
            heap.push(IterPair(i.first, i.second));
    }

    grouper.finish();
    firstNode->setChildren(newChildren);

    // delete all nodes except the first
    for(Node::Vector::const_iterator i = begin + 1; i != end; ++i) {
        Node* node = *i;
        node->children().clear(); // this node's children are owned by *begin now
        delete node;
    }
}

bool BuddyListSorter::shouldSkipNode(Node* node)
{
    if (node->hasFlag(FlagSkipGroup))
        return true;

    return false;
}

bool BuddyListSorter::shouldPruneNode(Node* node, int pass)
{
    if (node->hasFlag(FlagPruneTree))
        return true;

    // If pruneEmpty() is true, we're dropping Nodes with no children,
    // but with some missing().
    if (pass == 2 &&
        pruneEmpty() && 
        node->numLeaves(false) == 0 &&
        node->missing() > 0)
        return true;

    return false;
}

bool BuddyListSorter::shouldMergeLeaves(Node* a, Node* b)
{
    if (a->isLeaf() && b->isLeaf()) {
        Contact* x = reinterpret_cast<Contact*>(a->data());
        Contact* y = reinterpret_cast<Contact*>(b->data());
        if (x->name() == y->name() && x->service() == y->service()) {
            // here we are merging duplicate buddies, but we want to keep the most
            // available one.
            if (a->data() != b->data() && compareStatuses(x->status(), y->status()) < 0)
                a->setData(b->data());

            return true;
        }
    }

    return false;
}

bool BuddyListSorter::shouldMergeNodes(const Node::VecIter& i, const Node::VecIter& begin, const Node::VecIter& end, Node* child)
{
    if (i != end && shouldMergeLeaves(*i, child))
        return true;

    // hack for userOrder() being wrong after a reparent.
    else if (i != begin) {
        Node::VecIter j = i - 1;
        Node* sibling = *j;
        if (child->userOrder() == sibling->userOrder())
            return shouldMergeNodes(j, begin, end, child);
    }

    return false;
}

void BuddyListSorter::_sortedInsert(Node* parent, Node* child, ElemNodeComparator cmp)
{
    typedef Node::Vector::iterator Iter;

    Node::Vector& vec = parent->vector();

    Iter end(vec.end());
    // wclog << endl << "inserting " << *child << " into " << *parent << endl;
    Iter i = bisect_left(vec.begin(), end, child, cmp);
    
    // If the element immediately to the right of our insertion point is equal
    // to the Node we're inserting, then ignore the insert.
    if (shouldMergeNodes(i, vec.begin(), end, child))
        delete child;
    else {
//      if (parent->hasDupe(child))
//          BL_ASSERT(0);
        vec.insert(i, child);
    }
}

void BuddyListSorter::_mergeInsert(Node* parent, Node* child, ElemNodeComparator cmp)
{
    if (child->setParent(parent))
        updateUserOrder(child);

    wstring key(wstringToLower(child->key()));
    if (!key.empty()) {
        Node::Map::const_iterator i = parent->map().find(key);
        bool keyExists = i != parent->map().end();

        // always store a keyed Node in the map list
        parent->map()[key].push_back(child);

        // only do a sorted insert if this is the first Node with that key
        if (keyExists)
            return;
    }

    _sortedInsert(parent, child, cmp);
}

