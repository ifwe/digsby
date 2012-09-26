//
// automatic conversion between python unicode/str objects and std::wstring
//

%MappedType std::string
{
%TypeHeaderCode
#include <string>
using std::string;
%End

%ConvertFromTypeCode
    PyObject * s = PyString_FromStringAndSize(sipCpp->c_str(), sipCpp->size());
//    if (!s)
//        sipIsErr = 1;
    PyObject * u = PyUnicode_FromEncodedObject(s, "utf-8", "strict");
    Py_DECREF(s);
    return u;
%End

// python unicode/str objects -> string
%ConvertToTypeCode
    // just a type check
    if (!sipIsErr)
        return PyUnicode_Check(sipPy) || PyString_Check(sipPy);

    PyObject* str = sipPy;
    bool needsDeref = false;

    if (PyUnicode_Check(sipPy)) {
        str = PyUnicode_AsEncodedString(sipPy, "utf-8", "strict");
        if (!str)
            return 0;
        needsDeref = true;
    }

    *sipCppPtr = new string(PyString_AsString(str), PyString_GET_SIZE(str));

    if (needsDeref)
        Py_DECREF(str);

    return sipGetState(sipTransferObj);
%End
};

