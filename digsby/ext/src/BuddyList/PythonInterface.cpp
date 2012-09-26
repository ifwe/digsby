#include "precompiled.h"
#include "config.h"

#include "Python.h"
#include "PythonUtils.h"

#include "Contact.h"
#include "Group.h"
#include "Buddy.h"
#include "Account.h"
#include "BuddyListSorter.h"
#include "StringUtils.h"

#include <string>
#include <sstream>

using std::string;
using std::wostringstream;

#ifdef __GNUC__
#include <alloca.h>
#define _alloca alloca
#endif

#include "GNUC.h"
#ifdef __GNUC__
#include <ext/hash_set>
#else
#include <hash_set>
#endif
using stdext::hash_set;

int fromPyString(PyObject* obj, wstring& str);

static bool addProtoIdsTuple(Group* groupElem, PyObject* protocol, PyObject* id);

static bool gs_useDirtyFlag = true;

/**
 * A Group subclass overridding Group::merge(Elem*) so that we can merge protocols and ids.
 */
class PythonGroup : public Group
{
public:
    PythonGroup(const wstring& name)
        : Group(name)
    {}

    virtual Group* newGroup(const wstring& name)
    {
        return new PythonGroup(name);
    }

    /**
     * Merges protocols and ids with another PythonGroup.
     *
     * Called by the sorter when two groups with the same key are merged.
     */
    virtual void merge(Elem* other)
    {
        PyPtr* ptr = reinterpret_cast<PyPtr*>(other->userdata());
        if (!ptr)
            return;

        PyObject* protoIdsTuple = ptr->get();

        BL_ASSERT(PyTuple_CheckExact(protoIdsTuple));

        PyObject* protos = PyTuple_GET_ITEM(protoIdsTuple, 0);
        PyObject* ids    = PyTuple_GET_ITEM(protoIdsTuple, 1);

        BL_ASSERT(PyList_CheckExact(protos));
        BL_ASSERT(PyList_CheckExact(ids));

        const int n = PyList_GET_SIZE(protos);
        for (int i = 0; i < n; ++i) {
            PyObject* proto = PyList_GET_ITEM(protos, i);
            PyObject* id    = PyList_GET_ITEM(ids, i);
            BL_ASSERT(proto && id);
            if (proto != Py_None && id != Py_None)
                addProtoIdsTuple(this, proto, id);
        }
    }
};

// returns a std::string from a PyObject's __repr__
string repr(PyObject* o)
{
    PyObject* s = PyObject_Repr(o);
    if (!s) return "<error>";
    string str(PyString_AsString(s));
    Py_DECREF(s);
    return str;
}

/**
 * Converts a std::wstring to a PyUnicode*.
 */
inline PyObject* toPyString(const wstring& s)
{
    return PyUnicode_FromWideChar(s.c_str(), s.size());
}

// assigns the unicode value of obj into str, returning 0 on success
inline int fromPyString(PyObject* obj, wstring& str)
{
    int error = 0;
    PyObject* uni = 0;

    // convert str to unicode by assuming utf-8
    if (!PyUnicode_Check(obj)) {
        // TODO: use strict, or disallow str altogether
        uni = PyUnicode_FromEncodedObject(obj, "utf-8", "replace");
        if (!uni) {
            PyErr_Format(PyExc_TypeError, "expected unicode: %s", repr(obj).c_str());
            return -1;
        }

        obj = uni;
    }

    PyUnicodeObject* unicodeObject = reinterpret_cast<PyUnicodeObject*>(obj);

#ifndef HAVE_USABLE_WCHAR_T
    // convert to wchar_t
    const int len = PyUnicode_GetSize(obj);
    wchar_t* buf = reinterpret_cast<wchar_t*>(_alloca(len * sizeof(wchar_t)));
    int copied = PyUnicode_AsWideChar(unicodeObject, buf, len);

    if (copied == -1)
        error = -1;
    else {
        BL_ASSERT(copied == len);
        str.assign(buf, len);
    }
#else
    // If Py_UNICODE is just wchar_t, avoid the extra copy and use
    // std::wstring::assign on the unicode object's buffer directly.
    str.assign((wchar_t*)PyUnicode_AS_UNICODE(unicodeObject),
               PyUnicode_GET_SIZE(unicodeObject));
#endif

    if (uni)
        Py_DECREF(uni);
    return error;
}

