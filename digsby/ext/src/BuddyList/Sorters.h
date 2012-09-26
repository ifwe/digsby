#ifndef SORTERS_H_
#define SORTERS_H_

#include "Node.h"

#ifdef __GNUC__
#include <ext/hash_map>
#else
#include <hash_map>
#endif
using stdext::hash_map;

wstring BL_EXPORT fakeRootGroupKey();

/**
 * Base class for all Grouper objects, which do tree transformations on
 * Nodes.
 */
class BL_EXPORT Grouper
{
public:
    Grouper(int sortsByFlags, bool hasFakeRoot = false)
        : m_sortsByFlags(sortsByFlags)
        , m_hasFakeRoot(hasFakeRoot)
    {}

    virtual ~Grouper() {}

    virtual bool key(Node* parent,
                     Node* child,
                     BucketResult* result)
    {
        return false;
    }
    virtual wstring repr() const;

    void setSortsBy(int sortsBy) { m_sortsByFlags = sortsBy; }
    bool sortsBy(int sortsBy)
    {
        return (m_sortsByFlags & sortsBy) != 0;
    }

    int sortsByFlags() const { return m_sortsByFlags; }
    bool hasFakeRoot() const { return m_hasFakeRoot; }

private:
    int m_sortsByFlags;
    bool m_hasFakeRoot;
};

/**
 * Groups buddies by server group.
 **/
class BL_EXPORT ByGroup : public Grouper
{
public:
    ByGroup(bool showGroups = true, int skipLevel = -1)
        : m_showGroups(showGroups)
        , m_skipLevel(skipLevel)
        , Grouper(0)
    {}

    virtual bool key(Node* parent, Node* child, BucketResult* result);
    virtual wstring repr() const;

protected:
    Node* bucket(Node* elem, Node* parent);
    bool m_showGroups;
    char m_skipLevel;
};

/**
 * Groups buddies by status.
 */
class BL_EXPORT ByStatus : public Grouper
{
public:
    ByStatus(bool showGroups = true, bool showOffline = true)
        : m_showGroups(showGroups)
        , m_showOffline(showOffline)
        , Grouper(Status)
    {}

    virtual bool key(Node* parent, Node* child, BucketResult* result);
    virtual wstring repr() const;

protected:
    Node* bucket(const wstring& status, Node* elem, Node* parent);

private:
    bool m_showGroups;
    bool m_showOffline;
};

/**
 * Groups buddies by whether they are online or not.
 */
class BL_EXPORT ByOnline : public Grouper
{
public:
    ByOnline(bool groupOffline = true, bool showOffline = true)
        : m_groupOffline(groupOffline)
        , m_showOffline(showOffline)
        , Grouper(Status)
        , m_offlineCmp(new MultiComparator<const Node*>(Alias))
    {
        // When we're showing offline and grouping offline, then
        // that means that our custom m_offlineCmp will be given to 
        // the Offline group. This also means we need to report an extra
        // sortsBy flag: Alias.
        if (m_showOffline && m_groupOffline)
            setSortsBy(Status | Alias);
    }

    virtual ~ByOnline()
    {
        delete m_offlineCmp;
    }

    virtual bool key(Node* parent, Node* child, BucketResult* result);
    virtual wstring repr() const;

protected:
    Node* bucket(bool offline, Node* elem, Node* parent);

private:
    bool m_groupOffline;
    bool m_showOffline;
    ElemNodeComparator m_offlineCmp;
};

/**
 * Groups buddies by whether they are mobile or not.
 */
class BL_EXPORT ByMobile : public Grouper
{
public:
    ByMobile(bool showMobile = true)
        : m_showMobile(showMobile)
        , Grouper(Mobile)
    {}

    virtual ~ByMobile()
    {}

    virtual bool key(Node* parent, Node* child, BucketResult* result);
    virtual wstring repr() const;

protected:
    Node* bucket(bool mobile, Node* elem, Node* parent);

private:
    bool m_showMobile;
};

/**
 * Groups buddies by service.
 */
class BL_EXPORT ByService : public Grouper
{
public:
    ByService(bool showGroups = true)
        : m_showGroups(showGroups)
        , Grouper(Service)
    {}

    virtual bool key(Node* parent, Node* child, BucketResult* result);

    /**
     * Sets the "nice name" for a service grroup.
     */
    void setGroupName(const wstring& service, const wstring& name);

protected:
    /**
     * Returns a nice name for a service group, if one was set via setGroupName.
     */
    wstring _groupNameForService(const wstring& service);
    
    Node* bucket(const wstring& service, Node* elem, Node* parent);

    typedef hash_map<wstring, wstring> GroupNameMap;
    hash_map<wstring, wstring> m_groupNames;
    bool m_showGroups;
};

/**
 * Groups buddies by whether they are mobile or not.
 */
class BL_EXPORT ByFakeRoot : public Grouper
{
public:
    ByFakeRoot(const wstring& name) : Grouper(0, true)
        , m_fakeRootName(name)
    {}

    virtual ~ByFakeRoot()
    {}

    virtual bool key(Node* parent, Node* child, BucketResult* result);
    virtual wstring repr() const;

    wstring fakeRootName() const { return m_fakeRootName; }

protected:
    Node* bucket(bool skip, Node* elem, Node* parent);

private:
    wstring m_fakeRootName;
};

/**
 * Filter buddies by attribute (for example, when searching).
 */
class BL_EXPORT BySearch : public Grouper
{
public:
    BySearch(const wstring& searchString, const wstring& groupName = L"Contacts", int searchAttributes = AllSearchable)
        : Grouper(searchAttributes, false)
        , m_searchString(searchString)
        , m_caseInsensitive(true)
        , m_groupName(groupName)
        , m_groupContacts(true)
    {}

    bool caseInsensitive() const { return m_caseInsensitive; }
    void setCaseInsensitive(bool caseInsensitive) { m_caseInsensitive = caseInsensitive; }

    void setGroupContacts(bool groupContacts) { m_groupContacts = groupContacts; }
    bool groupContacts() const { return m_groupContacts; }

    wstring groupName() const { return m_groupName; }

    virtual ~BySearch() {}

    virtual bool key(Node* parent, Node* child, BucketResult* result);
    virtual wstring repr() const;

protected:
    Node* bucket(bool matches, Node* elem, Node* parent);
    wstring m_searchString;
    wstring m_groupName;

    bool m_caseInsensitive:1;
    bool m_groupContacts:1;
};
    
#endif

