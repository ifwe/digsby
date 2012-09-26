#ifndef BuddyListCommon_h
#define BuddyListCommon_h

#include "config.h"
#include <string>
using std::wstring;

class Buddy;
class Group;
class Account;
class Contact;
class BuddyListSorter;
class Contacts;

/**
 * Users of Elem may subclass this to store arbitrary data in Elem via setUserdata.
 */
class ElemUserData
{
public:
    ElemUserData() {}
    virtual ElemUserData* clone() = 0;
    virtual ~ElemUserData() {}
};

/**
 * Base class for all objects that are sorted.
 */
class BL_EXPORT Elem
{
public:
    Elem(Contacts* contacts)
        : m_userdata(0)
        , m_contacts(contacts)
    {}

    virtual ~Elem()
    {
        if (m_userdata) {
            delete m_userdata;
            m_userdata = 0;
        }
    }

    virtual void merge(Elem* other)
    {
        // overridable by subclasses
    }

    virtual std::wstring hash() { return L""; }

    virtual std::wstring name() const = 0;
    virtual void dump() const
    {
        printf("%ws", repr().c_str());
    }

    virtual std::wstring repr() const = 0;

    virtual Group* asGroup() { return 0; };
    virtual Buddy* asBuddy() { return 0; };
    virtual Contact* asContact() { return 0; };

    Contacts* contacts() const { return m_contacts; }

    /**
     * Returns the userdata pointer for this Elem object. Initially NULL.
     */
    ElemUserData* userdata() const { return m_userdata; }
    
    /**
     * Set a custom userdata pointer in this Elem object.
     *
     * Elem takes ownership of userdata and will delete it when it is destroyed.
     * If an old userdata is being replaced, it will be destroyed immediately.
     */
    void setUserdata(ElemUserData* userdata)
    {
        ElemUserData* oldUserdata = m_userdata;
        m_userdata = userdata;

        if (oldUserdata && userdata != oldUserdata)
            delete oldUserdata;
    }

protected:
    ElemUserData* m_userdata;
    Contacts* m_contacts;
};

class Searchable
{
public:
    virtual bool search(const wstring& searchString) const = 0;
};

#endif

