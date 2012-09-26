#ifndef Buddy_h
#define Buddy_h

#include "BuddyListCommon.h"
#include "StringUtils.h"

#include <vector>
using std::vector;

/**
 * Represents one person you can communicate with on one IM account.
 */
class BL_EXPORT Buddy: public Elem
{
public:
    TRACK_ALLOC_CLASS(Buddy);

    Buddy(Contacts* contacts,
          const wstring& name, 
          Account* account,
          const wstring& service = L"");
    virtual ~Buddy();

    bool invalidate();

    bool valid()
    {
        return m_valid;
    }

    Group* asGroup() { return 0; }
    Buddy* asBuddy() { return this; }

    /**
     * Returns the buddy's name. Guaranteed to be unique in this Buddy's Account among
     * buddies of the same service.
     */
    wstring name() const { return m_name; }

    /**
     * Returns a nicely formatted version of this buddy's name.
     */
    wstring niceName() const { return m_niceName; }
    void setNiceName() const;

    /**
     * Returns this buddy's service. May be different than account()->service().
     * For example, an MSN buddy on a Yahoo list will have account()->service() 
     * == "yahoo" but service() == "msn".
     */
    wstring service() const { return m_service; }

    /**
     * Equivalent to this->account()->service().
     */
    wstring protocol() const;

    /**
     * A string representing the status of this Buddy.
     */
    wstring status() const { return m_status; }
    void setStatus(const wstring& status);

    /**
     * Returns true if this Buddy is on a mobile device.
     */
    bool mobile() const { return m_mobile; }
    void setMobile(bool mobile);

    /**
     * Returns the Account object this Buddy belongs to.
     */
    Account* account() const { return m_account; }

    /**
     * Returns this Buddy's alias.
     */
    wstring alias() const { return m_alias; }
    void setAlias(const wstring& alias);

    bool leaving() const { return m_leaving; }
    void setLeaving(bool leaving);

    /**
     * Returns the Contact that this Buddy belongs to.
     */
    Contact* contact(bool create=true);

	unsigned long logSize() const { return m_logSize; }
	void setLogSize(unsigned long logSize);

    void dump() const
    {
        printf("%ws", repr().c_str());
    }

    bool addServerGroup(const wstring& serverGroup)
    {
        wstring g(wstringToLower(serverGroup));

        if (!inServerGroup(g)) {
            m_serverGroups.push_back(g);
            return true;
        } else
            return false;
    }

    bool inServerGroup(const wstring& serverGroup, bool isLower = false)
    {
        wstring g = isLower ? serverGroup : wstringToLower(serverGroup);
        return m_serverGroups.end() !=
            find(m_serverGroups.begin(), m_serverGroups.end(), g);
    }

    /**
     * Causes this Buddy to lose its pointer to its Contact.
     */
    void forgetContact() { m_contact = 0; }

    wstring repr() const;

    bool dirty() { return m_dirty; }
    void setDirty(bool dirty) { m_dirty = dirty; }

    void addExtraSearchString(const wstring& s) { m_extraSearchStrings.push_back(s); }
    const vector<wstring>& extraSearchStrings() const { return m_extraSearchStrings; }

protected:
    wstring m_name;
    wstring m_niceName;

    wstring m_service;
	
	unsigned long m_logSize;

    wstring m_status;
    Account* m_account;
    Contact* m_contact;

    wstring m_alias;

	bool m_mobile:1;
    bool m_leaving:1;
    bool m_dirty:1;
    bool m_valid:1;

    vector<wstring> m_serverGroups;
    vector<wstring> m_extraSearchStrings;
};

#endif

