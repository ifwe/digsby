#ifndef Node_h
#define Node_h

#include "dbgnew.h"
#ifdef __GNUC__
#include <ext/hash_map>
#else
#include <hash_map>
#endif
#include <string>
#include <sstream>
#include <vector>
#include <iostream>
#ifdef __GNUC__
#include <ext/hash_set>
#else
#include <hash_set>
#endif

#include "GNUC.h"

using stdext::hash_set;
using stdext::hash_map;

using std::wstring;
using std::wstringstream;
using std::wostream;
using std::pair;
using std::vector;

class Elem;
class Grouper;
class Node;

#include "BuddylistCommon.h"
#include "Comparators.h"

// NOTE: when modifying this enum, please update the table in stringForNodeFlag
// in Node.cpp
enum NodeFlag
{
    FlagStatusGroup  = 1<<0,
    FlagServiceGroup = 1<<1,
    FlagUserGroup    = 1<<2,
    FlagSkipGroup    = 1<<3,
    FlagPruneTree    = 1<<4,
    FlagGroupInRoot  = 1<<5,
    FlagOfflineGroup = 1<<6,
    FlagMobileGroup  = 1<<7,
    FlagFakeGroup    = 1<<8,
    FlagLeaf         = 1<<9,
    FlagRootGroup    = 1<<10,
    FlagSearchGroup  = 1<<11,
};

wstring BL_EXPORT stringForNodeFlags(int flags, const wstring& sep = L" | ");

void printIndent(int indent);
wostream& operator<<(wostream& out, const Node& r);
void dumpNodeList(const vector<Node*>& nodes, bool newline = true);

/**
 * Dumps a Node* tree to stdout.
 */
void BL_EXPORT dumpTree(Node* node, bool showAddresses = true, bool showFlags = false, bool showGroupNames = false);

/**
 * Returns a string representation of a Node* tree.
 */
std::wstring BL_EXPORT treeToString(Node* node, bool showAddresses = true, bool showFlags = false, bool showGroupNames = false, int indent = 0);

struct BucketResult;
typedef MultiComparator<const Node*>* ElemNodeComparator;

void BL_EXPORT setNodeTracking(bool);
void BL_EXPORT dumpNodes();


/**
 * The tree node used by the sorter.
 */
class BL_EXPORT Node
{
private:
    Node(const Node&);
    const Node& operator=(const Node&);

public:
    typedef vector<Node*> Vector;
    typedef vector<Node*>::const_iterator VecIter;
    typedef hash_map<wstring, Vector> Map;
    typedef pair<wstring, Vector> MapItem;

    Map& map() { return m_map; }
    Vector& vector() { return m_list; }
    Vector& children() { return m_list; }
    size_t numChildren() const { return m_list.size(); }
    bool hasChildren() const { return !m_list.empty(); }
    void setChildren(const Vector& list) { m_list = list; }
    Elem* data() const { return m_data; }
    bool isLeaf() const  { return (flags() & FlagLeaf) != 0; }
    void setData(Elem* data) { m_data = data; }

    wstring repr() const;

    Node(Elem* data, Node* parent);
    ~Node();

    void mergeElem(Node* other);

    Node* copy(Node* parent)
    {
        Node* n = new Node(data(), parent);
        n->setFlags(flags());
        n->setName(name());
        n->setKey(key());
        n->setComparator(comparator());
        n->setUserOrder(userOrder());
        n->setCustomOrder(customOrder());
        n->m_missing = m_missing;
        return n;
    }

    int userOrder() const { return m_userOrder; }
    void setUserOrder(int userOrder) { m_userOrder = userOrder; }

    Node* root() { return m_parent ? m_parent->root() : this; }

    Node* nthParent(unsigned int n) const
    {
        Node* p = (Node*)this;
        while (n-- && p)
            p = p->parent();
        return p;
    }

    /**
     * Returns this Node's parent Node. May be NULL if this Node is a root.
     */
    Node* parent() const { return m_parent; }

    /**
     * Sets this Node's parent.
     */
    bool setParent(Node* parent)
    {
        bool different = m_parent != parent;
        m_parent = parent;
        return different;
    }

    /**
     * Returns this Node's name.
     */
    wstring name() const { return m_name; }
    void setName(const wstring& name) { m_name = name; }

    wstring key() const { return m_key; }
    void setKey(const wstring& key) { m_key = key; }

    bool hasKey() const { return !m_key.empty(); }

    int flags() const { return m_flags; }
    bool hasFlag(int flag) const { return (m_flags & flag) != 0; }
    void setFlags(int flags) { m_flags = flags; }
    void addFlags(int flag) { m_flags |= flag; }
    void removeFlags(int flag) { m_flags &= ~flag; }

    ElemNodeComparator comparator() const { return m_cmp; }
    void setComparator(ElemNodeComparator cmp) { m_cmp = cmp; }

    int customOrder() const { return m_customOrder; }
    void setCustomOrder(int customOrder) { m_customOrder = customOrder; }

    size_t missing() const { return m_missing.size(); }
    void addMissing(Node* node);
    void copyMissing(Node* node);

    bool hasDupe(Node *n);
    
    Node* insertBucketNode(Node* child, BucketResult* result, bool& newNode);
    bool isSorted(ElemNodeComparator cmp) const;

    /**
     * Returns the number of non-container nodes in the sub tree rooted at this
     * Node. If includeMissing is true (the default), the count includes nodes
     * moved/pruned (i.e. missing).
     */
    int numLeaves(bool includeMissing = true) const;
    void leaves(Vector& nodes) const;

protected:
    wstring m_name;
    wstring m_key;
    Node* m_parent;
    Map m_map;          // links to other container nodes
    Vector m_list;      // maintained as a sorted list of leaf nodes
    Elem* m_data;

    int m_flags;
    int m_userOrder;
    ElemNodeComparator m_cmp;

    int m_customOrder;
    hash_set<wstring> m_missing;
};

#endif // Node_h

