#include "precompiled.h"
#include "config.h"
#include "Contact.h"
#include "Status.h"

#include <sstream>
using std::wstringstream;

TRACK_ALLOC_IMPL(Contact);

void Contact::merge(const vector<Contact*> contacts)
{
    foreach (Contact* contact, contacts)
        foreach (Buddy* buddy, contact->buddies())
            ;

    BL_ASSERT(false);
}

// Returns the most available status in all of this Contact's Buddy objects
Buddy* Contact::mostAvailableBuddy() const
{
    BL_ASSERT(!m_buddies.empty());

    Buddy* mostAvailableBuddy = NULL;
    int highestStatusValue = -10000;

    foreach (Buddy* buddy, m_buddies) {
        wstring status = buddy->status();
        int value = numberForStatus(status);
        if (value > highestStatusValue) {
            highestStatusValue = value;
            mostAvailableBuddy = buddy;
        }
    }

    return mostAvailableBuddy;
}

wstring Contact::_mostAvailableStatus() const
{
    return mostAvailableBuddy()->status();
}

static wstring stripStatus(const wstring& status)
{
    return status;
}

bool Contact::_updateStatus(Buddy* source, const wstring& status)
{
    int i = compareStatuses(m_status, status);

    m_lastStatus = m_status;

    bool different = true;

    // if the new status is more available then our current, then just set our
    // status to it
    if (i < 0)
        m_status = status;
    else if (i != 0)
        // otherwise we have to compare
        m_status = _mostAvailableStatus();
    else
        different = false;

    if (m_lastStatus.empty())
        m_lastStatus = m_status;

    return different;
}

bool Contact::_updateAlias(Buddy* source, const wstring& alias)
{
    if (alias != m_alias) {
        setAlias(mostAvailableBuddy()->alias());
        return true;
    } else
        return false;
}

void Contact::setAlias(const wstring& alias)
{
    m_alias = alias;
}

bool Contact::_updateService(Buddy* source, const wstring& service)
{
    if (service != m_service) {
        m_service = mostAvailableBuddy()->service();
        return true;
    } else
        return false;
}

bool Contact::_updateMobile(Buddy* source, bool mobile)
{
    if (mobile != m_mobile) {
        m_mobile = mostAvailableBuddy()->mobile();
        return true;
    } else
        return false;
}

bool Contact::_updateLogSize(Buddy* source, unsigned long logSize)
{
	unsigned long total = 0;
	foreach(Buddy* b, buddies())
		total += b->logSize();
	bool different = total != m_logSize;
	m_logSize = total;
	return different;
}

bool Contact::_updateLeaving(Buddy* source, bool leaving)
{
    bool different = false;
    if (leaving) {
        different = !m_leaving;
        m_leaving = true;
    } else {
        bool oldLeaving = m_leaving;

        m_leaving = false;
        foreach (Buddy* b, buddies())
            if (b->leaving()) {
                m_leaving = true;
                break;
            }

        different = oldLeaving != m_leaving;
    }

    return different;
}

void Contact::_addBuddy(Buddy* buddy)
{
    if (std::find(m_buddies.begin(), m_buddies.end(), buddy) == m_buddies.end()) {
        m_buddies.push_back(buddy);

        _updateStatus(buddy, buddy->status());
        _updateAlias(buddy, buddy->alias());
        _updateService(buddy, buddy->service());
        _updateMobile(buddy, buddy->mobile());
        _updateLogSize(buddy, buddy->logSize());
        _updateLeaving(buddy, buddy->leaving());
    }
}

void Contact::_removeBuddy(Buddy* buddy, bool update)
{
    std::vector<Buddy *>::iterator i = std::find(m_buddies.begin(), m_buddies.end(), buddy);
    if (i != m_buddies.end()) {
        m_buddies.erase(i);
        
        if (update && m_buddies.size()) {
            Buddy* b = mostAvailableBuddy();
            _updateStatus(b, b->status());
            _updateAlias(b, b->alias());
            _updateService(b, b->service());
            _updateMobile(b, b->mobile());
            _updateLogSize(b, b->logSize());
            _updateLeaving(b, b->leaving()); // not correct: if all buddies are offline and any of them are leaving, we need to be leaving to. I think?
        }
    }
}
              
wstring Contact::repr() const
{
    wstringstream ss;
    ss << "Contact(" << m_alias << ")";
    return ss.str();
}

Contact::~Contact()
{
    foreach (Buddy* b, m_buddies)
        b->forgetContact();

    m_buddies.clear();

    TRACK_DEALLOC();
}

wstring Contact::attribute(SortBy attribute) const
{
    switch (attribute) {
        case UserOrdering: return L"";
        case Name: return name();
        case LogSize: return L"";
        case Service: return service();
        case Status: return status();
        case Alias: return alias();
        case CustomOrder: return L"";
        case Mobile: return mobile() ? L"1" : L"0";
        default:
            BL_ASSERT_NOT_REACHABLE(L"");
    }
}

static bool searchMatch(const wstring& s, const wstring& searchString)
{
    return wstringToLower(s).find(searchString) != std::string::npos;
}

bool Contact::search(const wstring& searchString) const
{
    if (searchMatch(alias(), searchString))
        return true;

    foreach(Buddy* b, m_buddies)
        if (searchMatch(b->name(), searchString))
            return true;
        else if (searchMatch(b->alias(), searchString))
            return true;
        else
            foreach (wstring s, b->extraSearchStrings())
                if (searchMatch(s, searchString))
                    return true;
    return false;
}
