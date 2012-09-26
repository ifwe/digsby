#ifndef ___PYUTILS_H___
#define ___PYUTILS_H___

#include <Python.h>

#include "wx/wxprec.h"
#ifndef WX_PRECOMP
#include "wx/wx.h"
#endif

#if !WXPY
wxString getstring(PyObject* obj, const char* attr, wxString def = wxT(""));
#endif
//
// macro to block/unblock threads
//
#if WXPY

#include <sip.h>
#ifndef SIP_BLOCK_THREADS
#error "WXPY is 1, but SIP_BLOCK_THREADS is not defined"
#endif

#define PY_BLOCK SIP_BLOCK_THREADS
#define PY_UNBLOCK SIP_UNBLOCK_THREADS

#else // SWIG

#define PY_BLOCK PyGILState_STATE __python_threadstate = PyGILState_Ensure();
#define PY_UNBLOCK PyGILState_Release(__python_threadstate);
#endif

#endif