// std::wstring = getattr(obj, attr)
inline int PyGetWstring(PyObject* obj, const char* attr, wstring& wstr)
{
    PyObject* strobj = PyObject_GetAttrString(obj, attr);
    if (!strobj) return -1;

    int result = fromPyString(strobj, wstr);
    Py_DECREF(strobj);
    return result;
}

// TODO: remove global data
PyObject* groupType = 0;

static int isGroup(PyObject* o)
{
    if (!groupType) {
        PyErr_SetString(PyExc_AssertionError, "Must set Python Group type via blist.set_group_type");
        return -1;
    }

    return PyObject_IsInstance(o, groupType);
}

static bool storePythonBuddyObject(Buddy* buddy, const wstring& _groupname, PyObject* obj)
{
    wstring groupname(wstringToLower(_groupname));

    PyPtr* pyptr = reinterpret_cast<PyPtr*>(buddy->userdata());

    PyObject* dict;
    if (!pyptr) {
        dict = PyDict_New();
        if (!dict)
            return false;

        pyptr = new PyPtr(dict);
        buddy->setUserdata(pyptr);
        Py_DECREF(dict);
    } else {
        dict = pyptr->get();
        if (!dict) {
            PyErr_SetString(PyExc_AssertionError, "C++ Buddy object had NULL PyPtr");
            return false;
        }
    }

    PyObject* key = toPyString(groupname);
    if (!key)
        return false;

    bool success = 0 == PyDict_SetItem(dict, key, obj);
    Py_DECREF(key);
    return success;
}

/**
 * Given a buddy, gets buddy.protocol.account.name and
 * buddy.protocol.account.protocol.
 */
bool getAccountNameAndService(PyObject* buddy, wstring& username, wstring& service, wstring& protoUsername)
{
    PyObject* pyProtocol = PyObject_GetAttrString(buddy, "protocol");
    if (!pyProtocol)
        return false;

    PyObject* pyAccount = PyObject_GetAttrString(pyProtocol, "account");
    if (!pyAccount) {
        Py_DECREF(pyProtocol);
        return false;
    }

    bool success = true;
    if (PyGetWstring(pyAccount, "name", username) ||
        PyGetWstring(pyAccount, "protocol",  service) ||
        PyGetWstring(pyProtocol, "username",  protoUsername) )
        success = false;

    Py_DECREF(pyAccount);
    Py_DECREF(pyProtocol);

    return success;
}

static bool addExtraSearchStrings(Buddy* b, PyObject* o)
{
    PyObject* seq = PySequence_Fast(o, "Expected a metacontact to be iterable");
    if (!seq)
        return false;

    wstring buddyName;

    const int n = PySequence_Fast_GET_SIZE(seq);
    PyObject** elems = PySequence_Fast_ITEMS(seq);
    for (int i = 0; i < n; ++i) {
        PyObject* elem = *elems++;

        if (PyGetWstring(elem, "name", buddyName)) {
            Py_DECREF(seq);
            return false;
        } else
            b->addExtraSearchString(buddyName);
    }

    Py_DECREF(seq);
    return true;
}

