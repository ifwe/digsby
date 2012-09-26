typedef int UINT;

class PlatformMessageBinder /MainThreadDestructor/
{
%TypeHeaderCode
    #include "PlatformMessages.h"
%End

private:
    PlatformMessageBinder(PlatformMessageBinder&);

public:
    static PlatformMessageBinder* ForWindow(wxWindow* win);
    PlatformMessageBinder(wxWindow* win);
    virtual ~PlatformMessageBinder();

    void Bind(UINT message, SIP_PYOBJECT callback);
    bool Unbind(UINT message);
};
