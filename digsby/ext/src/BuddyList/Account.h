#ifndef Account_h
#define Account_h

#include <string>
#include <map>
#ifdef __GNUC__
#include <ext/hash_map>
#else
#include <hash_map>
#endif
#include <vector>
using std::vector;
using std::wstring;
using std::map;

#include "GNUC.h"
using stdext::hash_map;

#include "BuddyListCommon.h"
#include "Buddy.h"

/**
 * Represents a connection to an IM server.
 *
 * Made unique by (service, name) where service is like "aim" and name is
 * the account's username.
 */
class BL_EXPORT Account
{
protected:
    typedef hash_map<wstring, Buddy*> BuddyMap;
    typedef BuddyMap::const_iterator BuddyMapIter;
    typedef hash_map<wstring, BuddyMap> ServiceBuddyMap;
    typedef ServiceBuddyMap::const_iterator ServiceBuddyMapIter;

public:
    Account(Contacts* contacts, wstring name, wstring service)
        : m_contacts(contacts)
        , m_name(name)
        , m_service(service)
        , m_valid(true)
    {
    }

    virtual ~Account();

    bool invalidate();

    bool valid()
    {
        return m_valid;
    }

    /**
     * The account's username.
     */
    wstring name() const { return m_name; }

    /**
     * The account's service, a lowercased simple name identifying the type of
     * IM account this is (i.e., L"aim").
     */
    wstring service() const { return m_service; }

    /**
     * Username harvested from buddy.protocol
     * Needed for user ordering later
     * Should probably be replaced with an algorithm which can derive it.
     */
    wstring protocolUsername() const { return m_protocolUsername; }

    void setProtocolUsername( const wstring& protocolUsername ) {
        m_protocolUsername = protocolUsername;
    }

    /**
     * Returns a Buddy* for a name, and optionally a service. (Some IM accounts
     * can have buddies on multiple services.)
     *
     * If service isn't specified, it is assumed you are looking for a buddy on
     * this IM account's service.
     */
    Buddy* buddy(const wstring& name, const wstring& service = L"")
    {
        wstring bService = service;

        if (bService.empty()) {
            // no service given? first search m_service, and then any service
            Buddy* b = _buddy_any_service(name);
            if (b) return b;

            bService = m_service;
        } else {
            ServiceBuddyMapIter j = m_buddies.find(bService);
            if (j != m_buddies.end()) {
                BuddyMapIter i = j->second.find(name);
                if (i != j->second.end())
                    return i->second;
            }
        }

        return _create_new_buddy(name, bService);
    }


    Buddy* _create_new_buddy(const wstring& name, const wstring& service)
    {
        return (m_buddies[service][name] = new Buddy(m_contacts, name, this, service));
    }

    Buddy* _buddy_any_service(const wstring name)
    {
        // first search m_service
        ServiceBuddyMapIter j = m_buddies.find(m_service);
        if (j != m_buddies.end()) {
            BuddyMapIter i = j->second.find(name);
            if (i != j->second.end())
                return i->second;
        }

        // now search other services
        for (ServiceBuddyMapIter i = m_buddies.begin(); i != m_buddies.end(); ++i) {
            if (i->first == m_service)
                continue;
            else {
                BuddyMapIter k = i->second.find(name);
                if (k != i->second.end())
                    return k->second;
            }
        }

        return 0;
    }

    void setDirty(bool dirty);

    ServiceBuddyMap buddies() { return m_buddies; }

protected:
    wstring m_name;
    wstring m_service;
    wstring m_protocolUsername;

    ServiceBuddyMap m_buddies;
    Contacts* m_contacts;
    bool m_valid;
};


#endif

