#include "precompiled.h"
#include "config.h"
#include "Sorters.h"
#include "NodePrivate.h"
#include "Contact.h"
#include "StringUtils.h"
#include "Status.h"

#include <ostream>
#include <string>
using std::wostringstream;
using std::tolower;

#include <iostream>
using std::wcout;
using std::endl;

#define AS_CONTACT(node, name) \
    Contact* name = static_cast<Contact*>(node->data())

static wstring serverGroupPrefix = wstring(L"ServerGroup#");

wstring fakeRootGroupKey()
{
    return wstring(L"SpecialGroup_fakerootgroup");
}

/**
 * Returns the status for a Contact that Groupers should use.
 */
static wstring contactSortStatus(const Contact* c)
{
    if (c->leaving())
        // If a contact is currently "leaving," then sort by its
        // last known status. The effect here is to have a greyed out offline
        // buddy remain in its group temporarily for a few seconds before it
        // disappears.
        return c->lastStatus();
    else
        return c->status();
}

bool ByGroup::key(Node* parent, Node* child, BucketResult* result)
{
    if (!child->data()) return false;

    if (Group* g = child->data()->asGroup())
        result->key = serverGroupPrefix + child->data()->name();
    else
        return false;

    result->bucketFunc = bind(&ByGroup::bucket, this, _1, _2);
    return true;
}

Node* ByGroup::bucket(Node* elem, Node* parent)
{
    if (m_skipLevel > 1) {
        Node* parentChild = elem->nthParent(m_skipLevel - 1);
        if (parentChild && !parentChild->parent())
            elem->addFlags(FlagSkipGroup);
    }

    elem->setParent(parent);
    elem->addFlags(FlagUserGroup);
    if (!m_showGroups)
        elem->addFlags(FlagSkipGroup);

    return elem;
}

bool ByStatus::key(Node* parent, Node* child, BucketResult* result)
{
    // only group Contact objects
    if (!child->isLeaf()) return false;

    // don't make status groups inside status groups
    if (result->hasFlag(FlagStatusGroup)) return false;

    AS_CONTACT(child, c);

    wstring status(contactSortStatus(c));

    if (status == L"unknown")
        status = L"offline";

    result->key = status;
    result->bucketFunc = bind(&ByStatus::bucket, this, status, _1, _2);
    result->parentFlags |= FlagStatusGroup;
    return true;
}

Node* ByStatus::bucket(const wstring& status, Node* elem, Node* parent)
{
    Node* statusGroupNode = new Node(NULL, parent);

    statusGroupNode->setName(groupNameForStatus(status));
    statusGroupNode->addFlags(FlagStatusGroup);

    if (!m_showGroups)
        statusGroupNode->addFlags(FlagSkipGroup);

    // Add the "prune tree" flag if we're hiding offline buddies.
    if (!m_showOffline && status == L"offline")
        statusGroupNode->addFlags(FlagPruneTree);

    return statusGroupNode;
}

static const wstring onlineGroupPrefix = L"__online__";

bool ByOnline::key(Node* parent, Node* child, BucketResult* result)
{
    // only group Contact objects
    if (!child->isLeaf()) return false;

    // don't make status groups inside status groups
    if (result->hasFlag(FlagOfflineGroup)) return false;

    AS_CONTACT(child, c);

    wstring status(contactSortStatus(c));

    bool offline = false;
    if (status == L"offline" || status == L"unknown")
        offline = true;

    result->key = onlineGroupPrefix + (offline ? L"no" : L"yes");
    result->bucketFunc = bind(&ByOnline::bucket, this, offline, _1, _2);
    result->parentFlags |= FlagOfflineGroup;
    return true;
}

static const wstring mobileGroupPrefix = L"__mobile__";

bool ByMobile::key(Node* parent, Node* child, BucketResult* result)
{
    // only group Contact objects
    if (!child->isLeaf()) return false;

    // don't make mobile groups inside mobile groups
    if (result->hasFlag(FlagMobileGroup)) return false;

    AS_CONTACT(child, c);

    bool mobile = c->mobile();

    result->key = mobileGroupPrefix + (mobile ? L"no" : L"yes");
    result->bucketFunc = bind(&ByMobile::bucket, this, mobile, _1, _2);
    result->parentFlags |= FlagMobileGroup;
    return true;
}

Node* ByMobile::bucket(bool mobile, Node* elem, Node* parent)
{
    Node* groupNode = new Node(NULL, parent);
    groupNode->setName(mobile ? L"Mobile" : L"Not Mobile");
    groupNode->addFlags(FlagMobileGroup);
    if (mobile && !m_showMobile)
        groupNode->addFlags(FlagPruneTree);
    else
        groupNode->addFlags(FlagSkipGroup);
    return groupNode;
}

Node* ByOnline::bucket(bool offline, Node* elem, Node* parent)
{
    Node* groupNode = new Node(NULL, parent);
    groupNode->setName(offline ? L"Offline" : L"Online");
    //groupNode->addFlags(FlagStatusGroup);
    groupNode->addFlags(FlagOfflineGroup);

    if (!offline) {
        // always just make Online groups invisible
        groupNode->addFlags(FlagSkipGroup);
    } else {
        // Set a "high" customOrder so that Offline group always sorts last.
        groupNode->setCustomOrder(100);

        // The Node gets our own offline group comparator, so that it sorts
        // buddies alphabetically, no matter what your sorting options are.
        groupNode->setComparator(m_offlineCmp);

        // Otherwise, for Offline groups:
        if (m_groupOffline) {
            // If we're showing the offline group, then give it a flag
            // that the merging process will see and use to elevate it to
            // the root group.
            groupNode->addFlags(FlagGroupInRoot);
        } else {
            // Otherwise we're not collecting offline buddies into a group:
            if (m_showOffline)
                // ...but we're showing them. Make the group invisible.
                groupNode->addFlags(FlagSkipGroup);
        }

        if (!m_showOffline)
            // ...and we're not showing them. Prune all Offline groups entirely.
            groupNode->addFlags(FlagPruneTree);
    }

    return groupNode;
}

