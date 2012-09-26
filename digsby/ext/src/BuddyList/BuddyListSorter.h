#ifndef BuddyListSorter_h
#define BuddyListSorter_h

#include "BuddyListCommon.h"
#include "Node.h"
#include "Account.h"
#include "Contact.h"
#include "Group.h"
#include "BuddyChange.h"

#include <vector>
using std::vector;
using std::pair;

#ifdef __GNUC__
#include <ext/hash_map>
#else
#include <hash_map>
#endif
using stdext::hash_map;

BL_EXPORT wstring getSpecialGroupKey(const Node* node);

/**
 * A utility class used by Contacts to store user order efficiently.
 */
class BL_EXPORT ElemOrderIndices
{
public:
    ElemOrderIndices();

    typedef hash_map<wstring, int> IndexMap;

    /**
     * Returns a numerical "user order" index for the given Contact.
     */
    size_t index(const wstring& key);
    void _add(const wstring& key, size_t index);

    /**
     * Builds a list of values, in order.
     */
    vector<wstring> values();

protected:
    IndexMap m_indicesMap;
    int m_nextIndex;
};

typedef hash_map<wstring, ElemOrderIndices> ElemOrdering;

/**
 * A single source for retreiving Account, Buddy, and Contact objects.
 *
 * Also stores local data, including user order.
 */
class BL_EXPORT Contacts
{
private:
    Contacts(const Contacts&);
    Contacts& operator= (const Contacts&);

protected:
    typedef pair<wstring, wstring> AccountMapKey;
    typedef map<AccountMapKey, Account*> AccountMap;

    AccountMap m_accounts;

    typedef hash_map<wstring, Contact*> ContactMap;
    ContactMap m_contacts;

    // { group_names: {contact_name: index}}
    ElemOrdering m_order;

public:
    Contacts() 
    {
    }

    virtual ~Contacts();

    wstring contactReprs() const;

    /**
     * Sets the user ordering map used to lookup the Node userOrder() property.
     */
    void setOrdering(const ElemOrdering& ordering)
    {
        m_order = ordering;
    }

    ElemOrdering& ordering() { return m_order; }

    /**
     * Returns the user order index for a Node.
     */
    int userOrder(const Node* node,
                  const wstring& fakeRootName = L"",
                  const wstring& givenCategory = L"");


    /**
     * Finds the correct Contact object for a given Buddy.
     */
    Contact* forBuddy(Buddy* buddy, bool create = true)
    {
        wstring name = buddy->name();
        wstring contactKey;
        if (name.substr(0, 13) == L"Metacontact #")
            contactKey = name;
        else {
            Account* account = buddy->account();
            contactKey = wstring(L"Contact_") + 
                account->service() + L"_" + account->name() + L"_" +
                buddy->service() + L"_" + buddy->name();
        }

        ContactMap::const_iterator i = m_contacts.find(contactKey);

        Contact* contact = 0;
        if (i != m_contacts.end())
            contact = i->second;
        else if (create)
            contact = m_contacts[contactKey] = new Contact(this, name);

        if (contact)
            contact->_addBuddy(buddy);
        return contact;
    }

    void setDirty(bool dirty);

    /**
     * Returns a pointer to the AccountMap used to store Accounts.
     */
    AccountMap* accounts() { return &m_accounts; }

    /**
     * Returns an Account* for a username and service.
     *
     * The same Account object will be returned each time you ask for the same
     * name/service pair.
     */
    Account* account(const wstring name, const wstring service)
    {
        AccountMapKey key(name, service);
        AccountMap::const_iterator i = m_accounts.find(key);

        if (i != m_accounts.end())
            if (i->second->valid()){
                return i->second;
            } else {
                delete i->second;
                m_accounts.erase(i->first);
            }

        Account* account = new Account(this, name, service);
        m_accounts[key] = account;
        return account;
    }

    bool removeAccount(const wstring& name, const wstring service)
    {
        AccountMapKey key(name, service);
        AccountMap::const_iterator i = m_accounts.find(key);
        if (i != m_accounts.end()) {
            i->second->invalidate();
            return true;
        }
        return false;
    }

    bool removeContact(const wstring& contactId)
    {
        ContactMap::const_iterator i = m_contacts.find(contactId);

        if (i != m_contacts.end()) {
            Contact* contact = i->second;
            m_contacts.erase(i->first);
            delete contact;

            return true;
        }

        return false;
    }

    void removeAllContacts();
};

/**
 * Sorts and groups Contacts and Groups, and handles changes to element states efficiently
 * by doing near the least amount of work possible to apply a "delta" to the tree.
 *
 * To accomplish this, BuddyListSorter keeps references to the Elem* data you give it.
 */
class BL_EXPORT BuddyListSorter
{
public:
    BuddyListSorter();
    ~BuddyListSorter();

	/**
	 * Returns true if this sorter uses any of the attributes specified in
	 * sortFlags to arrange elements.
	 */
	bool sortsBy(int sortFlags) const { return (m_sortsByFlags & sortFlags) != 0; }

