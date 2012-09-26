#ifndef WindowTargetWx_h
#define WindowTargetWx_h

#include "AnimationPlatform.h"
#include <wx/window.h>

class Layer;

class WindowTarget : public wxWindow
{
public:
    WindowTarget(wxWindow* parent, int id = wxID_ANY);

    void invalidate();
    void invalidate(const Rect& rect);

    void setRootLayer(Layer* layer);
    Layer* rootLayer() const { return m_rootLayer; }

    String lastStatus() const { return m_lastStatus; }

protected:
    virtual void OnPaint(wxPaintEvent& e);

    DECLARE_EVENT_TABLE()

    Layer* m_rootLayer;
    String m_lastStatus;
};

#endif // WindowTargetWx_h
