#ifndef BuddyList_h
#define BuddyList_h

#include "BuddyListCommon.h"
#include "Account.h"

class BuddyList
{
public:
    AccountRef account(const wstring& service, const wstring& name)
    {
        wstring accountid(service + L"/" + name);
        
        AccountMap::const_iterator i = m_accountMap.find(accountid);

        AccountRef account;
        if (i == m_accountMap.end())
            account = AccountRef(new Account(service, name));
        else
            account = i->second;

        return account;
    }

protected:
    typedef hash_map<wstring, AccountRef> AccountMap;
    AccountMap m_accountMap;
};

static BuddyList gs_buddylist;

#endif
