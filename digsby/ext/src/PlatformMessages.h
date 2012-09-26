//
// binds callbacks to native GUI messages
//

#ifndef __PLATFORMMESSAGES_H__
#define __PLATFORMMESSAGES_H__

#include <wx/wx.h>
#include <wx/event.h>
#include "Python.h"

#ifdef __WXMSW__
#include <windows.h>

#include <map>
#include <vector>
using std::map;
using std::vector;

class NativeMsgHandler
{
public:
    virtual LRESULT handleMessage(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam) = 0;
};

typedef map<UINT, vector<NativeMsgHandler*>> NativeCallbackMap;

#else
#error "PlatformMessages does not support this platform yet."
#endif


class PlatformMessageBinder : public wxEvtHandler
{    
    DECLARE_DYNAMIC_CLASS(PlatformMessageBinder)
    // allows Python callbacks to respond to platform specific messages
    
public:
    static PlatformMessageBinder* ForWindow(wxWindow* win);

    PlatformMessageBinder();
    void Init(wxWindow*);

    virtual ~PlatformMessageBinder();
    
    void Bind(UINT message, PyObject* callback);
    bool Unbind(UINT message);

    void BindNative(UINT message, NativeMsgHandler* callback);
    bool UnbindNative(UINT message, NativeMsgHandler* callback);
    
#ifdef __WXMSW__
    LRESULT HandleMessage(UINT message, WPARAM wParam, LPARAM lParam);
#endif

protected:
    PlatformMessageBinder(wxWindow* win);

    typedef map<UINT, PyObject*> PythonCallbackMap;    
    PythonCallbackMap m_callbacks;
    
    NativeCallbackMap m_nativeCallbacks;
    
#ifdef __WXMSW__

    HWND m_hwnd;
    WNDPROC m_oldProc;
#endif
    
private:
    PlatformMessageBinder(PlatformMessageBinder&);    
};

#endif // __PLATFORMMESSAGES_H__
