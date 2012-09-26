#include "PlatformMessages.h"
#include "pyutils.h"

#include <windows.h>

#include <algorithm>

#if 0
#define DBG(x) x
#else
#define DBG(x) ((void*)0)
#endif

typedef map<HWND, PlatformMessageBinder*> WinMsgHandlers;
static WinMsgHandlers gs_handlers;
static int gs_binderCount = 0;

IMPLEMENT_DYNAMIC_CLASS(PlatformMessageBinder, wxEvtHandler)

// global callback function for all PlatformMessageBinder GWL_WNDPROC hooks
LRESULT APIENTRY PlatformMessageBinderProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    PlatformMessageBinder* msgBinder = 0;
    {
        WinMsgHandlers::iterator i = gs_handlers.find(hWnd);
        if (i != gs_handlers.end())
            msgBinder = i->second;

        // make sure the iterator goes out of scope before we call HandleMessage,
        // since the map may be cleared (and all its iterators made invalid)
        // as a result.
    }

    if (msgBinder)
        return msgBinder->HandleMessage(message, wParam, lParam);
    else {
        wxLogWarning(wxT("PlatformMessageBinderProc got unknown HWND %d"), hWnd);
        return DefWindowProc(hWnd, message, wParam, lParam);
    }
}

PlatformMessageBinder::PlatformMessageBinder(wxWindow* window)
{
    DBG(++gs_binderCount);
    DBG(fprintf(stderr, "PlatformMessageBinder(%p, window=%p) - now %d\n", this, window, gs_binderCount));
    Init(window);
}

PlatformMessageBinder::PlatformMessageBinder()
{
    DBG(++gs_binderCount);
    DBG(fprintf(stderr, "PlatformMessageBinder(%p) - now %d\n", this, gs_binderCount));
}

PlatformMessageBinder* PlatformMessageBinder::ForWindow(wxWindow* window)
{
    DBG(fprintf(stderr, "ForWindow(%p)\n", window));

    HWND hwnd = (HWND)window->GetHWND();
    WinMsgHandlers::iterator i = gs_handlers.find(hwnd);
    if (i != gs_handlers.end()) {
        DBG(fprintf(stderr, "  found existing: %p\n", i->second));
        return i->second;
    }
    
    PlatformMessageBinder* pmb = new PlatformMessageBinder(window);
    DBG(fprintf(stderr, "  returning new: %p\n", pmb));
    return pmb;
}

void PlatformMessageBinder::Init(wxWindow* window)
{
    m_hwnd = (HWND)window->GetHWND();
    m_oldProc = (WNDPROC)SetWindowLongPtr(m_hwnd, GWL_WNDPROC, (LONG_PTR)&PlatformMessageBinderProc);

    wxASSERT(gs_handlers.find(m_hwnd) == gs_handlers.end());
    gs_handlers[m_hwnd] = this;
}

void PlatformMessageBinder::Bind(UINT message, PyObject* callback)
{
    if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "callback must be callable");
    } else {
        // make sure to DECREF any old callback for this message
        // TODO: allow multiple callbacks per message
        if (Unbind(message))
            fprintf(stderr, "WARNING: Bind(%d) clobbered an old callback\n", message);

        Py_INCREF(callback);
        m_callbacks[message] = callback;
    }
}

void PlatformMessageBinder::BindNative(UINT message, NativeMsgHandler* cb)
{
    m_nativeCallbacks[message].push_back(cb);
}

bool PlatformMessageBinder::Unbind(UINT message)
{
    PythonCallbackMap::iterator i = m_callbacks.find(message);
    if (i != m_callbacks.end()) {
        PyObject* obj = i->second;
        m_callbacks.erase(message);
        Py_DECREF(obj);
        return true;
    }

    return false;
}

bool PlatformMessageBinder::UnbindNative(UINT message, NativeMsgHandler* cb)
{
    NativeCallbackMap::iterator i = m_nativeCallbacks.find(message);
    if (i != m_nativeCallbacks.end()) {
        vector<NativeMsgHandler*> cbs = i->second;
        cbs.erase(std::remove(cbs.begin(), cbs.end(), cb), cbs.end());
        m_nativeCallbacks.erase(message);
        return true;
    }

    return false;
}

LRESULT PlatformMessageBinder::HandleMessage(UINT message, WPARAM wParam, LPARAM lParam)
{
    bool execDefaultProc = true;

    // TODO: the point here is not to acquire python's GIL for every windows
    // message. however there should be another lock here around m_callbacks.

    // execute the python callback
    {
        PythonCallbackMap::iterator i = m_callbacks.find(message);
        if (i != m_callbacks.end()) {
            PY_BLOCK
            PyObject* cb = i->second;
            PyObject* result = PyObject_CallFunction(cb, "IIII", m_hwnd, message, wParam, lParam);
            if (result) {
                // if the callback returns False, don't run the original WndProc
                if (result == Py_False)
                    execDefaultProc = false;

                Py_DECREF(result);
            } else
                PyErr_Print();
            PY_UNBLOCK
        }
    }
    
    if (execDefaultProc) {
        // execute any native callbacks
        NativeCallbackMap::iterator i2 = m_nativeCallbacks.find(message);
        if (i2 != m_nativeCallbacks.end()) {
            vector<NativeMsgHandler*> handlers = i2->second;
            for (size_t n = 0; n < handlers.size(); ++n) {
                NativeMsgHandler* handler = handlers[n];
                handler->handleMessage(m_hwnd, message, wParam, lParam);
            }
        }
    }

    WNDPROC oldProc = m_oldProc;
    HWND hwnd = m_hwnd;

    // If necessary, run the old message handler.
    LRESULT res;
    if (execDefaultProc)
        res = CallWindowProc(oldProc, hwnd, message, wParam, lParam);
    else
        res = 1;

    if (message == WM_DESTROY)
        delete this;

    return res;
}

PlatformMessageBinder::~PlatformMessageBinder()
{
    DBG(--gs_binderCount);
    DBG(fprintf(stderr, "~PlatformMessageBinder(%p) - now %d\n", this, gs_binderCount));

    // Unregister our custom WM_MESSAGE hook
    SetWindowLongPtr(m_hwnd, GWL_WNDPROC, (LONG_PTR)m_oldProc);

    // Unhook from the global map of PlatformMessageBinders
    gs_handlers.erase(m_hwnd);

    // Release refcounts for all Python callbacks.
    PY_BLOCK

    PythonCallbackMap callbacks(m_callbacks);
    m_callbacks.clear();

    for(PythonCallbackMap::iterator i = callbacks.begin(); i != callbacks.end(); ++i)
        Py_DECREF(i->second);

    callbacks.clear();

    PY_UNBLOCK

    m_nativeCallbacks.clear();
}