// turns a Python Buddy object into a C++ Buddy
Buddy* fromPythonBuddy(BuddyListSorter* sorter, PyObject* o, const wstring& groupName)
{
    Buddy* buddy = 0;

    wstring buddyName, buddyAlias, buddyService, buddyStatus;
    wstring username, accountService, protoUsername;
    bool buddyLeaving;
    int buddyLogSize = 0;
    bool buddyMobile = false;
    bool setMobile   = false;
    bool setLeaving  = false;

    PyObject* dirty = PyObject_GetAttrString(o, "_notify_dirty");
    BL_ASSERT(dirty && PyBool_Check(dirty));
    bool is_dirty = (dirty && (dirty == Py_True)) || !gs_useDirtyFlag;

    if (is_dirty)
        PyObject_SetAttrString(o, "_notify_dirty", Py_False);

    bool setAlias = false;
    if (dirty)
        Py_DECREF(dirty);

    if (!getAccountNameAndService(o, username, accountService, protoUsername))
        return 0;

    if (PyGetWstring(o, "name", buddyName)) return 0;
    if (PyGetWstring(o, "sortservice", buddyService)) {
        PyErr_Clear();
        if (PyGetWstring(o, "service", buddyService)) return 0;
    }

    Account* acct = sorter->account(username, accountService);
    acct->setProtocolUsername(protoUsername);
    buddy = acct->buddy(buddyName, buddyService);
    buddy->addServerGroup(groupName);

    // metacontact hack: grab buddy names so they are searchable
    if (buddyName.substr(0, 13) == L"Metacontact #")
        addExtraSearchStrings(buddy, o);

    if (!is_dirty && !buddy->dirty())
        goto set_buddy_ptr;

    buddy->setDirty(false);

    if (sorter->sortsBy(Alias)) {
        if (PyGetWstring(o, "alias", buddyAlias)) return 0;
        setAlias = true;
    }
    if (sorter->sortsBy(Status)) {
        // buddy.status
        if (PyGetWstring(o, "status_orb", buddyStatus)) return 0;

        // buddy.leaving
        PyObject* leaving = PyObject_GetAttrString(o, "leaving");
        if (!leaving)
            PyErr_Clear();
        else {
            buddyLeaving = (PyBool_Check(leaving) && (leaving == Py_True));
            Py_DECREF(leaving);
            setLeaving = true;
        }
    }
    if (sorter->sortsBy(Mobile)) {
        PyObject* mobile = PyObject_GetAttrString(o, "mobile");
        if (!mobile) return 0;
        buddyMobile = (PyBool_Check(mobile) && (mobile == Py_True));
        Py_DECREF(mobile);
        setMobile = true;
    }
    if (sorter->sortsBy(LogSize)) {
        PyObject* logSize = PyObject_GetAttrString(o, "log_size");
        if (!logSize)
            return NULL;

        if (-1 == (buddyLogSize = PyLong_AsLong(logSize))) return NULL;
        Py_DECREF(logSize);
    }

    if (setAlias)
        buddy->setAlias(buddyAlias);
    if (!buddyStatus.empty())
        buddy->setStatus(buddyStatus);
    if (setMobile)
        buddy->setMobile(buddyMobile);
    if (setLeaving)
        buddy->setLeaving(buddyLeaving);

    buddy->setLogSize(buddyLogSize);

set_buddy_ptr:
    // store a reference to the Python object in the C++ Buddy object
    //buddy->setUserdata(new PyPtr(o));

    if (!storePythonBuddyObject(buddy, groupName, o))
        buddy = NULL;

    return buddy;
}

// turns a Python Group object into a C++ Group
static const char* groupTypeError = "Group objects must be sequences";

// tuple must be a tuple
// elem will be added to the nth list in the tuple
static bool addToNthList(PyObject* tuple, PyObject* elem, int n)
{
    BL_ASSERT(PyTuple_CheckExact(tuple));

    PyObject* list = PyTuple_GET_ITEM(tuple, n);
    if (!list)
        return false;

    BL_ASSERT(PyList_CheckExact(list));

    return PyList_Append(list, elem) != -1;
}

static bool addProtoIdsTuple(Group* groupElem, PyObject* protocol, PyObject* id)
{
    bool success = true;

    PyPtr* protoIdsPtr = reinterpret_cast<PyPtr*>(groupElem->userdata());

    if (!protoIdsPtr) {
        // No proto/id tuple there yet.
        // build a list of two tuples: [(protocols, ...), (ids, ...)]
        PyObject* protoIdsTuple = Py_BuildValue("([O],[O])", protocol, id);
        if (protoIdsTuple)
            groupElem->setUserdata(new PyPtr(protoIdsTuple));
        else
            success = false;
        Py_DECREF(protoIdsTuple);
    } else {
        // There's already a tuple there. Add protocol and id to it.
        PyObject* protoIdsTuple = protoIdsPtr->get();

        if (!addToNthList(protoIdsTuple, protocol, 0))
            success = false;
        else if (!addToNthList(protoIdsTuple, id, 1))
            success = false;
    }

    return success;
}

static bool addProtoIdsTuple(Group* groupElem, PyObject* group)
{
    bool success = true;

    // Grab protocol, id from the group.
    PyObject* protocol = PyObject_GetAttrString(group, "protocol");

    if (!protocol)
        return false;

    PyObject* id = PyObject_GetAttrString(group, "id");
    if (!id) {
        Py_DECREF(protocol);
        return false;
    }

    if (protocol != Py_None && id != Py_None)
        success = addProtoIdsTuple(groupElem, protocol, id);

    Py_DECREF(protocol);
    Py_DECREF(id);

    return success;
}

