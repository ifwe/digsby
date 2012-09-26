
class Statistics
{
%TypeHeaderCode
#include "Statistics.h"
%End

public:
    Statistics(unsigned int intervalMs = 1000 * 10);
    ~Statistics();
    bool start();
    bool stop();

    void event(SIP_PYOBJECT eventName);
%MethodCode
    char* eventName = PyString_AsString(a0);
    if (!eventName)
        sipIsErr = 1;
    else
        sipCpp->event(eventName);
%End

    SIP_PYOBJECT samples();
%MethodCode
    const SampleBuffer& b = sipCpp->samples();

    sipRes = PyList_New(b.size());
    if (!sipRes)
        sipIsErr = 1;
    else {
        size_t j = 0;
        for (SampleBuffer::const_iterator i = b.begin(); i != b.end(); ++i) {
            PyObject* tuple = Py_BuildValue("(Kn)",
                i->time,
                i->pagefileUsage);

            PyList_SetItem(sipRes, j++, tuple);
        }
    }
%End

    SIP_PYOBJECT sampleNames();
%MethodCode
        sipRes = Py_BuildValue("(ss)", "time", "pagefileUsage");
%End

    SIP_PYOBJECT events();
%MethodCode
    const EventBuffer& b = sipCpp->events();

    sipRes = PyList_New(b.size());

    if (!sipRes)
        sipIsErr = 1;
    else {
        size_t j = 0;
        for (EventBuffer::const_iterator i = b.begin(); i != b.end(); ++i) {
            if (PyList_SetItem(sipRes, j++, Py_BuildValue("(KB)", i->time, i->eventId)) == -1) {
                sipIsErr = 1;
                break;
            }
        }
    }
%End

    SIP_PYOBJECT eventNames();
%MethodCode
    const EventNameMap& map = sipCpp->eventNames();
    sipRes = PyDict_New();
    if (!sipRes)
        sipIsErr = 1;
    else {
        for (EventNameMap::const_iterator i = map.begin(); i != map.end(); ++i) {
            PyObject* key = PyString_FromStringAndSize(i->first.c_str(), i->first.size());
            PyObject* val = PyInt_FromLong(i->second);
            PyDict_SetItem(sipRes, key, val);
            Py_DECREF(key);
            Py_DECREF(val);
        }
    }
%End  

};