void ByService::setGroupName(const wstring& service, const wstring& name)
{
    m_groupNames[service] = name;
}

bool ByService::key(Node* parent, Node* child, BucketResult* result)
{
    // only group buddy objects
    if (!child->isLeaf()) return false;

    // don't make service groups inside service groups
    if (result->hasFlag(FlagServiceGroup)) return false;

    AS_CONTACT(child, c);

    result->key = c->service();
    result->bucketFunc = bind(&ByService::bucket, this, c->service(), _1, _2);
    result->parentFlags |= FlagServiceGroup;
    return true;
}

wstring ByService::_groupNameForService(const wstring& service)
{
    GroupNameMap::const_iterator i = m_groupNames.find(service);
    if (i != m_groupNames.end())
        return i->second;
    else
        return service;
}

Node* ByService::bucket(const wstring& service, Node* elem, Node* parent)
{
    Node* serviceGroupNode = new Node(NULL, parent);

    serviceGroupNode->setName(_groupNameForService(service));
    serviceGroupNode->addFlags(FlagServiceGroup);
    if (!m_showGroups)
        serviceGroupNode->addFlags(FlagSkipGroup);

    return serviceGroupNode;
}

static wstring fakeRootPrefix = wstring(L"FakeRootGroup#");

bool ByFakeRoot::key(Node* parent, Node* child, BucketResult* result)
{
    bool skip;
    // only group buddy objects
    if (!child->isLeaf()) return false;
    AS_CONTACT(child, c);

    if (!child->parent())
        return false;

    Node* grandparent = child->nthParent(2);
    if (!grandparent)
        return false;

    Node* ancestor = grandparent->parent();
    if (ancestor) {
        if (ancestor->parent()) {
            return false;
        } else if (!(child->parent()->hasFlag(FlagFakeGroup))) {
            return false;
        } else {
            result->key = serverGroupPrefix + m_fakeRootName;
            skip = false;
        }
    } else {
        result->key = fakeRootPrefix + m_fakeRootName;
        skip = true;
    }
    result->parentFlags |= FlagFakeGroup;
    result->bucketFunc = bind(&ByFakeRoot::bucket, this, skip, _1, _2);
    return true;
}

Node* ByFakeRoot::bucket(bool skip, Node* elem, Node* parent)
{
    Node* fakeRootGroup = new Node(NULL, parent);
    fakeRootGroup->setName(m_fakeRootName);
    if (skip) {
        fakeRootGroup->addFlags(FlagSkipGroup);
    }
    fakeRootGroup->addFlags(FlagFakeGroup);
    return fakeRootGroup;
}

bool BySearch::key(Node* parent, Node* child, BucketResult* result)
{
    if (!child->isLeaf() || result->hasFlag(FlagSearchGroup))
        return false;
    AS_CONTACT(child, c);

    wstring searchString;
    if (caseInsensitive())
        searchString = wstringToLower(m_searchString);
    else
        searchString = m_searchString;

    bool matches = c->search(searchString);

    if (matches)
        result->key = m_searchString + L" yes";
    else
        result->key = m_searchString + L" no";

    result->bucketFunc = bind(&BySearch::bucket, this, matches, _1, _2);
    result->parentFlags |= FlagSearchGroup;
    return true;
}

Node* BySearch::bucket(bool matches, Node* elem, Node* parent)
{
    Node* groupNode = new Node(NULL, parent);
    groupNode->setName(groupName());
    groupNode->addFlags(FlagSearchGroup);

    if (!matches)
        groupNode->addFlags(FlagPruneTree);
    else if (!groupContacts())
        groupNode->addFlags(FlagSkipGroup);

    return groupNode;
}

wstring Grouper::repr() const
{
    wostringstream os;
    os << L"Grouper(" << this << L")";
    return os.str();
}

wstring ByGroup::repr() const
{
    wostringstream os;
    os << L"ByGroup(showGroups=" << m_showGroups << L")";
    return os.str();
}

wstring ByStatus::repr() const
{
    wostringstream os;
    os << L"ByStatus(showGroups=" << m_showGroups << ", " <<
                    "showOffline=" << m_showOffline << L")";
    return os.str();
}

wstring ByOnline::repr() const
{
    wostringstream os;
    os << L"ByOnline(groupOffline=" << m_groupOffline << ", " <<
                    "showOffline=" << m_showOffline << L")";
    return os.str();
}

wstring ByMobile::repr() const
{
    wostringstream os;
    os << L"ByMobile(showMobile=" << m_showMobile << L")";
    return os.str();
}

wstring ByFakeRoot::repr() const
{
    wostringstream os;
    os << L"ByFakeRoot(" << m_fakeRootName << L")";
    return os.str();
}

wstring BySearch::repr() const
{
    wostringstream os;
    os << L"BySearch(" << m_searchString << L")";
    return os.str();
}