/**
 * Python groups with a "_root" attribute set to True get put into Nodes marked
 * with FlagRootGroup.
 */
bool isRoot(PyObject* group)
{
    PyObject* is_root = PyObject_GetAttrString(group, "_root");
    if (!is_root) {
        PyErr_Clear();
        return false;
    }

    bool root = PyBool_Check(is_root) && is_root == Py_True;
    Py_DECREF(is_root);
    return root;
}

Group* fromPythonGroup(BuddyListSorter* sorter, PyObject* object)
{
    if (!PySequence_Check(object)) {
        PyErr_SetString(PyExc_TypeError, groupTypeError);
        return NULL;
    }

    wstring groupName;
    if (PyGetWstring(object, "name", groupName))
        return NULL;

    PyObject* seq = PySequence_Fast(object, groupTypeError);
    if (!seq)
        return NULL;

    Group* group = new PythonGroup(groupName);
    if (!addProtoIdsTuple(group, object)) {
        delete group;
        Py_DECREF(seq);
        return NULL;
    }

    group->setRoot(isRoot(object));

    const int m = PySequence_Fast_GET_SIZE(seq);
    PyObject** elems = PySequence_Fast_ITEMS(seq);
    for (int i = 0; i < m; ++i) {
        PyObject* elem = *elems++;

        int is_group = isGroup(elem);
        Elem* child = 0;

        if (is_group == 1)
            child = fromPythonGroup(sorter, elem);
        else if (is_group == 0)
            child = fromPythonBuddy(sorter, elem, groupName);

        if (!child) {
            delete group;
            group = 0;
            goto done;
        } else
            group->addChild(child);
    }

done:
    Py_DECREF(seq);
    return group;
}

PyObject* wstringVectorToPyList(const vector<wstring>& strings)
{
    PyObject* pylist = PyList_New(strings.size());
    if (!pylist) return NULL;

    int n = 0;
    for(vector<wstring>::const_iterator i = strings.begin(); i != strings.end(); ++i) {
        PyObject* pystr = toPyString(*i);
        if (!pystr) {
            Py_DECREF(pylist);
            return NULL;
        }

        PyList_SET_ITEM(pylist, n++, pystr);
    }

    return pylist;
}

PyObject* elemOrderIndicesToPyList(ElemOrderIndices& map)
{
    return wstringVectorToPyList(map.values());
}

PyObject* toContactOrder(ElemOrdering& ordering)
{
    bool err = false;

    PyObject* d = PyDict_New();
    if (!d) return NULL;

    for (ElemOrdering::iterator i = ordering.begin(); i != ordering.end(); ++i) {
        PyObject* key = toPyString(i->first);
        if (!key) {
            Py_DECREF(d);
            return NULL;
        }

        PyObject* list = elemOrderIndicesToPyList(i->second);
        if (!list) {
            Py_DECREF(d);
            Py_DECREF(key);
            return NULL;
        }

        if (-1 == PyDict_SetItem(d, key, list)) {
            Py_DECREF(d);
            Py_DECREF(list);
            Py_DECREF(key);
            return NULL;
        }

        Py_DECREF(list);
        Py_DECREF(key);
    }

    return d;
}

bool fromContactOrder(PyObject* order_dict, ElemOrdering& ordering)
{
    bool isErr = false;

    // orderDict should be:
    // {'groupname': ['service/acctname/buddyname', ...], ... }

    if (!PyDict_Check(order_dict)) {
        PyErr_SetString(PyExc_TypeError, "order_dict must be a dict");
        return false;
    }

    PyObject* values = PyMapping_Values(order_dict);
    if (!values)
        return false;

    PyObject *key, *val;
    Py_ssize_t pos = 0;

    wstring groupname;
    while (PyDict_Next(order_dict, &pos, &key, &val)) {
        if (fromPyString(key, groupname))
            goto err;

        PyObject* seq = PySequence_Fast(val, "invalid contact ordering: subelement must be a sequence");
        if (!seq) {
            PyErr_SetString(PyExc_TypeError, "invalid contact ordering type");
            goto err;
        }

        ElemOrderIndices groupMap;

        const int m = PySequence_Fast_GET_SIZE(seq);
        PyObject** elems = PySequence_Fast_ITEMS(seq);
        wstring contactid;
        for (int j = 0; j < m; ++j) {
            PyObject* elem = *elems++;
            if (fromPyString(elem, contactid)) {
                Py_DECREF(seq);
                goto err;
            }
            groupMap._add(contactid, j);
        }

        ordering[groupname] = groupMap;
        Py_DECREF(seq);
    }

    goto cleanup;
err:
    isErr = true;

cleanup:
    Py_DECREF(values);

    return !isErr;
}

