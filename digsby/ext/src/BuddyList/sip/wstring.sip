//
// automatic conversion between python unicode/str objects and std::wstring
//

%MappedType wstring
{
%TypeHeaderCode
#include <string>
#ifdef __GNUC__
#include <alloca.h>
#define _alloca alloca
#endif
using std::wstring;
%End

%ConvertFromTypeCode
    return PyUnicode_FromWideChar(sipCpp->c_str(), sipCpp->size());
%End

// python unicode/str objects -> wstring
%ConvertToTypeCode
    // just a type check
    if (!sipIsErr)
        return PyUnicode_Check(sipPy) || PyString_Check(sipPy);

    PyObject* unicode = sipPy;
    bool needsDeref = false;

    // str -> unicode via utf-8
    if (PyString_Check(sipPy)) {
        unicode = PyUnicode_FromEncodedObject(sipPy, "utf-8", "replace");
        if (!unicode)
            return 0;

        needsDeref = true;
    }

    wstring* target = new wstring;

    // Move Unicode wchar_t bytes into wstring
    const size_t len = PyUnicode_GET_SIZE(unicode);
    if (len) {
        wchar_t* buf = (wchar_t*)_alloca(len * sizeof(wchar_t));
        PyUnicode_AsWideChar((PyUnicodeObject*)unicode, buf, len);
        target->assign(buf, len);
    }

    *sipCppPtr = target;

    if (needsDeref)
        Py_DECREF(unicode);

    return sipGetState(sipTransferObj);
%End
};



    void set_group_type(SIP_PYOBJECT);
%MethodCode
    Py_XDECREF(groupType);
    Py_INCREF(a0);
    groupType = a0;
%End

////

