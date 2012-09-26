#ifndef TRANSPARENTFRAME_H__
#define TRANSPARENTFRAME_H__

#include <wx/frame.h>
#include <wx/bitmap.h>

void Unpremultiply(wxBitmap& bitmap);

class TransparentFrame : public wxFrame
{
public:
    TransparentFrame(wxWindow* parent);
    virtual ~TransparentFrame();

    void SetAlpha(int alpha) { m_alpha = alpha; }
    int GetAlpha() const { return m_alpha; }
    virtual wxBitmap GetBitmap();

    void OnPaint(wxPaintEvent&);

protected:
    int m_alpha;

    DECLARE_CLASS(TransparentFrame)
    DECLARE_EVENT_TABLE()
};

#endif // TRANSPARENTFRAME_H__

