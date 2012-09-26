//
// SkinVList is like wxVListBox but with smooth scrolling.
//
// Instead of storing list items itself, this class only asks elements to
// be drawn at a specified location. This allows the list to have an arbitrarily
// huge number of elements, or for the element data to be stored elsewhere, etc.
//
#include <wx/dcbuffer.h>
#include <wx/dc.h>
#include <wx/selstore.h>

#include "skinvlist.h"

#include <vector>
#include <cstdlib>
#include <iostream>
#include <stdio.h>

#include "pyutils.h"

#if WXPY
#include <sip.h>

// used to translate C++ objects -> python and vice versa
const sipAPIDef *get_sip_api()
{
    /* accessing the SIP API from other modules is not allowed except through
       the pointer obtained by this function */
    PyObject *sip_module;
    PyObject *sip_module_dict;
    PyObject *c_api;

    /* Import the SIP module. */
    sip_module = PyImport_ImportModule("sip");

    if (sip_module == NULL)
        return NULL;

    /* Get the module's dictionary. */
    sip_module_dict = PyModule_GetDict(sip_module);

    /* Get the "_C_API" attribute. */
    c_api = PyDict_GetItemString(sip_module_dict, "_C_API");

    if (c_api == NULL)
        return NULL;

    /* Sanity check that it is the right type. */
    if (!PyCObject_Check(c_api))
        return NULL;

    /* Get the actual pointer from the object. */
    return (const sipAPIDef *)PyCObject_AsVoidPtr(c_api);
}

#else
#include "wx/wxPython/wxPython.h"
#endif

#include "skinobjects.h"

#define DBG(_x) ((void) 0)
//#define DBG(_x) _x

// with DEBUG_REGIONS on, colored rectangles will be drawn in invalidated regions
// to show where the list is painting. for example, when scrolling down, only
// the bottom part of the list should become colored.
#define  DEBUG_REGIONS 0

using namespace std;

wxGraphicsContext* createGC(wxDC& dc)
{
    return wxGraphicsContext::Create((wxWindowDC&)dc);
}

IMPLEMENT_CLASS(SkinVList, SkinScrollWindow);

BEGIN_EVENT_TABLE(SkinVList, SkinScrollWindow)
    EVT_PAINT(SkinVList::OnPaint)
    EVT_ERASE_BACKGROUND(SkinVList::OnEraseBackground)
    EVT_SIZE(SkinVList::OnSize)
    EVT_LEFT_DOWN(SkinVList::OnLeftDown)
    EVT_LEFT_DCLICK(SkinVList::OnLeftDClick)
END_EVENT_TABLE()

SkinVList::SkinVList(wxWindow* parent, wxWindowID id, int style)
  : SkinScrollWindow(parent, id, style | wxWANTS_CHARS)
  , totalHeight(0)
  , firstVisible(0)
  , selStore(NULL)
  , background(NULL)
  , current(wxNOT_FOUND)
  , drawCallback(0)
  , paintCallback(0)
{
    SetBackgroundStyle(wxBG_STYLE_CUSTOM);

    if (style & wxLB_MULTIPLE)
        selStore = new wxSelectionStore();
}


SkinVList::~SkinVList()
{
    if (selStore)
        delete selStore;

    PY_BLOCK
    Py_CLEAR(drawCallback);
    Py_CLEAR(paintCallback);
    Py_CLEAR(background);
    PY_UNBLOCK
}

void SkinVList::SetSelection(int selection, bool keepVisible /* = true*/)
{
    if (HasMultipleSelection())
        // TODO: implement multiple selection
        assert(false);
    else
        DoSetCurrent(selection, keepVisible);
}

bool SkinVList::IsSelected(size_t row) const
{
    return selStore ? selStore->IsSelected(row) : (int)row == current;
}

bool SkinVList::DoSetCurrent(int i, bool keepVisible /* = true */)
{
    if (i == current)
        return false;
    else if (current != wxNOT_FOUND)
        RefreshLine(current);

    current = i;
    if (current > (int)heights.size()) {
        wxLogWarning(wxT("DoSetCurrent got %d but list is only %d elements long"), i, heights.size());
        current = wxNOT_FOUND;
    }

    if (current != wxNOT_FOUND) {
        if (keepVisible && !IsVisible(current)) {
            DBG(cout << "was not visible, scrolling to line " << current << endl);
            ScrollToLine(current);
        } else
            RefreshLine(current);
    }

    DBG(cout << "selection changed: " << current << endl);
    return true;
}

