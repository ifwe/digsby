#include "TreeList.h"

#include "BuddyList/config.h"
#include "BuddyList/Group.h"


/////
// all Elem* specific functionality goes here
////

bool _isExpandable(TreeListNode n)
{
    return n->asGroup() != 0;
}

static bool _hasChildren(TreeListNode n)
{
    return n->asGroup() != 0;
}

static const NodeVector& _getChildren(TreeListNode n)
{
    return n->asGroup()->children();
}

/////////

bool TreeListModel::expand(N node)
{
    bool expanded;
    if (m_collapsed.find(node) != m_collapsed.end()) {
        m_collapsed.erase(node);
        expanded = true;
    } else
        expanded = false;

    invalidateRange(indexOf(node), IndexLast);
    emitExpansionStateChangedEvent(node, true);

    return expanded;
}

void TreeListModel::cacheIndices()
{
    m_indices.clear();

    int c = 0;
    for(NodeVector::const_iterator i = m_flattenedList.begin();
        i != m_flattenedList.end(); ++i)
        m_indices[*i] = c++;
}

void TreeListModel::_flatten(N root, NodeVector& lst, DepthMap& depths, int depth /* = 0*/)
{
    if (hideRoot() && depth) // don't show root in flattened list
        lst.push_back(root);

    if (_hasChildren(root)) {
        const NodeVector& children = _getChildren(root);
        for(NodeVector::const_iterator i = children.begin(); i != children.end(); ++i) {
            N el = *i;
            depths[el] = depth;
            if (isExpandable(el) && isExpanded(el))
                _flatten(el, lst, depths, depth + 1);
            else
                lst.push_back(el);
        }
    }
}
    

TreeListSaveSelection::TreeListSaveSelection(TreeList* treelist)
    : m_treelist(treelist)
{
    m_elem = m_treelist->GetSelectedItem();
}

TreeListSaveSelection::~TreeListSaveSelection()
{
    if (m_elem) {
        int index = m_treelist->model()->indexOf(m_elem);
        m_treelist->SetSelection(index, false);
    }
}

void TreeList::OnRightDown(wxMouseEvent& e)
{
    // This is to provide slightly more native behavior--a right click down
    // means select an item. This does not prevent a popup.
    SetSelection(HitTest(e.GetPosition()));
    e.Skip(true);
}

void TreeList::OnKeyDown(wxKeyEvent& e)
{
    switch (e.GetKeyCode())
    {
        // TODO: make keybindings configurable
        case WXK_LEFT:
            GoLeft(e);
            break;
        case WXK_RIGHT:
            GoRight(e);
            break;
        case WXK_UP:
            GoUp();
            return e.Skip(false);
        case WXK_DOWN:
            GoDown();
            return e.Skip(false);
        case WXK_PAGEUP:
            PageUp();
            SetSelection(GetFirstVisibleLine());
            break;
        case WXK_PAGEDOWN:
            PageDown();
            SetSelection(GetFirstVisibleLine());
            break;
    }

    e.Skip(true);
}

void TreeList::GoLeft(wxKeyEvent& e)
{
    N obj = GetSelectedItem();

    if (e.GetModifiers() == wxMOD_SHIFT) {
        // shift + left: collapse all groups
        TreeListSaveSelection save(this);
        model()->collapseAll();
    } else if (obj && e.GetModifiers() == wxMOD_NONE)
        if (model()->isExpandable(obj) && model()->isExpanded(obj))
            model()->toggleExpand(obj);
        else
            selectParent(obj);
}

void TreeList::GoRight(wxKeyEvent& e)
{
    int i = GetSelection();
    N obj = GetSelectedItem();

    if (e.GetModifiers() == wxMOD_SHIFT) {
        // shift + right: expand all groups
        TreeListSaveSelection save(this);
        model()->expandAll();
    } else if (obj && e.GetModifiers() == wxMOD_NONE)
        if (model()->isExpandable(obj)) {
            if (!model()->isExpanded(obj))
                model()->toggleExpand(obj);
            else if (i + 1 < (int)GetItemCount() && GetParent(model()->itemAt(i + 1)) == obj)
                // right on a group: go to first child
                SetSelection(GetSelection() + 1);
        }
}

void TreeList::GoUp()
{
    int sel = GetSelection() - 1;
    if (sel >= 0) SetSelection(sel);
}

void TreeList::GoDown()
{
    int sel = GetSelection() + 1;
    if (sel < (int)GetItemCount()) SetSelection(sel);
}

bool TreeList::selectParent(N obj)
{
    N parent = GetParent(obj);
    if (parent) {
        int i = model()->indexOf(parent);
        if (i != -1) {
            SetSelection(i);
            return true;
        }
    }

    return false;
}

int TreeList::HitTestParent(const wxPoint& pos, float* percent)
{
    int i = HitTestEx(pos.x, pos.y, 0);
    if (i == -1)
        return -1;

    N parent = model()->parentOf(model()->itemAt(i));
    int j = model()->indexOf(parent);

    wxRect rect;
    if (j != -1) {
        rect = GetItemRect(j);
        i = j;
    } else
        rect = GetItemRect(i);

    if (percent)
        *percent = (float)(pos.y - rect.y) / (float)rect.height;

    return i;
}