    /**
     * Returns a Node* pointing to the root of this BuddyListSorter's tree.
     */
    Node* root() const { return m_root; }

    /**
     * Returns the comparator that should be used to sort children of the
     * given Node. If no Node is given, this sorter's default comparator is
     * used.
     */
    ElemNodeComparator listCompare(Node* node = 0) const
    {
        if (node && node->comparator())
            return node->comparator();
        return m_cmp;
    }

    /**
     * Sets the comparators used for ordering elements.
     */
    void setComparators(const vector<SortBy>& cmps);

    /**
     * Give this sorter a new root Elem.
     */
    void setRoot(Elem* rootElem);

    /**
     * Returns a merged copy of the tree.
     *
     * The caller owns the Node* tree returned by this function.
     */
    Node* gather();

    /**
     * Gets an Account object for a name and service.
     */
    Account* account(const wstring& name, const wstring& service)
    {
        return m_contacts->account(name, service);
    }

    bool removeAccount(const wstring& name, const wstring& service)
    {
        return m_contacts->removeAccount(name, service);
    }

    bool removeContact(const wstring& contactId)
    {
        return m_contacts->removeContact(contactId);
    }

    /**
     * While contacts are still split between C/Python, this is a way for
     * Python to invalidate everything the sorter thinks about Metacontacts;
     * for example, when new metacontact data comes in from the network.
     */
    void removeAllContacts()
    {
        return m_contacts->removeAllContacts();
    }

    /**
     * Delegates to Contacts::userOrder to find the user order index for a Node.
     */
    int userOrder(const Node* node)
    {
        return m_contacts->userOrder(node);
    }

    wstring contactReprs() const
    {
        return m_contacts->contactReprs();
    }

    void buddyChanged(const wstring& accountService,
                      const wstring& accountName,
                      const wstring& buddyName,
                      const wstring& buddyService,
                      unsigned int change)
    {
    }

    /**
     * Sets the element ordering dictionary used to order Nodes by their
     * userOrder() property.
     */
    void setOrdering(const ElemOrdering& ordering)
    {
        m_contacts->setOrdering(ordering);
    }

    ElemOrdering& ordering() { return m_contacts->ordering(); }

	/**
	 * Takes ownership of grouper.
	 */
	void addSorter(Grouper* grouper);

    /**
     * Removes all groupers.
     */
    void clearSorters();

    /**
     * Deletes all Nodes.
     */
    void clearNodes();

    //
    // hackish buddylist specific stuff that we should genericize:
    //

    /**
     * Returns true if empty container Nodes will be pruned.
     */
    bool pruneEmpty() const { return m_pruneEmpty; }

    /**
     * Sets whether or not to prune empty container Nodes.
     */
    void setPruneEmpty(bool pruneEmpty) { m_pruneEmpty = pruneEmpty; }

    bool hasFakeRoot() const { return m_hasFakeRoot; }
    wstring fakeRootName() const { return m_fakeRootName; }

    //
    // Internal sorting functions
    //
    Node* toNode(Elem* elem, Node* parent = 0);
    void insort(Node* node, Node* child, int parentFlags = 0);
    bool key(Node* node, Node* child, BucketResult* result);
    Node* _findParent(Node* realparent, Node* child);
    void _merge(const Node::Vector& mergeNodes, Node* realparent);
    void _merge_children(const Node::Vector& nodes, Node* realparent, bool firstIsCopy = false);
    void _descendMerge(Node* node);
    void _sorted_merge(const Node::VecIter& begin, const Node::VecIter& end);
    void _finalPrune(Node* node);

    void _mergeInsert(Node* parent, Node* child, ElemNodeComparator cmp);
    void _sortedInsert(Node* parent, Node* child, ElemNodeComparator cmp);

    void updateUserOrder(Node* n);

protected:
    /**
     * Returns true if the given node should be "skipped" -- meaning its
     * children are merged one level up in the merge process.
     */
    bool shouldSkipNode(Node* node);

    /**
     * Returns true if the given node should be pruned entirely from the merged
     * tree.
     */
    bool shouldPruneNode(Node* node, int pass = 1);

    bool shouldMergeNodes(const Node::VecIter& i,
                          const Node::VecIter& begin,
                          const Node::VecIter& end,
                          Node*);


    /**
     * This specific bit of functionality should be customizable, but currently it means
     * that duplicate Contact objects in the same group should be merged.
     */
    bool shouldMergeLeaves(Node* a, Node* b);

    /**
     * Internal method that updates the m_sortsByFlags variable used by sortsBy.
     */
    void _updateSortsBy();

    ElemNodeComparator m_cmp;
    Node* m_root;
    Elem* m_rootElem;
    vector<Grouper*> m_groupers;
    Contacts* m_contacts;
    wstring m_fakeRootName;
    int m_sortsByFlags;
    bool m_pruneEmpty:1;
    bool m_hasFakeRoot:1;
};

#endif