wxRect SkinVList::GetItemRect(size_t i) const {
    wxASSERT_MSG(i >= 0 && i < heights.size(), wxT("invalid index"));

    int y2     = heightSums[i];
    int height = heights[i];

    return wxRect(0, y2 - height, GetClientRect().width, height);
}

wxCoord SkinVList::OnGetLineHeight(size_t n) const
{
    return n < heights.size() ? heights[n] : 0;
}

int SkinVList::GetItemY(size_t i) const
{
    return i < heights.size() ? (heightSums[i] - heights[i] - GetScrollPos(wxVERTICAL)) : 0;
}

bool SkinVList::IsVisible(size_t i) const
{
    return i < heights.size() && GetViewRect().Contains(GetItemRect(i));
}

void SkinVList::OnHandleScroll(wxScrollWinEvent& e)
{
    SkinScrollWindow::OnHandleScroll(e);
    CalcVisible();
}

size_t SkinVList::GetLastVisibleLine() const
{
    int y = GetClientRect().GetBottom() + GetViewStart();
    size_t len = heightSums.size();

    if (!len) {
        DBG(cout << "GetLastVisibleLine(1) -> " << firstVisible << endl);
        return firstVisible;
    }

    size_t i = firstVisible;
    while (i < len && (int)heightSums[i] < y)
        ++i;

    DBG(cout << "GetLastVisibleLine(2) -> " << i-1 << endl);
    return i;
}

void SkinVList::RefreshLine(size_t row)
{
  if (row < heights.size()) {
      wxRect rect(GetClientRect());
      rect.height = heights[row];
      rect.y = heightSums[row] - rect.height;

      rect.Offset(0, -GetViewStart());

      RefreshRect(rect);
  }
}

void SkinVList::RefreshLines(size_t a, size_t b)
{
    if (b < a) {
        size_t temp = a;
        a = b;
        b = temp;
    }

    wxRect refreshRect;
    wxRect crect(GetClientRect());
    int viewStart = GetViewStart();

    for (size_t i = a; i <= b; ++i) {
        wxRect rect(crect);
        rect.height = heights[i];
        rect.y = heightSums[i] - rect.height - viewStart;
        refreshRect.Union(rect);
    }

    RefreshRect(refreshRect);
}

// sets "firstVisible" to the index of the first row that is at least partially
// visible
void SkinVList::CalcVisible()
{
    unsigned int vy = max(0, GetViewStart());

    // TODO: this is a dumb algorithm for finding the first row visible.
    // a bisection algorithm would perform much better for large lists.

    DBG(cout << "CalcVisible" << endl);

    if (firstVisible > heightSums.size() - 1)
        firstVisible = heightSums.size() - 1;

    if (!heightSums.size())  {
      return;

    } else if (firstVisible > 0 && vy < heightSums[firstVisible-1]) {
        DBG(cout << " going up" << endl);
        while (--firstVisible > 0)
            if (firstVisible == 0 || heightSums[firstVisible-1] <= vy)
                break;

    } else if (heightSums.size() > firstVisible && heightSums[firstVisible] < vy) {
        DBG(cout << " going down" << endl);
        while (++firstVisible < heightSums.size())
            if (heightSums.size() > firstVisible  && heightSums[firstVisible] >= vy)
                break;
    }

  DBG(cout << "  firstVisible: " << firstVisible << endl);


}

inline ostream& operator<< (ostream& o, const wxRect& r)
{
    o << "wxRect(" << r.x << ", " << r.y << ", " << r.width << ", " << r.height << ")";
    return o;
}

// sets the background for the list, drawn behind all elements
void SkinVList::SetBackground(PyObject* background)
{
    PY_BLOCK
    Py_XDECREF(this->background);
    Py_XINCREF(background);
    this->background = background;

    DBG(cout << "SkinVList::SetBackground:" << endl);
    DBG(PyObject_Print(background, stdout, 0));

    // If the background object has a ".ytile" attribute that evaluates
    // to false, then it is assumed that it does not "tile" in the Y direction,
    // and that we cannot scroll vertically just by blitting unchanged pixels
    // (this is called physical scrolling here).
    //
    // With .ytile = false we have to repaint the background with every update.
    bool physical = true;
    if (background) {
        DBG(cout << "physical scrolling is ");
        PyObject* ytileobj = PyObject_GetAttrString(background, "ytile");

        if (ytileobj) {
            physical = 0 != PyObject_IsTrue(ytileobj);
            DBG(cout << physical << endl);
            Py_DECREF(ytileobj);
        } else
            PyErr_Clear(); // no .ytile attribute is OK
    }

    EnablePhysicalScrolling(physical);
    PY_UNBLOCK
}

