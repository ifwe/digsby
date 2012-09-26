
%{
#include "wx/wxPython/wxPython.h"
#include "wx/wxPython/pyclasses.h"
#include "wx/wxPython/pyistream.h"

#include <wx/dcbuffer.h>
#include <wx/metafile.h>
#include <wx/colour.h>
#include <wx/vlbox.h>

#include "skinbrush.h"
#include "skinvlist.h"
%}

%import typemaps.i
%import my_typemaps.i

%import core.i
%import windows.i
%import misc.i
%import _dc.i
%import _colour.i
%import _vscroll.i
%import skinbrush.i


%pythoncode { wx = wx._core }
%pythoncode { __docfilter__ = wx.__DocFilter(globals()) }

%{
#include <wx/vlbox.h>
%}

namespace std {
	%template(UintList) vector<unsigned int>;
}

// First, the C++ version
%{
class SkinVListBox  : public wxVListBox
{
    DECLARE_ABSTRACT_CLASS(SkinVListBox)
public:
    SkinVListBox() : wxVListBox() {}

    SkinVListBox(wxWindow *parent,
                 wxWindowID id = wxID_ANY,
                 const wxPoint& pos = wxDefaultPosition,
                 const wxSize& size = wxDefaultSize,
                 long style = 0)
        : wxVListBox(parent, id, pos, size, style)
    {}

    // Overridable virtuals

    // the derived class must implement this function to actually draw the item
    // with the given index on the provided DC
    // virtual void OnDrawItem(wxDC& dc, const wxRect& rect, size_t n) const = 0;
    DEC_PYCALLBACK__DCRECTSIZET_constpure(OnDrawItem);


    // the derived class must implement this method to return the height of the
    // specified item
    // virtual wxCoord OnMeasureItem(size_t n) const = 0;
    DEC_PYCALLBACK_COORD_SIZET_constpure(OnMeasureItem);


    // this method may be used to draw separators between the lines; note that
    // the rectangle may be modified, typically to deflate it a bit before
    // passing to OnDrawItem()
    //
    // the base class version doesn't do anything
    //    virtual void OnDrawSeparator(wxDC& dc, wxRect& rect, size_t n) const;
    DEC_PYCALLBACK__DCRECTSIZET2_const(OnDrawSeparator);


    // this method is used to draw the items background and, maybe, a border
    // around it
    //
    // the base class version implements a reasonable default behaviour which
    // consists in drawing the selected item with the standard background
    // colour and drawing a border around the item if it is either selected or
    // current
    //     virtual void OnDrawBackground(wxDC& dc, const wxRect& rect, size_t n) const;
    DEC_PYCALLBACK__DCRECTSIZET_const(OnDrawBackground);


    PYPRIVATE;
};

IMPLEMENT_ABSTRACT_CLASS(wxPyVListBox, wxVListBox);

IMP_PYCALLBACK__DCRECTSIZET_constpure(PySkinVListBox, SkinVListBox, OnDrawItem);
IMP_PYCALLBACK_COORD_SIZET_constpure (PySkinVListBox, SkinVListBox, OnMeasureItem);
IMP_PYCALLBACK__DCRECTSIZET2_const   (PySkinVListBox, SkinVListBox, OnDrawSeparator);
IMP_PYCALLBACK__DCRECTSIZET_const    (PySkinVListBox, SkinVListBox, OnDrawBackground);

%}



// Now define this class for SWIG

/*
    This class has two main differences from a regular listbox: it can have an
    arbitrarily huge number of items because it doesn't store them itself but
    uses OnDrawItem() callback to draw them and its items can have variable
    height as determined by OnMeasureItem().

    It emits the same events as wxListBox and the same event macros may be used
    with it.
 */
//MustHaveApp(wxPyVListBox);

//%rename(SkinVListBox) PySkinVListBox;


class PySkinVListBox : public wxPyVListBox
{
public:
    PySkinVListBox(wxWindow *parent,
                   wxWindowID id = wxID_ANY,
                   const wxPoint& pos = wxDefaultPosition,
                   const wxSize& size = wxDefaultSize,
                   long style = 0);                 

//    %RenameCtor(PreVListBox,  wxPyVListBox());

    void _setCallbackInfo(PyObject* self, PyObject* _class);

    bool Create(wxWindow *parent,
                wxWindowID id = wxID_ANY,
                const wxPoint& pos = wxDefaultPosition,
                const wxSize& size = wxDefaultSize,
                long style = 0);                

    // get the number of items in the control
    size_t GetItemCount() const;

    // does this control use multiple selection?
    bool HasMultipleSelection() const;

    // get the currently selected item or wxNOT_FOUND if there is no selection
    //
    // this method is only valid for the single selection listboxes
    int GetSelection() const;

    // is this item the current one?
    bool IsCurrent(size_t item) const;

    // is this item selected?
    bool IsSelected(size_t item) const;

    // get the number of the selected items (maybe 0)
    //
    // this method is valid for both single and multi selection listboxes
    size_t GetSelectedCount() const;

    // get the margins around each item
    wxPoint GetMargins() const;

    // get the background colour of selected cells
    const wxColour& GetSelectionBackground() const;


    // set the number of items to be shown in the control
    //
    // this is just a synonym for wxVScrolledWindow::SetLineCount()
    void SetItemCount(size_t count);

    // delete all items from the control
    void Clear();

    // set the selection to the specified item, if it is wxNOT_FOUND the
    // selection is unset
    //
    // this function is only valid for the single selection listboxes
    void SetSelection(int selection);

    // selects or deselects the specified item which must be valid (i.e. not
    // equal to wxNOT_FOUND)
    //
    // return True if the items selection status has changed or False
    // otherwise
    //
    // this function is only valid for the multiple selection listboxes
    bool Select(size_t item, bool select = true);

    // selects the items in the specified range whose end points may be given
    // in any order
    //
    // return True if any items selection status has changed, False otherwise
    //
    // this function is only valid for the single selection listboxes
    bool SelectRange(size_t from, size_t to);

    // toggle the selection of the specified item (must be valid)
    //
    // this function is only valid for the multiple selection listboxes
    void Toggle(size_t item);

    // select all items in the listbox
    //
    // the return code indicates if any items were affected by this operation
    // (True) or if nothing has changed (False)
    bool SelectAll();

    // unselect all items in the listbox
    //
    // the return code has the same meaning as for SelectAll()
    bool DeselectAll();

    // set the margins: horizontal margin is the distance between the window
    // border and the item contents while vertical margin is half of the
    // distance between items
    //
    // by default both margins are 0
    void SetMargins(const wxPoint& pt);
    %Rename(SetMarginsXY, void, SetMargins(wxCoord x, wxCoord y));

    // change the background colour of the selected cells
    void SetSelectionBackground(const wxColour& col);

    virtual void OnDrawSeparator(wxDC& dc, wxRect& rect, size_t n) const;
    virtual void OnDrawBackground(wxDC& dc, const wxRect& rect, size_t n) const;

    %property(FirstSelected, GetFirstSelected, doc="See `GetFirstSelected`");
    %property(ItemCount, GetItemCount, SetItemCount, doc="See `GetItemCount` and `SetItemCount`");
    %property(Margins, GetMargins, SetMargins, doc="See `GetMargins` and `SetMargins`");
    %property(SelectedCount, GetSelectedCount, doc="See `GetSelectedCount`");
    %property(Selection, GetSelection, SetSelection, doc="See `GetSelection` and `SetSelection`");
    %property(SelectionBackground, GetSelectionBackground, SetSelectionBackground, doc="See `GetSelectionBackground` and `SetSelectionBackground`");
};
