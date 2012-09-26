/**
  skinvlist.h

  Like wxVListBox, but smooth scrolling.
*/
#ifndef _SKINVLIST_H_
#define _SKINVLIST_H_

#include "wx/wxprec.h"
#ifndef WX_PRECOMP
#include "wx/wx.h"
#include "wx/graphics.h"
#endif

class wxSelectionStore;

#include "ScrollWindow.h"
#include "Python.h"

#include <vector>

class SkinRegion;

wxGraphicsContext* createGC(wxDC& dc);


class SkinVList : public SkinScrollWindow {
public:

#if SWIG
    %pythonAppend SkinVList "self._setOORInfo(self)"
#endif
  SkinVList(wxWindow* parent, wxWindowID id = wxID_ANY, int style = wxLB_SINGLE);

#ifndef SWIG
  virtual ~SkinVList();
#endif

  bool SetHeights(const std::vector<unsigned int>& newHeights);

  int  HitTest(wxCoord x, wxCoord y) const;
  int  HitTest(const wxPoint& pt) const;

#if SWIG
  %apply float *OUTPUT { float *percent }; //  make percent in HitTextEx an extra function output
#endif
  int  HitTestEx(wxCoord x, wxCoord y, float* percent) const;

  bool ScrollToLine(size_t line);

  void RefreshLine(size_t line);
  void RefreshLines(size_t a, size_t b);
  void RefreshAll() { Refresh(); }

  size_t GetRowCount() const { return heights.size(); }
  size_t GetItemCount() const { return heights.size(); }

  void SetSelection(int selection, bool keepVisible = true);
  bool HasMultipleSelection() const { return selStore != NULL; }
    int  GetSelection() const
    {
        wxASSERT_MSG( !HasMultipleSelection(), _T("GetSelection() can't be used with wxLB_MULTIPLE") );
        return current;
    }
  bool IsSelected(size_t row) const;


  size_t GetFirstVisibleLine() const { return firstVisible; }
  size_t GetLastVisibleLine() const;
  bool   IsVisible(size_t i) const;
    wxRect GetItemRect(size_t i) const;
    int    GetItemY(size_t i) const;


  //void SetBackground(SkinRegion* background);
  void SetBackground(PyObject* background);
  PyObject* GetBackground() const;
#ifdef SWIG
  %property(Background, GetBackground, SetBackground);
#endif

  void OnDrawItem(wxDC& dc, const wxRect& rect, int n);
  void SetDrawCallback(PyObject* drawCallback);
  void SetPaintCallback(PyObject* paintCallback);
  PyObject* GetDrawCallback() const;

#ifndef SWIG
protected:
    std::vector<unsigned int> heights, heightSums;
    unsigned int totalHeight;

    PyObject* background;
    PyObject* drawCallback;
    PyObject* paintCallback;

    void CalcVisible();

    bool DoSetCurrent(int i, bool keepVisible = true);
    void DoHandleItemClick(int item, int flags);
    void SendSelectedEvent();
    void UpdateVirtualSize();

    void OnHandleScroll(wxScrollWinEvent& event);

    size_t firstVisible, lastVisible;
    int    current;
    wxSelectionStore* selStore;

    // event handlers
    void OnPaint(wxPaintEvent&);
    void OnEraseBackground(wxEraseEvent&);
    void OnSize(wxSizeEvent&);
    void OnLeftDown(wxMouseEvent&);
    void OnKeyDown(wxKeyEvent& event);
    void OnLeftDClick(wxMouseEvent& eventMouse);

    virtual wxCoord OnGetLineHeight(size_t n) const;

    enum
    {
        ItemClick_Shift = 1, // item shift-clicked
        ItemClick_Ctrl  = 2, // ctrl
        ItemClick_Kbd   = 4  // item selected from keyboard
    };

    DECLARE_CLASS(SkinVList)
    DECLARE_EVENT_TABLE()
#endif
};

#endif