PyObject* SkinVList::GetBackground() const
{
    return background;
}

int SkinVList::HitTest(const wxPoint& pt) const
{
    return HitTest(pt.x, pt.y);
}

int SkinVList::HitTest(wxCoord x, wxCoord y) const
{
    float percent;
    return HitTestEx(x, y, &percent);
}

// Returns the row the mouse is over, or wxNOT_FOUND. Also sets the value of
// percent to be the percentage down in the row the mouse is.
int SkinVList::HitTestEx(wxCoord x, wxCoord y, float* percent) const
{
    if (!GetClientRect().Contains(x, y))
        return wxNOT_FOUND;

    // offset by view position
    y += GetViewStart();

    // find the first visible item whose lower boundary is beneath the mouse click
    for (unsigned int n = firstVisible; n < heights.size(); ++n) {
        if (y < (int)heightSums[n]) {
            float height = (float)heights[n];
            if (height)
                *percent = float(y - (n > 0 ? heightSums[n-1] : 0)) / height;
            else
                *percent = 0.0f;

            DBG(cout << "percent: " << *percent << endl);
            return n;
        }
    }

    return wxNOT_FOUND;
}

#if WXPY
static sipAPIDef* sip = NULL;
static bool sip_initialized = false;
static bool sip_found_classes = false;

static const sipTypeDef* sipType_wxAutoBufferedPaintDC;
static const sipTypeDef* sipType_wxRect;
static const sipTypeDef* sipType_wxString;

static bool sip_init()
{
    if (sip_found_classes)
        return true;

    if (!sip_initialized) {
        sip_initialized = true;
        sip = (sipAPIDef*)get_sip_api();
        if (sip == NULL) {
            PyErr_SetString(PyExc_AssertionError, "could not obtain SIP api pointer");
            PyErr_Print();
            return false;
        }

        sipType_wxAutoBufferedPaintDC = sip->api_find_type("wxAutoBufferedPaintDC");
        sipType_wxRect = sip->api_find_type("wxRect");
        sipType_wxString = sip->api_find_type("wxString");
    }

    if (!sip || !sipType_wxAutoBufferedPaintDC || !sipType_wxRect || !sipType_wxString) {
        PyErr_SetString(PyExc_AssertionError, "could not find SIP types");
        PyErr_Print();
        return false;
    }

    sip_found_classes = true;
    return true;
}
#endif

static void PySkinDraw(PyObject* bg, wxDC& dc, const wxRect& rect)
{
    PY_BLOCK
#if WXPY
    if (!sip_init())
        return;

    PyObject* pydc   = sip->api_convert_from_type((void*)&dc, sipType_wxAutoBufferedPaintDC, NULL);
    PyObject* pyrect = sip->api_convert_from_type((void*)&rect, sipType_wxRect, NULL);
#else
    PyObject* pydc   = wxPyConstructObject((void*)&dc,   wxT("wxAutoBufferedPaintDC"),    false);
    PyObject* pyrect = wxPyConstructObject((void*)&rect, wxT("wxRect"),  false);
#endif //WXPY
    PyObject* pyn    = PyInt_FromLong(0);

    if ( !pydc )
        cout << "error: DC was null" << endl;
    else if ( !pyrect )
        cout << "error: rect was null" << endl;
    else if ( !pyn )
        cout << "error: n was null" << endl;
    else if ( !bg )
        cout << "error: bg was null" << endl;
    else {
        DBG(PyObject_Print(pydc, stdout, 0); cout << endl);
        DBG(PyObject_Print(pyrect, stdout, 0); cout << endl);
        DBG(PyObject_Print(pyn, stdout, 0); cout << endl);

#if WXPY
        const wxString drawStr_wx(wxT("Draw"));
        PyObject* DrawStr = sip->api_convert_from_type((void*)&drawStr_wx, sipType_wxString, NULL);
#else
        PyObject* DrawStr = wx2PyString(wxT("Draw"));
#endif
        PyObject* drawMethod = PyObject_GetAttr(bg, DrawStr);

        if (drawMethod) {
            if (PyCallable_Check(drawMethod)) {
                PyObject* result = PyObject_CallFunctionObjArgs(drawMethod, pydc, pyrect, pyn, NULL);
                Py_XDECREF(result);
            } else
                cout << "background.Draw is not callable" << endl;
        } else
            cout << "background has no Draw attribute" << endl;

        Py_XDECREF(drawMethod);
        Py_DECREF(DrawStr);

        if (PyErr_Occurred())
            PyErr_Print();
    }

    Py_XDECREF(pydc);
    Py_XDECREF(pyrect);
    Py_XDECREF(pyn);

    PY_UNBLOCK
}

