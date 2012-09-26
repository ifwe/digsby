#include "precompiled.h"
#include "config.h"
#include "Node.h"

#include <string>
#include <sstream>
#include <iostream>
#include <map>
using std::wostream;
using std::wostringstream;
using std::wcout;
using std::endl;
using std::wstring;

#include "NodePrivate.h"
#include "Group.h"
#include "ContactData.h"

Node::Node(Elem* data, Node* parent)
    : m_data(data)
    , m_parent(parent)
    , m_name(data ? data->name() : L"")
    , m_flags(0)
    , m_cmp(NULL)
    , m_customOrder(0)
    , m_userOrder(0)
{
    if (data)
        m_name = data->name();

#ifdef TRACK_NODE_ALLOCS
    gs_nodeSet.insert(this);
#endif
}

Node::~Node()
{
    // Nodes destroy their children
    foreach(Node* child, m_list)
        delete child;

#ifdef TRACK_NODE_ALLOCS
    gs_nodeSet.erase(this);
#endif
}

Node* Node::insertBucketNode(Node* child, BucketResult* result, bool& newNode)
{
    BL_ASSERT(!result->key.empty());
    BL_ASSERT(!result->bucketFunc.empty());

    Node* bucketNode;
    Node::Map::const_iterator i = m_map.find(result->key);

    if (i != m_map.end()) {
        // the bucket was found
        bucketNode = i->second[0];
    } else {
        // bucket doesn't exist yet; use result->bucketFunc
        // to create one
        Node* bucket = result->bucketFunc(child, this);
        bucket->setKey(result->key);
        bucketNode = bucket;
        m_map[result->key].push_back(bucket);
        BL_ASSERT(m_map[result->key].size() == 1);
        newNode = true;
    }

    BL_ASSERT(!m_map.empty());
    return bucketNode;
}

wstring Node::repr() const
{
    wstringstream ss; ss << *this; return ss.str();
}

bool Node::isSorted(ElemNodeComparator cmp) const
{
    Vector cpy(m_list);
    sort(cpy.begin(), cpy.end(), *cmp);
    return cpy == m_list;
}

int Node::numLeaves(bool includeMissing /*= true*/) const
{
    int total = 0;

    foreach(Node* n, m_list)
        if (n->hasFlag(FlagLeaf))
            total += 1;
        else
            total += n->numLeaves(includeMissing);

    if (includeMissing)
        total += m_missing.size();

    return total;
}

void Node::leaves(Vector& nodes) const
{
    foreach (Node* n, m_list)
        if (n->hasFlag(FlagLeaf))
            nodes.push_back(n);
        else
            n->leaves(nodes);
}

void Node::addMissing(Node* missingParent)
{
    Vector missingNodes;
    missingParent->leaves(missingNodes);
    foreach (Node* n, missingNodes)
        m_missing.insert(n->data()->hash());
}

void Node::copyMissing(Node* nodeToCopy)
{
    foreach (wstring hash, nodeToCopy->m_missing)
        m_missing.insert(hash);
}

void Node::mergeElem(Node* other)
{
    Elem* otherElem = other->data();
    if (otherElem) {
        if (data())
            data()->merge(otherElem);
        else
            setData(otherElem);
    }

    addMissing(other);
}

bool Node::hasDupe(Node* node)
{
    if (!node->data())
        return false;

    wstring h(node->data()->hash());
    if (h.empty())
        return false;

    foreach(Node* n, children())
        if (n->data())
            if (n->data() == node->data() || n->data()->hash() == h)
                return true;

    return false;
}

// For outputting Nodes to << ostream
wostream& operator<<(wostream& out, const Node& node)
{
    // custom order
    //if (!node.name().empty())
        //out << node.name() << "[" << node.customOrder() << "] ";

    if (node.data())
        out << node.data()->repr();
    else
        out << "<null data>";

    if (node.hasKey())
        out << " key=" << node.key();

    return out;
}

void dumpNodeList(const Node::Vector& nodes, bool newline)
{
    foreach(Node* node, nodes) {
        if (newline) wcout << "    ";
        wcout << *node << ",";
        if (newline) wcout << endl;
        else wcout << " ";
    }
}

/*
 * dumps a Node tree out to stdout
 */
