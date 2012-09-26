%UnitCode
#include "precompiled.h"
#include "config.h"
%End
%Module blist

%ModuleHeaderCode
#include "PythonInterface.h"
#include "BuddyChange.h"
#include "Sorters.h"
#include "FileUtils.h"

inline PyObject* wstringToPy(const wstring& s)
{
    return PyUnicode_FromWideChar(s.c_str(), s.size());
}
%End

%Include wstring.sip

/**
 * Attributes which we sort and group by.
 *
 * For now, this enum must be duplicated in Comparators.h
 */
enum SortBy
{
    UserOrdering = 1,
    Name         = 2,
    LogSize      = 4,
    Service      = 8,
    Status       = 16,
    Alias        = 32,
    CustomOrder  = 64,
    Mobile       = 128,
    Online       = 256,
};

void use_dirty(bool);
%MethodCode
    gs_useDirtyFlag = a0;
%End

void setNodeTracking(bool);
void dumpNodes();

class BuddyListSorter
{
%TypeHeaderCode
#include "BuddyListSorter.h"
%End

public:
    BuddyListSorter();

    void set_root(SIP_PYOBJECT);
%MethodCode
		sipCpp->clearNodes();
        Group* group = fromPythonGroup(sipCpp, a0);
        if (!group) {
            sipIsErr = 1;
        } else {
            sipCpp->setRoot(group);
            delete group;
        }
%End

    void setPruneEmpty(bool);

    void addSorter(Grouper* grouper /Transfer/);
    void clearSorters();
    void clearNodes();
    bool removeAccount(const wstring& name, const wstring& service);
    bool removeContact(const wstring& contactId);
    void removeAllContacts();
    void buddyChanged(const wstring& accountService,
                      const wstring& accountName,
                      const wstring& buddyName,
                      const wstring& buddyService,
                      unsigned int change);

    void set_contact_order(SIP_PYOBJECT);
%MethodCode
    ElemOrdering ordering;
    if (!fromContactOrder(a0, ordering))
        sipIsErr = 1;
    sipCpp->setOrdering(ordering);
%End

    SIP_PYOBJECT get_contact_order();
%MethodCode
    sipRes = toContactOrder(sipCpp->ordering());
    if (!sipRes)
        sipIsErr = 1;
%End

    void setComparators(SIP_PYOBJECT);
%MethodCode
    PyObject* seq = PySequence_Fast(a0, "setComparators takes a sequence of SortBy enums");
    if (!seq)
        sipIsErr = 1;
    else {
        const int n = PySequence_Fast_GET_SIZE(seq);
        PyObject** elems = PySequence_Fast_ITEMS(seq);
        vector<SortBy> sorts;
        for (int i = 0; i < n; ++i) {
            PyObject* elem = *elems++;
            if (!PyInt_Check(elem)) {
                PyErr_SetString(PyExc_TypeError, "Comparator enums must be integers");
                sipIsErr = 1;
                break;
            }

            sorts.push_back(static_cast<SortBy>(PyInt_AsLong(elem)));
        }
        Py_DECREF(seq);

        if (!sipIsErr)
            sipCpp->setComparators(sorts);
    }
%End

    bool sortsBy(int sortBy) const;

    wstring dump_root(bool showFlags = true, bool showGroupNames = false);
%MethodCode
        sipRes = new wstring(treeToString(sipCpp->root(), false, a0, a1));
%End

    wstring dump_gather(bool showFlags = true, bool showGroupNames = false);
%MethodCode
        Node* root = sipCpp->gather();
        sipRes = new wstring(treeToString(root, false, a0, a1));
        delete root;
%End

    Group* root() const;
%MethodCode
        sipRes = stripNodes(sipCpp->root())->asGroup();
%End

    Group* _gather() const;
%MethodCode
        Node* merged = sipCpp->gather();
        sipRes = stripNodes(merged)->asGroup();
        delete merged;
%End

    void _done_gather(Group* g) const;
%MethodCode
        //if (a0)
            //delete a0;
%End

    wstring contactReprs() const;


};

/////

class Node
{
%TypeHeaderCode
#include "Node.h"
%End

public:

wstring name;
%GetCode
    sipPy = wstringToPy(sipCpp->name());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "name is read-only");
    sipErr = 1;
