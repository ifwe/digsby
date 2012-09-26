%ModuleHeaderCode
#include "alphaborder.h"
%End

typedef std::vector<int> FrameSize;

class AlphaBorder : wxFrame
{
public:
%ConvertToSubClassCode
wxClassInfo* c = sipCpp->GetClassInfo();
if(0) {}
#define C(clz) else if (c == CLASSINFO(clz)) { sipClass = sipClass_ ## clz; }
    C(AlphaBorder)
else
    sipClass = NULL;
#undef C
%End

    AlphaBorder(wxWindow* parent, SplitImage4* border, const FrameSize& frameSize, int style = 0) /Transfer/;
    virtual ~AlphaBorder();

    void SetBackground(SplitImage4* background /TransferBack/);
    void UpdatePosition(const wxRect& r);
    void PaintAlphaBackground();

    wxRect GetClipRect() const;

    void SetFrameSize(const FrameSize& frameSize);
    void SetFrameSize(int left, int top, int right, int bottom);
    void SetAlpha(unsigned char alpha, bool refresh = false);

    int m_alpha;
    int left;
    int top;
    int right;
    int bottom;
};

class BorderedFrame : wxFrame
{
public:
%ConvertToSubClassCode
wxClassInfo* c = sipCpp->GetClassInfo();
if(0) {}
#define C(clz) else if (c == CLASSINFO(clz)) { sipClass = sipClass_ ## clz; }
    C(BorderedFrame)
else
    sipClass = NULL;
#undef C
%End

    BorderedFrame(wxWindow* parent, SplitImage4* background, SplitImage4* border, const FrameSize& frameSize, int style = 0) /Transfer/;
    virtual ~BorderedFrame();

    bool SetBackground(SplitImage4* background /TransferBack/, const FrameSize& frameSize);
    void SetFrameSize(const FrameSize& frameSize);
    void SetRect(const wxRect& rect);

    bool SetTransparent(int alpha);
    int  GetAlpha() const;

    bool SetCursor(const wxCursor& cursor);

    void PaintBackground(wxDC& dc);
    void OnPaint(wxPaintEvent& dc);

    SplitImage4* splitBg;
    AlphaBorder* alphaBorder;
};

%If (WXMSW)
bool ApplyAlpha(wxWindow* window, wxBitmap& bitmap, unsigned char alpha = 255);
%End
