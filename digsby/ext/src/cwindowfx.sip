%ModuleHeaderCode
#include <wx/window.h>
#include <wx/timer.h>
#include <wx/panel.h>
#include <wx/frame.h>
#include <wx/image.h>
#include <wx/bitmap.h>

#include "cwindowfx.h"
%End

bool IsMainThread();
bool isWin7OrHigher();
void redirectStderr(const wxString& filename);
void printToStderr(const wxString& s);
void FitInMonitors(wxWindow* window, const wxPoint& defaultPosition = wxDefaultPosition);
void SetFrameIcon(wxTopLevelWindow* win, const wxImage& image);
void SetBold(wxWindow* window, bool bold = true);

class SimplePanel : wxPanel
{
public:
    SimplePanel(wxWindow* parent /TransferThis/, int style = wxTAB_TRAVERSAL);
    //void OnEraseBackground(wxEraseEvent& e);
    virtual ~SimplePanel();
};

class NotifyWindow : wxFrame
{
public:
    NotifyWindow(wxWindow* window /TransferThis/, int id, const wxString& title, long style = wxFRAME_NO_TASKBAR | wxSTAY_ON_TOP | wxFRAME_SHAPED | wxNO_BORDER);
    virtual ~NotifyWindow();
    virtual bool Show(bool show = true);
    void SetRect(const wxRect& rect);
};

class Fader : wxTimer
{
public:
    Fader(wxTopLevelWindow* window, int fromAlpha = 255, int toAlpha = 0, unsigned int step = 8, SIP_PYCALLABLE onDone = NULL);
    virtual ~Fader();
    virtual void Notify();
    void Stop(bool runStopCallback = true);


// let the GC know about onDoneCallback
%GCClearCode
    Py_CLEAR(sipCpp->onDoneCallback);
    sipRes = 0;
%End

%GCTraverseCode
    PyObject *obj = sipCpp->onDoneCallback;
    sipRes = obj ? sipVisit(obj, sipArg) : 0;
%End

};

int GetTransparent(wxTopLevelWindow* tlw);

Fader* fadein(wxTopLevelWindow* window, int fromAlpha = 1,   int toAlpha = 255, unsigned int step = 8, SIP_PYCALLABLE onDone = NULL)
    /Factory/;
Fader* fadeout(wxTopLevelWindow* window, int fromAlpha = 255, int toAlpha = 0,   unsigned int step = 8, SIP_PYCALLABLE onDone = NULL)
    /Factory/;

void setalpha(wxTopLevelWindow* window, int alpha);

void Bitmap_Draw(const wxBitmap& bitmap, wxDC& dc, const wxRect& rect, int alignment = 0);

int getCacheKey(wxBitmap* bitmap);
int getCacheKey(wxImage* image);

wxRect RectClamp(const wxRect& self, const wxRect& r, int flags = wxALL);
wxPoint RectClampPoint(const wxRect& self, const wxPoint& pt, int flags = wxALL);

bool WindowVisible(wxTopLevelWindow* window);

wxBitmap* getScreenBitmap(const wxRect& rect);


wxRect GetTrayRect();

%If (WXMSW)
bool GetTaskBarAutoHide();
wxRect GetTaskbarRect();
wxRect GetNormalRect(wxTopLevelWindow* win);
SIP_PYOBJECT PyGetFontUnicodeRanges(const wxFont& font);
void ApplySmokeAndMirrors(wxWindow* win, const wxBitmap& shape, int ox = 0, int oy = 0);
void ApplySmokeAndMirrors(wxWindow* win, const wxRegion& shape);
void ApplySmokeAndMirrors(wxWindow* win, long shape = 0);
%End

bool LeftDown();
wxWindow* FindTopLevelWindow(wxWindow* window);

void Premultiply(wxBitmap& bmp);
void Unpremultiply(wxBitmap& bitmap);

/*
struct AnimationFrame
{
    AnimationFrame(const wxBitmap bitmap, float duration);
    wxBitmap m_bitmap;
    float m_duration;
};

typedef std::vector<AnimationFrame> AnimationFrameVector;

class Animation : wxWindow
{
private:
    Animation(const Animation&);
public:
    Animation(wxWindow* parent, int id = wxID_ANY, const AnimationFrameVector& frames, bool repeating);
    ~Animation();

    void SetFrames(const AnimationFrameVector& frames, bool repeating);
    wxBitmap GetFrameBitmap(size_t frameIndex) const;
    float GetFrameDuration(size_t frameIndex) const;
    size_t GetCurrentFrame() const;
};


*/