void dumpTree(Node* node, bool showAddresses, bool showFlags, bool showGroupNames)
{
    std::wcout.imbue(std::locale(""));
    std::wcout << treeToString(node, showAddresses, showFlags, showGroupNames, 0);
}

static void printIndent(wostream& wcout, int indent)
{
    static const int num_spaces = 4;
    for (int c = 0; c < indent * num_spaces; ++c)
        wcout << " ";
}

std::wstring treeToString(Node* node, bool showAddresses, bool showFlags, bool showGroupNames, int indent)
{
    const bool showMissing = true;

    wostringstream wcout;

    if (!node) {
        wcout << "<null>";
        return wcout.str();
    }

    if (showAddresses)
        wcout << node << "\t";

    printIndent(wcout, indent);
    wcout << node->repr();

    if (showMissing)
        wcout << " " << node->missing() << "m" << node->numLeaves(false) << "f";
    if (showFlags)
        wcout << " (" << stringForNodeFlags(node->flags()) << ")";
    /*
    if (showGroupNames) {
        wstring category, key;
        userOrderInfo(node, category, key);
        wcout << " (" << category << ", " << key << ")";
    }
    */

    Node::Vector children(node->children());

    if (children.size()) {
        wcout << endl;
        Node::Vector::const_iterator i = children.begin();
        while (true) {
            Node* child = *i++;
            wcout << treeToString(child, showAddresses, showFlags, showGroupNames, indent + 1);

            if (child->parent() != node) wcout << " XXX";
            if (i == children.end())     break;
            else wcout << endl;
        }
    }

    if (indent == 0)
        wcout << endl;

    return wcout.str();
}

#ifdef TRACK_NODE_ALLOCS
#include <hash_set>
using stdext::hash_set;

bool gs_nodeTracking = false;
hash_set<Node*> gs_nodeSet;

/**
 * If #define TRACK_NODE_ALLOCS existed at compile time, then this function
 * enables tracking of all Node construction and destruction. See dumpNodes().;
 */
void setNodeTracking(bool nodeTracking)
{
    gs_nodeTracking = nodeTracking;

    if (!nodeTracking)
        gs_nodeSet.clear();
}

/**
 * If setNodeTracking(true) was called and we had #define TRACK_NODE_ALLOCS at
 * compile time, then this function will output the Node::repr() string for
 * each "live" Node object.
 */
void dumpNodes()
{
    if (!gs_nodeTracking) {
        fprintf(stderr, "Node tracking is not enabled.\n");
        return;
    }

    foreach (Node* node, gs_nodeSet)
        fprintf(stderr, "%ws\n", node->repr().c_str());

    fprintf(stderr, "%d nodes.\n", gs_nodeSet.size());
}
#else
void setNodeTracking(bool nodeTracking) {}
void dumpNodes()
{
    fprintf(stderr, "must #define TRACK_NODE_ALLOCS\n");
}
#endif

static const wchar_t* stringForNodeFlag(NodeFlag f)
{
    switch (f) {
        case FlagStatusGroup:  return L"StatusGroup";
        case FlagServiceGroup: return L"ServiceGroup";
        case FlagUserGroup:    return L"UserGroup";
        case FlagSkipGroup:    return L"SkipGroup";
        case FlagPruneTree:    return L"PruneTree";
        case FlagGroupInRoot:  return L"GroupInRoot";
        case FlagOfflineGroup: return L"OfflineGroup";
        case FlagMobileGroup:  return L"MobileGroup";
        case FlagFakeGroup:    return L"FakeGroup";
        case FlagLeaf:         return L"Leaf";
        case FlagRootGroup:    return L"RootGroup";
        case FlagSearchGroup:  return L"SearchGroup";

        default:
            return NULL;
    }
}

wstring stringForNodeFlags(int flags, const wstring& sep)
{
    wostringstream s;

    bool first = true;
    for (int x = 0; x < sizeof(int) * 8; ++x) {
        int flag = (1 << x);
        if (flags & flag) {
            if (const wchar_t* name = stringForNodeFlag(static_cast<NodeFlag>(flag))) {
                if (!first)
                    s << sep;
                else
                    first = false;
                s << name;
            }
        }
    }

    return s.str();
}

