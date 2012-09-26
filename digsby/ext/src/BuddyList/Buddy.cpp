#include "precompiled.h"
#include "config.h"

#include "Buddy.h"
#include "Account.h"
#include "Contact.h"
#include "BuddyListSorter.h"

#include <sstream>
using std::wstringstream;

TRACK_ALLOC_IMPL(Buddy);

Buddy::Buddy(Contacts* contacts,
             const wstring& name, 
             Account* account,
             const wstring& service)
    : Elem(contacts)
    , m_name(name)
    , m_alias(name)
	, m_mobile(false)
    , m_niceName(name)
    , m_status(L"unknown")
    , m_account(account)
    , m_contact(NULL)
	, m_logSize(0)
    , m_dirty(true)
    , m_leaving(false)
    , m_valid(true)
{
    m_service = (!service.empty() ? service : this->account()->service());

	Contact* c = contact();
	c->_updateService(this, m_service);
	c->_updateStatus(this, m_status);
	c->_updateLogSize(this, m_logSize);	
    
    TRACK_ALLOC();
}

wstring Buddy::protocol() const
{
    return m_account->service();
}

void Buddy::setStatus(const wstring& status)
{
    m_status = status;
    contact()->_updateStatus(this, status);
}

void Buddy::setMobile(bool mobile)
{
    m_mobile = mobile;
    contact()->_updateMobile(this, mobile);
}

void Buddy::setLogSize(unsigned long logSize)
{
	m_logSize = logSize;
	contact()->_updateLogSize(this, logSize);
}

void Buddy::setAlias(const wstring& alias)
{
    m_alias = alias;
    contact()->_updateAlias(this, alias);
}

void Buddy::setLeaving(bool leaving)
{
    m_leaving = leaving;
    contact()->_updateLeaving(this, leaving);
}

wstring Buddy::repr() const
{
    wstringstream ss;
    ss << "Buddy(" << m_name << " " << m_service << ")";
    return ss.str();
}

Contact* Buddy::contact(bool create)
{
    if (!m_contact)
        m_contact = contacts()->forBuddy(this, create);

    return m_contact;
}

Buddy::~Buddy()
{
    invalidate(); // removes this from Contact's buddy list
    TRACK_DEALLOC();
}

bool Buddy::invalidate()
{
    bool old = m_valid;
    m_valid = false;

    contact(false); // sets m_contact

    if (m_contact) {
        m_contact->_removeBuddy(this);
        m_contact = 0;
    }

    return old;
}