%End

wstring __repr__();
%MethodCode
    sipRes = new wstring(sipCpp->repr());
%End

int __len__();
%MethodCode
    sipRes = (int)sipCpp->numChildren();
%End

Node* __getitem__(int i);
%MethodCode
if (a0 < 0)
    a0 = sipCpp->numChildren() - a0;
if (a0 >= (int)sipCpp->numChildren()) {
    PyErr_Format(PyExc_IndexError, "index out of range: %d", a0);
    sipIsErr = 1;
} else {
    sipRes = sipCpp->children()[a0];
}
%End

private:
    Node();
    ~Node();
};

/////

class Elem
{
%TypeHeaderCode
#include "BuddylistCommon.h"
#include "PythonUtils.h"
%End

public:

wstring name;
%GetCode
    sipPy = wstringToPy(sipCpp->name());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "name is read-only");
    sipErr = 1;
%End

%ConvertToSubClassCode
if (sipCpp->asContact())
    sipClass = sipClass_Contact;
else if (sipCpp->asBuddy())
    sipClass = sipClass_Buddy;
else if (sipCpp->asGroup())
    sipClass = sipClass_Group;
else
    BL_ASSERT_NOT_REACHABLE(0);
%End

wstring __repr__();
%MethodCode
    if (sipCpp)
        sipRes = new wstring(sipCpp->repr());
    else
        sipRes = new wstring(L"<null Elem>");
%End

%GCTraverseCode
    sipRes = 0;
    if (PyPtr* pyptr = reinterpret_cast<PyPtr*>(sipCpp->userdata()))
        if (PyObject *obj = pyptr->get())
            sipRes = sipVisit(obj, sipArg);
%End

%GCClearCode
    sipCpp->setUserdata(0);
    sipRes = 0;
%End

private:
    Elem();
    ~Elem();
};

/////

class Group : Elem
{
%TypeHeaderCode
#include "Group.h"
#include "PythonUtils.h"
%End

public:

wstring groupKey() const /PyName=groupkey/;

SIP_PYOBJECT _protocol_ids;
%GetCode
    PyPtr* pyptr = reinterpret_cast<PyPtr*>(sipCpp->userdata());

    if (pyptr) {
        PyObject* tuple = pyptr->get();
        Py_INCREF(tuple);
        sipPy = tuple;
    } else {
        Py_INCREF(Py_None);
        sipPy = Py_None;
    }
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "_protocol_ids is read-only");
    sipErr = 1;
%End

int __len__();
%MethodCode
    sipRes = (int)sipCpp->numChildren();
%End

SIP_PYOBJECT __getitem__(int i);
%MethodCode
if (a0 < 0)
    a0 = sipCpp->numChildren() - a0;
if (a0 >= (int)sipCpp->numChildren()) {
    PyErr_Format(PyExc_IndexError, "index out of range: %d", a0);
    sipIsErr = 1;
} else {
    Elem* elem = sipCpp->children()[a0];

    if (Buddy* b = elem->asBuddy()) {
        // In v1 of C++ sorting, we're storing references back to the original Python
        // buddy objects. Here's where we return them.
        PyPtr* ptr = reinterpret_cast<PyPtr*>(b->userdata());
        if (ptr) {
            PyObject* dict = ptr->get();
            if (dict) {
                sipRes = pyContactForGroupname(dict, sipCpp->name());
                if (!sipRes)
                    sipIsErr = 1;
            } else {
                sipIsErr = 1;
                PyErr_SetString(PyExc_AssertionError, "buddy's pyptr was NULL");
            }
        }
    } else {
        Group* g = elem->asGroup();
        BL_ASSERT(g);
        sipRes = sipConvertFromInstance(elem, sipClass_Group, NULL);
    }
}
%End

wstring display_string;
%GetCode
    sipPy = wstringToPy(sipCpp->displayString());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "display_string is read-only");
    sipErr = 1;
%End

void destroy();
%MethodCode
    delete sipCpp;
%End

    virtual ~Group();

private:
    Group();
};

/////

class Buddy : Elem
{
%TypeHeaderCode
#include "Buddy.h"
%End

private:
    Buddy();
    ~Buddy();
};

