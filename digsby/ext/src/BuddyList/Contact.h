#ifndef Contact_h
#define Contact_h

#include "BuddyListCommon.h"
#include "Buddy.h"
#include "SortBy.h"

/**
 * Represents an identity across IM or other networks, and may point to
 * multiple Buddy objects.
 */
class BL_EXPORT Contact : public Elem, Searchable
{
public:
    TRACK_ALLOC_CLASS(Contact);

    Contact(Contacts* contacts, const wstring& name)
        : m_status(L"unknown")
        , m_name(name)
        , m_leaving(false)
        , Elem(contacts)
    {
        TRACK_ALLOC();
    }

    virtual ~Contact();

    /**
     * Used to maintain group counts, even with Contact merging.
     */
    virtual wstring hash()
    {
        return name() + L"$$$" + service();
    }

    /**
     * Returns a reference to this Contact's vector of Buddy objects.
     */
    vector<Buddy*>& buddies() { return m_buddies; }

    /**
     * Merges this Contact with the Contact objects specified in contacts.
     */
    void merge(const vector<Contact*> contacts);

    /**
     * Returns this Contact's alias, a user-customizable name.
     */
    wstring alias() const { return m_alias; }
    void setAlias(const wstring& alias);

    /**
     * This method returns the same value as alias().
     */
    wstring name() const { return m_name; }

    /**
     * Returns a plain text representation of this Contact's status.
     */
    wstring strippedStatus() const { return m_strippedStatus; }

    /**
     * Returns this Contact's most "available" Buddy object's status.
     */
    wstring status() const { return m_status; }

    /**
     * Returns this Contact's most "available" Buddy object's service.
     */
	wstring service() const { return m_service; }

    /**
     * Returns true if this Contact's most "available" Buddy object is mobile.
     */
	bool mobile() const { return m_mobile; }

    /**
     * Returns this Contact's log size, which is the total sum of Buddy log sizes.
     */
    unsigned long logSize() const { return m_logSize; }

    /**
     * Returns true if any Buddy objects this Contact points to are online.
     */
	bool online() const
    {
        return m_mobile || (status() != L"offline" && status() != L"unknown");
    }

    /**
     * Returns true if this contact is "leaving" to go offline.
     */
    bool leaving() const { return m_leaving; }

    wstring lastStatus() const { return m_lastStatus; }

    Contact* asContact() { return this; }

    wstring repr() const;

    /**
     * Returns this Contact's most available Buddy.
     */
    Buddy* mostAvailableBuddy() const;

    wstring attribute(SortBy attribute) const;

    virtual bool search(const wstring& searchString) const;

    // TODO: make this class a "friend" of Buddy?

    void _addBuddy(Buddy* buddy);
    void _removeBuddy(Buddy* buddy, bool update = true);
	
    bool _updateStatus(Buddy* src, const wstring& status);
    bool _updateAlias(Buddy* src, const wstring& alias);
	bool _updateService(Buddy* source, const wstring& service);
	bool _updateMobile(Buddy* source, bool mobile);
	bool _updateLogSize(Buddy* src, unsigned long logSize);
	bool _updateLeaving(Buddy* src, bool leaving);

    wstring _mostAvailableStatus() const;

protected:
    vector<Buddy*> m_buddies;
    wstring m_name;
    wstring m_status;
    wstring m_lastStatus;
    wstring m_strippedStatus;
    wstring m_alias;
	wstring m_service;
	bool m_mobile;
    bool m_leaving;
	unsigned long m_logSize;
};

#endif // Contact_h

