#ifndef _CGUI_BUDDYLIST_H_
#define _CGUI_BUDDYLIST_H_

#include "TreeList.h"

class BuddyList : public TreeList
{
public:
    BuddyList(wxWindow* parent);
    virtual ~BuddyList();

    void foo();
};

#endif // _CGUI_BUDDYLIST_H_