class Contact : Elem
{
%TypeHeaderCode
#include "Contact.h"
%End

public:

wstring alias;
%GetCode
    sipPy = wstringToPy(sipCpp->alias());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "alias is read-only");
    sipErr = 1;
%End

wstring service;
%GetCode
    sipPy = wstringToPy(sipCpp->service());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "service is read-only");
    sipErr = 1;
%End

wstring status;
%GetCode
    sipPy = wstringToPy(sipCpp->status());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "status is read-only");
    sipErr = 1;
%End

bool online;
%GetCode
    sipPy = PyBool_FromLong(sipCpp->online());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "online is read-only");
    sipErr = 1;
%End

bool mobile;
%GetCode
    sipPy = PyBool_FromLong(sipCpp->mobile());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "mobile is read-only");
    sipErr = 1;
%End

wstring stripped_msg;
%GetCode
    sipPy = wstringToPy(sipCpp->strippedStatus());
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "stripped_msg is read-only");
    sipErr = 1;
%End

SIP_PYOBJECT icon;
%GetCode
    Py_INCREF(Py_None);
    sipPy = Py_None;
%End
%SetCode
    PyErr_SetString(PyExc_AttributeError, "icon is read-only");
    sipErr = 1;
%End

private:
    Contact();
    ~Contact();
};

class Grouper
{
%TypeHeaderCode
#include "Sorters.h"
%End
public:
    wstring repr() const;
private:
    Grouper();
};


class ByGroup : Grouper
{
%TypeHeaderCode
#include "Sorters.h"
%End

public:
    ByGroup(bool showGroups = true, int skipLevel = -1);

};

class ByStatus : Grouper
{
%TypeHeaderCode
#include "Sorters.h"
%End

public:
    ByStatus(bool showGroups = true, bool showOffline = true);
};

class ByOnline : Grouper
{
%TypeHeaderCode
#include "Sorters.h"
%End

public:
    ByOnline(bool groupOffline = true, bool showOffline = true);
};

class ByMobile : Grouper
{
%TypeHeaderCode
#include "Sorters.h"
%End

public:
    ByMobile(bool showMobile = true);
};

class ByService : Grouper
{
%TypeHeaderCode
#include "Sorters.h"
%End

public:
    ByService(bool showGroups = true);
    void setGroupName(const wstring& service, const wstring& name);
};

class ByFakeRoot : Grouper
{
%TypeHeaderCode
#include "Sorters.h"
%End

public:
    ByFakeRoot(const wstring& name);
};

class BySearch : Grouper
{
%TypeHeaderCode
#include "Sorters.h"
%End

public:
    BySearch(wstring& searchString, wstring& groupName, int searchAttributes = AllSearchable);

    bool caseInsensitive() const;
    void setCaseInsensitive(bool caseInsensitive);

    void setGroupContacts(bool groupContacts);
    bool groupContacts() const;

    wstring groupName() const;
};

wstring fakeRootGroupKey();

// extra file utilities that should go in another binary

unsigned long long sumFileSizes(const wstring& wildcard);

SIP_PYOBJECT findFiles(const wstring& wildcard, bool sort = true);
%MethodCode
    std::vector<std::wstring> files;
    if (!findFiles(files, *a0, a1)) {
        PyErr_SetString(PyExc_IOError, "error finding files");
        sipIsErr = 1;
    } else {
        sipRes = wstringVectorToPyList(files);
        if (!sipRes)
            sipIsErr = 1;
    }
%End

SIP_PYOBJECT getLogSizes(const wstring& logdir);
%MethodCode
    LogSizeMap sizes;

    // this may take awhile, so release the GIL
    Py_BEGIN_ALLOW_THREADS
    getLogSizes(sizes, *a0);
    Py_END_ALLOW_THREADS

    PyObject* dict = PyDict_New();

    for (LogSizeMap::const_iterator i = sizes.begin();
         i != sizes.end(); ++i) {
        PyObject* key = toPyString(i->first);
        PyObject* value = PyLong_FromUnsignedLongLong(i->second);
        if (PyDict_SetItem(dict, key, value)) {
            sipIsErr = 1;
            Py_DECREF(dict);
            break;
        }
        Py_DECREF(key);
        Py_DECREF(value);
    }

    if (!sipIsErr)
        sipRes = dict;
%End

