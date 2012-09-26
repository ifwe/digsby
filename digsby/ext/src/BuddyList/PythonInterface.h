#ifndef PythonInterface_h
#define PythonInterface_h

#include "Group.h"
#include "BuddyListSorter.h"
#include "Contact.h"
#include <Python.h>


extern PyObject* groupType;
Group* fromPythonGroup(BuddyListSorter* sorter, PyObject* object);
bool fromContactOrder(PyObject* order_dict, ElemOrdering& ordering);
PyObject* toContactOrder(ElemOrdering& ordering);
inline PyObject* toPyString(const wstring& s);

Elem* stripNodes(Node* node, void* onlineSet = 0);

static bool gs_useDirtyFlag;

PyObject* pyContactForGroupname(PyObject* dict, const wstring& groupname);
PyObject* group__getitem__(Group* group, int i);
PyObject* wstringVectorToPyList(const vector<wstring>& strings);
#endif
