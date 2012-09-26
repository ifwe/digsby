#include "precompiled.h"
#include "config.h"
#include "Group.h"

#include <sstream>
using std::wstringstream;

TRACK_ALLOC_IMPL(Group);

wstring Group::repr() const
{
    wstringstream ss;
    ss << "Group(" << m_name << ")";
    return ss.str();
}

Group::~Group()
{
    for (vector<Elem*>::iterator i = m_children.begin(); i != m_children.end(); ++i)
        if (Group* g = (*i)->asGroup())
            delete g;

    TRACK_DEALLOC();
}

