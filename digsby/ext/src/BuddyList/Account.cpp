#include "precompiled.h"
#include "config.h"
#include "Account.h"

Account::~Account()
{
    foreach (ServiceBuddyMap::value_type i, m_buddies)
        foreach (BuddyMap::value_type j, i.second)
            delete j.second;
}

bool Account::invalidate()
{
    foreach (ServiceBuddyMap::value_type i, m_buddies)
        foreach (BuddyMap::value_type j, i.second)
            j.second->invalidate();

    bool old = m_valid;
    m_valid = false;
    return old;
}

void Account::setDirty(bool dirty){
    foreach (ServiceBuddyMap::value_type i, buddies())
        foreach (Account::BuddyMap::value_type j, i.second)
            j.second->setDirty(dirty);
}