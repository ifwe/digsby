#ifndef Group_h
#define Group_h

#include "BuddyListCommon.h"
#include "Buddy.h"
#include <string>
#include <vector>
using std::wstring;
using std::vector;

/**
 * A container for Contacts or other Groups
 */
class BL_EXPORT Group : public Elem
{
public:
    TRACK_ALLOC_CLASS(Group);

    Group(const wstring& name)
        : Elem(0)
        , m_root(false)
    {
        m_name = name;
        TRACK_ALLOC();
    }

    virtual ~Group();

    wstring name() const { return m_name; }

    void addChild(Elem* elem)
    {
        m_children.push_back(elem);
    }

    virtual Group* newGroup(const wstring& name)
    {
        return new Group(name);
    }

    Group* copy()
    {
        Group* group = newGroup(name());
        group->setDisplayString(displayString());
        group->setGroupKey(groupKey());
        if (userdata())
            group->setUserdata(userdata()->clone());
        group->setRoot(root());
        return group;
    }

    const vector<Elem*>& children() const { return m_children; }
    size_t numChildren() const { return m_children.size(); }

    Buddy* asBuddy() { return 0; }
    Group* asGroup() { return this; }

    void dump() const
    {
        printf("Group(%ws)", name().c_str());
    }

    wstring repr() const;

    wstring groupKey() const { return m_groupKey; }
    void setGroupKey(const wstring& groupKey) { m_groupKey = groupKey; } 

    wstring displayString() const { return m_displayString; }
    void setDisplayString(const wstring& displayString) { m_displayString = displayString; }

    void setRoot(bool root) { m_root = root; }
    bool root() const { return m_root; }

protected:
    wstring m_name;
    wstring m_groupKey;
    vector<Elem*> m_children;
    wstring m_displayString;

    bool m_root;
};

#endif