void SkinVList::OnPaint(wxPaintEvent&)
{
    wxAutoBufferedPaintDC dc(this);
    PrepareDC(dc);

    int vy = GetViewStart();
    wxRect crect(GetClientRect());
    wxRegion updateRegion(GetUpdateRegion());
    wxRect updateBox;

    if (!updateRegion.IsOk()) {
        wxLogWarning(wxT("SkinVList::OnPaint -- invalid update region"));
        updateBox = wxRect(GetVirtualSize());
    } else {
        updateRegion.Offset(0, vy);
        updateBox = updateRegion.GetBox();
    }

    crect.Offset(0, vy);

    if (background)
        PySkinDraw(background, dc, crect);
    else {
        dc.SetBrush(*wxWHITE_BRUSH);
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.DrawRectangle(crect);
    }

#if DEBUG_REGIONS
#define RR rand() * 255 / RAND_MAX
    dc.SetBrush(wxBrush(wxColor(RR, RR, RR, 128)));
    dc.SetPen(*wxTRANSPARENT_PEN);
    dc.DrawRectangle(updateBox);
    // DBG(fprintf(stdout, "updateBox(%d %d %d %d)\n", updateBox.x, updateBox.y, updateBox.width, updateBox.height));
#endif

    wxRect rect(0, 0, crect.width, 0);

    int lastVisiblePixel = min(updateBox.GetBottom(), crect.GetBottom());

    for (size_t n = firstVisible; n < heights.size(); ++n) {
        rect.y      = heightSums[n] - heights[n];
        rect.height = heights[n];

        if (rect.y + rect.height >= updateBox.GetTop()) {
            // call virtual subclass method to draw each individual item
            wxRect drawRect(rect);
            OnDrawItem(dc, drawRect, n);
        }

        if (rect.GetBottom() > lastVisiblePixel)
            break;
    }

    if (paintCallback) {
        PY_BLOCK
#if WXPY
        if(!sip_init()) return;
        PyObject* pydc = sip->api_convert_from_type((void*)&dc, sipType_wxAutoBufferedPaintDC, NULL);
#else
        PyObject* pydc   = wxPyConstructObject((void*)&dc,   wxT("wxAutoBufferedPaintDC"),    false);
#endif

        if (pydc) {
            PyObject* result = PyObject_CallFunctionObjArgs(paintCallback, pydc, NULL);
            Py_XDECREF(result);
            Py_DECREF(pydc);
        }
        PY_UNBLOCK
    }
}

void SkinVList::DoHandleItemClick(int item, int)
{
    // has anything worth telling the client code about happened?
    bool notify = false;

    // in any case the item should become the current one
    if (DoSetCurrent(item) && !HasMultipleSelection())
        notify = true; // this has also changed the selection for single selection case

    // notify the user about the selection change
    if (notify)
        SendSelectedEvent();

    // else: nothing changed at all
}

void SkinVList::SetDrawCallback(PyObject* drawCallback)
{
    PY_BLOCK
    if (PyCallable_Check(drawCallback)) {
        Py_XDECREF(this->drawCallback);
        Py_INCREF(drawCallback);
        this->drawCallback = drawCallback;
    } else {
        PyErr_SetString(PyExc_TypeError, "SetDrawCallback takes a callable argument");
    }
    PY_UNBLOCK
}

void SkinVList::SetPaintCallback(PyObject* paintCallback)
{
    PY_BLOCK
    if (PyCallable_Check(paintCallback)) {
        Py_XDECREF(this->paintCallback);
        Py_INCREF(paintCallback);
        this->paintCallback = paintCallback;
    } else {
        PyErr_SetString(PyExc_TypeError, "SetPaintCallback takes a callable argument");
    }
    PY_UNBLOCK
}

void SkinVList::OnLeftDown(wxMouseEvent& event)
{
    SetFocus();

    int item = HitTest(event.GetPosition());

    if (item != wxNOT_FOUND) {
        DBG(cout << "Clicked on item " << item << endl);

        int flags = 0;
        if (event.ShiftDown())
           flags |= ItemClick_Shift;

        // under Mac Apple-click is used in the same way as Ctrl-click
        // elsewhere
#ifdef __WXMAC__
        if (event.MetaDown())
#else
        if (event.ControlDown())
#endif
            flags |= ItemClick_Ctrl;

        DoHandleItemClick(item, flags);
    }
}

