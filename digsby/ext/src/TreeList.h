#ifndef TreeList_h
#define TreeList_h

#include "SkinVList.h"

#include <set>
#include <vector>
#include <hash_map>
using std::vector;
using std::set;
using stdext::hash_map;

#include "BuddyList/config.h"
#include "BuddyList/BuddyListCommon.h"

typedef Elem* TreeListNode;
typedef vector<TreeListNode> NodeVector;

class TreeList;

bool _isExpandable(TreeListNode n);

/**
 * Used by TreeList to display a tree in list form.
 *
 * Provides mapping between tree and list data structures.
 */
class TreeListModel
{
    typedef TreeListNode N;
protected:
    typedef set<N> NodeSet;
    typedef hash_map<N, int> IndicesMap;
    typedef hash_map<N, int> DepthMap;
    typedef vector<N> NodeVector;

public:
    static const int IndexLast = -1;

    TreeListModel(N root = 0)
        : m_hideRoot(true)
        , m_root(root)
    {
    }

    void setRoot() const;

    N root() const { return m_root; }

    /**
     * Returns true if the root node will be hidden.
     */
    bool hideRoot() const { return m_hideRoot; }

    /**
     * Sets whether to hide the root node or not.
     */
    void setHideRoot(bool hideRoot) { m_hideRoot = hideRoot; }

    /**
     * Expands the given Node so that its children are visible.
     */
    bool expand(N node);

    /**
     * Expands all container Nodes so that their children are visible.
     */
    bool expandAll()
    {
        wxLogMessage(wxT("TODO: expandAll"));
        return true;
    }

    /**
     * Collapses the given Node so that its children are hidden.
     */
    bool collapse(N node)
    {
        bool collapsed = m_collapsed.insert(node).second;
        invalidateRange(indexOf(node), IndexLast);
        emitExpansionStateChangedEvent(node, false);
        return collapsed;
    }

    /**
     * Collapses all container Nodes so that their children are hidden.
     */
    int collapseAll()
    {
        wxLogMessage(wxT("TODO: collapseAll"));
        return 0;
    }
    
    bool toggleExpand(N node)
    {
        if (!isExpandable(node))
            return false;
        else if (isExpanded(node))
            return collapse(node);
        else
            return expand(node);
    }

    N itemAt(size_t i) const
    {
        BL_ASSERT(i < m_flattenedList.size());
        return m_flattenedList[i];
    }

    int indexOf(N child)
    {
        IndicesMap::const_iterator i = m_indices.find(child);
        if (i != m_indices.end())
            return i->second;
        else
            return -1;
    }
    
    bool isExpandable(N node)
    {
        return _isExpandable(node);
    }

    bool isExpanded(N child)
    {
        return m_collapsed.find(child) == m_collapsed.end();
    }

    void _flatten(N root, NodeVector& lst, DepthMap& depths, int depth = 0);

    void updateList()
    {
        m_depths.clear();
        m_flattenedList.clear();
        _flatten(root(), m_flattenedList, m_depths);
        cacheIndices();
    }

    /*
     * Stores a map of Node -> index
     */
    void cacheIndices();

    N parentOf(N child)
    {
        BL_ASSERT(false && "need to implement");
        (void*)child;
        return 0; // return child->parent();
    }

    void emitExpansionStateChangedEvent(N node, bool expanded)
    {
        // TODO
        (void*)node;
        (void*)expanded;
    }

    void invalidateRange(int a, int b)
    {
        // TODO
        (void*)a;
        (void*)b;
    }

    void setRoot(N node)
    {
        m_root = node;
        updateList();
    }

protected:

    NodeSet m_collapsed;
    IndicesMap m_indices;
    DepthMap m_depths;
    NodeVector m_flattenedList;

    N m_root;
    bool m_hideRoot;

};

/**
 * A stack object helper that saves a treelist's selection on construction and
 * restores it on destruction.
 */
class TreeListSaveSelection
{
public:
    TreeListSaveSelection(TreeList* treelist);
    ~TreeListSaveSelection();

protected:
    TreeListNode m_elem;
    TreeList* m_treelist;
};


/**
 * Displays hierarchical data in a list.
 */
class TreeList : public SkinVList
{
public:
    typedef TreeListNode N;
    typedef std::vector<unsigned int> CellHeightVector;

    TreeList(wxWindow* parent, wxWindowID id = wxID_ANY, int style = wxLB_SINGLE)
        : SkinVList(parent, id, style)
    {
        m_model = new TreeListModel();
    }

    virtual ~TreeList()
    {}

    TreeListModel* model() const { return m_model; }

    /**
     * Returns the selected node, or NULL.
     */
    N GetSelectedItem() const
    {
        int i = GetSelection();
        return i != -1 ? GetItemAt(i) : NULL; 
    }

    /**
     * Returns the Node at the given index.
     */
    N GetItemAt(int i) const
    {
        return model()->itemAt(i);
    }

    /**
     * Returns a Node's parent.
     */
    N GetParent(N obj) const
    {
        return model()->parentOf(obj);
    }

    /**
     * For an (x, y) coordinate, returns the parent Node and percentage
     * over the parent and its children.
     */
    int HitTestParent(const wxPoint& pos, float* percent);

    /**
     * Given a Node, selects that Node's parent.
     */
    bool selectParent(N obj);

    /**
     * Sets the new root node.
     */
    void SetRoot(N root)
    {
        model()->setRoot(root);
    }

protected:
    void OnRightDown(wxMouseEvent& e);
    void OnKeyDown(wxKeyEvent& e);

    void GoLeft(wxKeyEvent& e);
    void GoRight(wxKeyEvent& e);
    void GoUp();
    void GoDown();

    CellHeightVector m_heights;
    TreeListModel* m_model;
};

#endif // TreeList_h

