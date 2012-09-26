%ModuleHeaderCode
PyObject* RECT_to_tuple(LPRECT r);
%End

%ModuleCode
PyObject* RECT_to_tuple(LPRECT r)
{
    PyObject* left = PyInt_FromLong(r->left);
    PyObject* top = PyInt_FromLong(r->top);
    PyObject* right = PyInt_FromLong(r->right);
    PyObject* bottom = PyInt_FromLong(r->bottom);

    PyObject* obj = PyTuple_Pack(4, left, top, right, bottom);

    Py_DECREF(left);
    Py_DECREF(top);
    Py_DECREF(right);
    Py_DECREF(bottom);

    return obj;
}
%End

SIP_PYTUPLE GetMonitorInfo(long hmonitor);
%MethodCode
    MONITORINFOEX info;
    info.cbSize = sizeof(info);

    if (!GetMonitorInfo((HMONITOR)a0, &info)) {
        PyErr_SetFromWindowsErr(0);
        sipIsErr = 1;
    } else {
        PyObject* work = RECT_to_tuple(&info.rcWork);
        PyObject* monitor = RECT_to_tuple(&info.rcMonitor);
        PyObject* name = PyUnicode_FromWideChar(info.szDevice, wcslen(info.szDevice));

        if (work && monitor && name) {
            sipRes = PyTuple_Pack(3, work, monitor, name);
            Py_DECREF(work);
            Py_DECREF(monitor);
            Py_DECREF(name);
        } else
            sipIsErr = 1;
    }
%End


%ModuleHeaderCode
BOOL CALLBACK MultimonEnumProc(HMONITOR hMonitor, HDC hdcMonitor, LPRECT lprcMonitor, LPARAM dwData);
%End

%ModuleCode
BOOL CALLBACK MultimonEnumProc(HMONITOR hMonitor, HDC /*hdcMonitor*/, LPRECT /*lprcMonitor*/, LPARAM dwData)
{
    PyObject* intobj = PyLong_FromLong((long)hMonitor);
    PyList_Append((PyObject*)dwData, intobj);
    Py_DECREF(intobj);

    return TRUE;
}
%End

SIP_PYLIST GetHMONITORs();
%MethodCode
    PyObject* monitorList = PyList_New(0);
    if (!monitorList)
        sipIsErr = 1;
    else {
        if (!EnumDisplayMonitors(NULL, NULL, MultimonEnumProc, (LPARAM)monitorList)) {
            sipIsErr = 1;
            Py_DECREF(monitorList);
        } else
            sipRes = monitorList;
    }
%End
