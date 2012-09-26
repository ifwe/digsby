#include "pyutils.h"

#if !WXPY
#include "wx/wxPython/wxPython.h"

wxString getstring(PyObject* obj, const char* attr, wxString def)
{
    wxString result(def);
    
    PyGILState_STATE state = PyGILState_Ensure();

	PyObject* valobj = PyObject_GetAttrString(obj, attr);
	if ( valobj )
	{
		result = Py2wxString(valobj);
		Py_DECREF(valobj);
	}

	PyGILState_Release(state);

	return result;
}
#endif