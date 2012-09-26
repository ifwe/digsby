#include "Python.h"
#include "GettextPython.h"

static bool fromPyString(PyObject* sipPy, wxString& target)
{
    PyObject* unicode = sipPy;
    bool needsDeref = false;

    // str -> unicode via utf-8
    if (PyString_Check(sipPy))
    {
        unicode = PyUnicode_FromEncodedObject(sipPy, "utf-8", "replace");
        if (!unicode)
            return false;

        needsDeref = true;
    }

    // Move Unicode wchar_t bytes into wxString
    size_t len = PyUnicode_GET_SIZE(unicode);
    if (len) {
        PyUnicode_AsWideChar((PyUnicodeObject*)unicode, target.GetWriteBuf(len), len);
        target.UngetWriteBuf();
    }

    if (needsDeref)
        Py_DECREF(unicode);

    return true;
}

wxString _(const char* s)
{
    PyObject* builtin = PyImport_ImportModule("__builtin__");
    if (!builtin)
        return wxString::FromUTF8(s);

    wxString result;
    wxString wxs;

    PyObject* builtinDict = PyModule_GetDict(builtin);
    if (!builtinDict)
        goto error;

    if (!PyDict_Check(builtinDict))
        goto error;

    PyObject* underscoreCallable = PyDict_GetItemString(builtinDict, "_");
    if (!underscoreCallable)
        goto error;

    PyObject* string = PyObject_CallFunction(underscoreCallable, "s", s);
    if (!string)
        goto error;

    bool didString = fromPyString(string, wxs);
    Py_DECREF(string);

    if (!didString)
        goto error;

    result = wxs;
    goto done;

error:
    result = wxString::FromUTF8(s);

done:
    Py_DECREF(builtin);
    return result;
}

