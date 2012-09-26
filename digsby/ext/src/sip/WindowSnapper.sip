class WindowSnapper /MainThreadDestructor/
{
%TypeHeaderCode
#include "WindowSnapper.h"
%End

private:
    WindowSnapper(const WindowSnapper&);

public:
    WindowSnapper(wxWindow* win, int snapMargin = 12, bool enable = true) /Transfer/;
    virtual ~WindowSnapper();

    bool SetEnabled(bool enable);
    bool IsEnabled() const;

    int GetSnapMargin() const;
    void SetSnapMargin(int snapMargin);

    bool GetSnapToScreen() const;
    void SetSnapToScreen(bool snapToScreen);

    void SetDocked(bool docked);

    // vector<SnapRect> WindowSnapper::GetSnapRects() const;
};
