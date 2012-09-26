#include "precompiled.h"
#include "config.h"

#include "BuddyListSorter.h"
#include "Group.h"
#include "StringUtils.h"
#include "Sorters.h"

#include <sstream>
using std::wostringstream;
using std::endl;

static const wstring special_prefix = L"SpecialGroup_";
static const wstring group_postfix = L"group";

wstring getSpecialGroupKey(const Node* node)
{
    if (node->hasFlag(FlagOfflineGroup))
        return special_prefix + wstringToLower(node->name()) + group_postfix;
    else if (node->hasFlag(FlagFakeGroup))
        return special_prefix + L"fakeroot" + group_postfix;
    else
        return special_prefix + wstringToLower(node->name());
}

/**
 * Returns a string identifier based on all the network groups the given Contact Node
 * is in.
 */
wstring groupNames(const Node* n, const wstring& fakeRootName)
{
    wstring groupNames;
    Node* parent = n->parent();
    if (!parent)
        return groupNames;
    
    if (n->isLeaf())
        if (parent->hasFlag(FlagRootGroup) || 
            parent->hasFlag(FlagFakeGroup) ||
                // sort buddies in real groups named the same as the fake root group as if
                // they are actually in the fake root group
                (!fakeRootName.empty() && 
                 CaseInsensitiveEqual(fakeRootName, parent->name())))
            return fakeRootGroupKey();

    while (parent->parent()) {
        if (parent->data()) {
            Group* g = reinterpret_cast<Group*>(parent->data());
            if (!g->root() && parent->parent()) {
                if (!groupNames.empty())
                    groupNames = wstring(L"##") + groupNames;
                groupNames = wstringToLower(g->name()) + groupNames;
            }
        } else {
            return getSpecialGroupKey(parent);
        }
        parent = parent->parent();
    }

    return groupNames;
}

static const wstring groupCategory = L"__groups__";

/**
 * Sets category and key to the correct userOrder lookup values for the given Node.
 */
void userOrderInfo(const Node* node, const wstring& fakeRootName, wstring& category, wstring& key)
{
    Elem* elem = node->data();

    if (!elem) {
        // no elem means this is a "fake" Group created by one of the sorters
        key = getSpecialGroupKey(node);
        category = groupCategory;
    } else {
        if (Contact* contact = elem->asContact()) {
            category = groupNames(node, fakeRootName);
            key = contact->name();

            // HACK until buddy transition is complete
            if (key.substr(0, 13) != L"Metacontact #") {
                Account* account = contact->buddies()[0]->account();
                key = account->service() + L"/" + account->protocolUsername() + L"/" + key;
            }
        } else {
            Group* group = elem->asGroup();
            BL_ASSERT(group);
            if (node->hasFlag(FlagFakeGroup))
                key = getSpecialGroupKey(node);
            else if (!fakeRootName.empty() && CaseInsensitiveEqual(fakeRootName, group->name()))
                key = fakeRootGroupKey();
            else
                key = wstringToLower(group->name());
            
            category = groupCategory;
        }
    }
}

int Contacts::userOrder(const Node* node, const wstring& fakeRootName, const wstring& givenCategory)
{
    wstring category, key;
    int val = 0;
    // printf("userOrder(%ws) -> \n", node->repr().c_str());
    userOrderInfo(node, fakeRootName, category, key);
    wstring cat = givenCategory.empty() ? category : givenCategory;
    if (!cat.empty()) {
        val = m_order[cat].index(key);
        // printf(" (%ws, %ws) -> %d\n", cat.c_str(), key.c_str(), val);
    } else {
        // printf(" <<NONE>>\n");
    }
    
    return val;
}

Contacts::~Contacts()
{
    // delete all Accounts (must come before contact deletion,
    // buddies in these accounts will be deleted, removing them from the contacts)
    foreach (AccountMap::value_type a, m_accounts)
        delete a.second;

    // delete all Contacts
    foreach (ContactMap::value_type i, m_contacts)
        delete i.second;
}

void Contacts::removeAllContacts()
{
    foreach (ContactMap::value_type i, m_contacts) {
        Contact* contact = i.second;
        delete contact;
    }
    
    m_contacts.clear();
}

void Contacts::setDirty(bool dirty) {
    foreach (AccountMap::value_type a, m_accounts)
        a.second->setDirty(dirty);
}

wstring Contacts::contactReprs() const
{
    wostringstream s;
    foreach (ContactMap::value_type i, m_contacts) {
        Contact* contact = i.second;
        s << contact->name() << " (status=" << contact->status()
          << ", online=" << contact->online() << ")" << endl;

        foreach (Buddy* buddy, contact->buddies()) {
            s << "    " << buddy->name() << " (service="
              << buddy->service() << ", status=" << buddy->status()
              << ")" << endl;
        }
    }

    return s.str();
}

ElemOrderIndices::ElemOrderIndices()
    : m_nextIndex(0)
{} 

size_t ElemOrderIndices::index(const wstring& key)
{
    // already in the map?
    IndexMap::const_iterator i = m_indicesMap.find(key);
    if (i != m_indicesMap.end())
        return i->second;

    // else append to list and update indices map
    size_t idx = m_nextIndex++;
    m_indicesMap[key] = idx;
    return idx;
}

void ElemOrderIndices::_add(const wstring& key, size_t index)
{
    m_indicesMap[key] = index;
    m_nextIndex = index + 1;
}

struct OrderPairs //: public binary_function<const Pair&, const Pair&, bool>
{
	typedef std::pair<wstring, int> Pair;
    bool operator()(const Pair& a, const Pair& b) { return a.second < b.second; }
};

vector<wstring> ElemOrderIndices::values()
{
    typedef std::pair<wstring, int> Pair;



    // Get all items: (wstring, index)
    vector<Pair> items;
    foreach (Pair p, m_indicesMap)
        items.push_back(p);

    // Sort by index.
    std::sort(items.begin(), items.end(), OrderPairs());

    // Build list of just (wstring)
    vector<wstring> values;
    foreach (Pair p, items)
        values.push_back(p.first);

    return values;
}