/**
 * New reference.
 */
PyObject* pyContactForGroupname(PyObject* dict, const wstring& groupname)
{
    PyObject* pygroupname = toPyString(wstringToLower(groupname));
    if (!pygroupname)
        return NULL;

    PyObject* buddy = PyDict_GetItem(dict, pygroupname);
    Py_DECREF(pygroupname);

    if (buddy)
        Py_INCREF(buddy);
    else {
        PyObject* values = PyDict_Values(dict);
        if (!values)
            return NULL;

        buddy = PyList_GetItem(values, 0);
        Py_DECREF(values);
        if (buddy)
            Py_INCREF(buddy);
    }

    return buddy;
}

/**
 * Searches all the buddies in a Contact for a matching
 * buddy.group (or buddy.group.name) against groupname.
 *
 * Returns a Buddy*, or NULL.
 */
Buddy* bestBuddyForGroupName(Contact* contact, const wstring& groupname)
{
    wstring name(wstringToLower(groupname));
    const vector<Buddy*>& buddies = contact->buddies();
    for(vector<Buddy*>::const_iterator i = buddies.begin(); i != buddies.end(); ++i) {
        Buddy* pythonContact = *i;
        if (pythonContact->inServerGroup(name, true))
            return pythonContact;
    }

    return NULL;
}

// Determines whether to show "Groupname (4)" or "Groupname (4/5)"
static bool showSimpleGroupCount(Node* node)
{
    return node->hasFlag(FlagStatusGroup | FlagOfflineGroup | FlagSearchGroup);
}

/**
 * Returns a tree of Elem objects, without any Nodes.
 */
Elem* stripNodes(Node* node, void* onlineSet)
{
    Elem* elem = node->data();
    Group* g = 0;

    if (elem) {
        if (Group* gelem = elem->asGroup()) {
            g = gelem->copy();
            if (node->hasFlag(FlagFakeGroup)) {
                g->setGroupKey(getSpecialGroupKey(node));
            } else {
                g->setGroupKey(wstringToLower(gelem->name()));
            }
            BL_ASSERT(g);
        } else {
            Contact* c = elem->asContact();
            BL_ASSERT(c);

            if (onlineSet && c->online())
                reinterpret_cast<hash_set<wstring>*>(onlineSet)->insert(c->hash());

            Buddy* buddy = NULL;
            if (node->parent())
                buddy = bestBuddyForGroupName(c, node->parent()->name());

            if (!buddy)
                buddy = c->mostAvailableBuddy();

            BL_ASSERT(buddy);
            return buddy;
        }
    } else {
        // nodes without data() are special groups created by Groupers
        g = new Group(node->name());
        g->setGroupKey(getSpecialGroupKey(node));
    }

    if (g) {
        // We return copies of Groups
        elem = g;

        // TODO: the sorter is returning duplicates. fix this, and we won't need
        //       to use a set here.
        hash_set<wstring> onlineSet;

        Node::Vector& children = node->children();
        for(Node::VecIter i = children.begin(); i != children.end(); ++i) {
            Elem* childElem = stripNodes(*i, &onlineSet);
            BL_ASSERT(childElem);
            g->addChild(childElem);
        }

        wostringstream ss;
        if (showSimpleGroupCount(node)) {
            // For status groups, or the offline group, don't show the number of offline buddies.
            ss << node->name() << L" (" << g->numChildren() << L")";
        } else {
            ss << node->name() << L" (" << onlineSet.size()
               << L"/" << node->missing() << L")";
        }

        g->setDisplayString(ss.str());
    }

    return elem;
}
