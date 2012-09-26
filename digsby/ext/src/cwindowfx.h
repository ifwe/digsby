//
// cwindowfx.h
//

#ifndef _CWINDOWFX_H_
#define _CWINDOWFX_H_

#include <wx/window.h>
#include <wx/timer.h>
#include <wx/panel.h>
#include <wx/frame.h>
#include <wx/image.h>
#include <wx/bitmap.h>
#include <vector>
#include "Python.h"

bool IsMainThread();
void redirectStderr(const wxString& filename);
void printToStderr(const wxString& s);
void FitInMonitors(wxWindow* window, const wxPoint& defaultPosition = wxDefaultPosition);
wxIconBundle createIconBundle(const wxBitmap& bitmap);
wxIconBundle createIconBundle(const wxImage& image);
void SetFrameIcon(wxTopLevelWindow* win, const wxImage& image);

// font utility functions
void ModifyFont(wxWindow* ctrl, int weight = -1, int pointSize = -1, const wxString& faceName = wxEmptyString, int underline = -1);
wxFont ModifiedFont(const wxFont& font_, int weight = -1, int pointSize = -1, const wxString& faceName = wxEmptyString, int underline = -1);
void SetBold(wxWindow* window, bool bold = true);

/**
 * A panel that disables painting of the background.
 */
class SimplePanel : public wxPanel
{
public:
#if SWIG
    %pythonAppend SimplePanel "self._setOORInfo(self)"
#endif
    SimplePanel(wxWindow* parent, int style = wxTAB_TRAVERSAL);
    void OnEraseBackground(wxEraseEvent& e);
    virtual ~SimplePanel();
#ifndef SWIG
private:
    DECLARE_EVENT_TABLE()
#endif
};

/**
 * A borderless frame whose show method doesn't steal focus.
 */
class NotifyWindow : public wxFrame
{
public:
#if SWIG
    %pythonAppend NotifyWindow "self._setOORInfo(self)"
#endif
    NotifyWindow(wxWindow* window, int id, const wxString& title, long style = wxFRAME_NO_TASKBAR | wxSTAY_ON_TOP | wxFRAME_SHAPED | wxNO_BORDER);
    virtual ~NotifyWindow();
    virtual bool Show(bool show = true);
    void SetRect(const wxRect& rect);
};

class Fader : public wxTimer
{
public:
    Fader(wxTopLevelWindow* window, int fromAlpha = 255, int toAlpha = 0, unsigned int step = 8, PyObject* onDone = NULL);
    virtual ~Fader();
    virtual void Notify();
    void Stop(bool runStopCallback = true);
    PyObject* onDoneCallback;

protected:
    void OnWindowDestroyed(wxWindowDestroyEvent& e);
    
    wxTopLevelWindow* window;
    int to;
    int value;
    int step;
};

#ifdef SWIG
%newobject fadein;
%newobject fadeout;
#endif

int GetTransparent(wxTopLevelWindow* tlw);

Fader* fadein(wxTopLevelWindow* window,  int fromAlpha = 1,   int toAlpha = 255, unsigned int step = 8, PyObject* onDone = NULL);
Fader* fadeout(wxTopLevelWindow* window, int fromAlpha = 255, int toAlpha = 0,   unsigned int step = 8, PyObject* onDone = NULL);

void setalpha(wxTopLevelWindow* window, int alpha);

void Bitmap_Draw(const wxBitmap& bitmap, wxDC& dc, const wxRect& rect, int alignment = 0);

int getCacheKey(wxBitmap* bitmap);
int getCacheKey(wxImage* image);

wxRect RectClamp(const wxRect& self, const wxRect& r, int flags = wxALL);
wxPoint RectClampPoint(const wxRect& self, const wxPoint& pt, int flags = wxALL);

/**
 * Returns true if a top level window is shown, not minimized, and not obscured
 * by any other top level window (including windows from other applications).
 */
bool WindowVisible(wxTopLevelWindow* window);

/**
 * Returns a wxBitmap containing the entire display area.
 */
wxBitmap* getScreenBitmap(const wxRect& rect);

/**
 * Returns a wxRect with screen coordinates for the taskbar.
 */
wxRect GetTaskbarRect();

/**
 * Returns a wxRect with screen coordinates for the system tray area.
 */
wxRect GetTrayRect();

/**
 * Returns whether the Win version is 7 or higher, false on non-Win platforms.
 */
bool isWin7OrHigher();

/**
 * Returns whether the Win version is Vista or higher, false on non-Win platforms.
 */
bool isVistaOrHigher();

#ifdef __WXMSW__
/**
 * Returns true if the taskbar is set to autohide.
 */
bool GetTaskBarAutoHide();

/**
 * Returns the normal size a window would be (even if it's maximized).
 */
wxRect GetNormalRect(wxTopLevelWindow* win);

/**
   Returns a series of Unicode code point ranges for the given font.

   Return value is a Python list with [(start, len), (start, len), ...]
   */
PyObject* PyGetFontUnicodeRanges(const wxFont& font);

void ApplySmokeAndMirrors(wxWindow* win, const wxBitmap& shape, int ox = 0, int oy = 0);
void ApplySmokeAndMirrors(wxWindow* win, const wxRegion& shape);
void ApplySmokeAndMirrors(wxWindow* win, long shape = 0);


#endif // __WXMSW__

bool LeftDown();
wxWindow* FindTopLevelWindow(wxWindow* window);

void Premultiply(wxBitmap& bmp);
void Unpremultiply(wxBitmap& bitmap);

PyObject* RectPos(const wxRect& rect, const wxPoint& point);

/*
struct AnimationFrame
{
    AnimationFrame(const wxBitmap bitmap, float duration)
        : m_bitmap(bitmap)
        , m_duration(duration)
    {}
    
    wxBitmap m_bitmap;
    float m_duration;
};

typedef std::vector<AnimationFrame> AnimationFrameVector;

class Animation;

class AnimationTimer : public wxTimer
{
public:
    AnimationTimer(Animation* anim)
        : animation(anim)
    {}
    
    ~AnimationTimer()
    {
        animation = 0;
    }
        
    virtual void Notify();
   
protected:
    Animation* animation;
};

class Animation : public wxWindow
{
public:
    Animation();
    Animation(wxWindow* parent, int id = wxID_ANY, const AnimationFrameVector& frames, bool repeating);    
    ~Animation();
    void SetFrames(const AnimationFrameVector& frames, bool repeating);
    
    wxBitmap GetFrameBitmap(size_t frameIndex) const
    {
        wxASSERT(frameIndex < frames.size());
        return frames[frameIndex].m_bitmap;
    }
    
    float GetFrameDuration(size_t frameIndex) const
    {
        wxASSERT(frameIndex < frames.size());
        return frames[frameIndex].m_duration;
    }
    
    size_t GetCurrentFrame() const
    {        
        return currentFrame;
    }
    
    void OnTimer();
    
protected:   
    void OnPaint(wxPaintEvent& e);
    void NextFrame();
    void CalcMinSize();
    
#ifndef SWIG
    DECLARE_EVENT_TABLE()
    DECLARE_DYNAMIC_CLASS(Animation)
#endif

    AnimationFrameVector frames;
    AnimationTimer* timer;
    size_t currentFrame;
    bool playing;
    bool repeating;
};



*/
#endif // _CWINDOWFX_H_
