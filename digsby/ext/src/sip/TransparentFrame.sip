class TransparentFrame :  wxFrame
{
%TypeHeaderCode
#include "TransparentFrame.h"
%End

public:
    TransparentFrame(wxWindow* parent);
    virtual ~TransparentFrame();

    void SetAlpha(int alpha);
    int GetAlpha() const;
    virtual wxBitmap GetBitmap();
    void OnPaint(wxPaintEvent&);
};