void SkinVList::SendSelectedEvent()
{
    wxASSERT_MSG( current != wxNOT_FOUND,
                  _T("SendSelectedEvent() shouldn't be called") );

    wxCommandEvent event(wxEVT_COMMAND_LISTBOX_SELECTED, GetId());
    event.SetEventObject(this);
    event.SetInt(current);

    (void)GetEventHandler()->ProcessEvent(event);
}

bool SkinVList::SetHeights(const std::vector<unsigned int>& newHeights)
{
    if (!wxIsMainThread()) {
        wxLogError(wxT("SkinVList::SetHeights called from the wrong thread"));
        return false;
    }

    heights = newHeights;
    heightSums.clear();
    heightSums.reserve(heights.size());

    //
    // "heightSums" is a parallel list containing the y position of the bottom of each element
    //
    unsigned int total = 0;
    for (size_t i = 0; i < heights.size(); ++i) {
        total += heights[i];
        heightSums.push_back(total);
    }

    totalHeight = total;
    UpdateVirtualSize();

    if (heightSums.size() != heights.size())
        wxLogWarning(wxT("heightSums and heights have different sizes"));

    return true;
}


void SkinVList::OnEraseBackground(wxEraseEvent& WXUNUSED(event))
{
    // do nothing.
}

void SkinVList::OnSize(wxSizeEvent& event)
{
    event.Skip();
    UpdateVirtualSize();
}

void SkinVList::UpdateVirtualSize()
{
    SetVirtualSize(GetClientSize().GetWidth(), totalHeight);
    CalcVisible();
}

void SkinVList::OnLeftDClick(wxMouseEvent& eventMouse)
{
    int item = HitTest(eventMouse.GetPosition());
    if (item != wxNOT_FOUND) {
        // if item double-clicked was not yet selected, then treat
        // this event as a left-click instead
        if (item == current) {
            wxCommandEvent event(wxEVT_COMMAND_LISTBOX_DOUBLECLICKED, GetId());
            event.SetEventObject(this);
            event.SetInt(item);

            DBG(cout << "DOUBLE CLICK" << item);
            (void)GetEventHandler()->ProcessEvent(event);
        } else
            OnLeftDown(eventMouse);
    }
}

void SkinVList::OnDrawItem(wxDC& dc, const wxRect& rect, int n)
{
    if ( !drawCallback ) {
        // TODO: raise an exception here.
        cout << "error: no drawCallback given to SkinVList" << endl;
        return;
    }

    PY_BLOCK
#if WXPY
    if (!sip_init())
        return;
#endif

    DBG(PyObject_Print(drawCallback, stdout, 0));

    // OnDrawItem(wxDC, wxRect, n)
#if WXPY
    PyObject* pydc   = sip->api_convert_from_type((void*)&dc,   sipType_wxAutoBufferedPaintDC, NULL);
    PyObject* pyrect = sip->api_convert_from_type((void*)&rect, sipType_wxRect, NULL);
#else
    PyObject* pydc   = wxPyConstructObject((void*)&dc,   wxT("wxAutoBufferedPaintDC"),    false);
    PyObject* pyrect = wxPyConstructObject((void*)&rect, wxT("wxRect"), false);
#endif //WXPY
    PyObject* pyn    = PyInt_FromLong(n);

    // pack into an args tuple
    PyObject* argtuple = PyTuple_Pack(3, pydc, pyrect, pyn);

    // invoke the callable
    PyObject* result = PyObject_CallObject(drawCallback, argtuple);

    if (PyErr_Occurred()) // print (and clear) any exceptions
        PyErr_Print();

    // clean up references.
    Py_XDECREF(pydc);
    Py_XDECREF(pyrect);
    Py_XDECREF(pyn);
    Py_XDECREF(argtuple);
    Py_XDECREF(result);

    PY_UNBLOCK
    return;
}

PyObject* SkinVList::GetDrawCallback() const
{
    return drawCallback;
}


bool SkinVList::ScrollToLine(size_t line)
{
    if (line >= heights.size() || line >= heightSums.size()) {
        wxLogWarning(wxT("ScrollToLine got invalid line %d"), line);
        return false;
    }

    wxRect view(GetViewRect());

    int y2 = heightSums[line];
    int itemHeight = heights[line];
    int y1 = y2 - itemHeight;

    if (y1 < view.GetTop())		  // the item is above the current scroll position
        Scroll(-1, y1);
    else if (y2 > view.GetBottom()) // the item is beneath the current scroll position
        Scroll(-1, y1 - (view.GetHeight() - itemHeight));
    else
        return false;

    CalcVisible();
    RefreshLine(line);
    return true;
}
