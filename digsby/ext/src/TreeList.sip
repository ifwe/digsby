%Import Buddylist/sip/blist.sip

class TreeList : SkinVList
{
%TypeHeaderCode
#include "TreeList.h"
%End

private:
    TreeList(const TreeList&);

public:
    TreeList(wxWindow* parent, wxWindowID id = wxID_ANY, int style = wxLB_SINGLE) /Transfer/;
    virtual ~TreeList();

    void SetRoot(Elem* root);
    Elem* GetSelectedItem() const;
    Elem* GetItemAt(int i) const;
    Elem* GetParent(Elem* obj) const;
    int HitTestParent(const wxPoint& pos, float* percent);
};


