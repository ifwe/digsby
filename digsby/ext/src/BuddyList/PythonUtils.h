#ifndef PythonUtils_h
#define PythonUtils_h

#include "BuddyListCommon.h"
#include "Python.h"

/**
 * A PyObject smart pointer that handles reference counting internally.
 */
class PyPtr : public ElemUserData
{
public:
    PyPtr(PyObject* ptr)
        : m_ptr(ptr)
    {
        ref(ptr);
    }

    PyPtr(PyPtr* pyptr)
        : m_ptr(pyptr->get())
    {
        ref(m_ptr);
    }

    virtual PyPtr* clone()
    {
        return new PyPtr(this);
    }

    virtual ~PyPtr()
    {
        deref(m_ptr);
    }

    operator PyObject*() const { return m_ptr; }

    PyObject* get() const { return m_ptr; }

    PyPtr& operator=(const PyPtr& other)
    {
        deref(m_ptr);
        m_ptr = other.m_ptr;
        ref(m_ptr);

        return *this;
    }

    PyPtr(const PyPtr& other)
    {
        m_ptr = other.m_ptr;
        ref(m_ptr);
    }

    static void deref(PyObject* ptr)
    {
        Py_XDECREF(ptr);
    }

    static void ref(PyObject* ptr)
    {
        Py_XINCREF(ptr);
    }

protected:
    PyObject* m_ptr;
};
        

#endif // PythonUtils_h
