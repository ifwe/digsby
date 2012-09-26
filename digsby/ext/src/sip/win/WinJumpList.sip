%ModuleHeaderCode
#include "WinJumpList.h"
%End

%ModuleHeaderCode
bool pyGetTask(JumpListTask& task, PyObject* elem);
%End

%ModuleCode
bool pyGetTask(PyObject* elem, JumpListTask& task)
{
    if (elem == Py_None)
        return true; // an empty task is a separator; from Python None means separator

    PyObject* seq = PySequence_Fast(elem, "elements of jump list must be sequences");
    if (!seq)
        return false;

    wchar_t* args;
    wchar_t* description;
    wchar_t* title;
    wxBitmap* bitmap = 0;

    int state = 0;
    if (sipParseResult(NULL, NULL, seq, "(xxxD0)", &args, &description, &title, sipType_wxBitmap, &state, &bitmap)) {
        Py_DECREF(seq);
        return false;
    }

    task.bitmap = bitmap ? *bitmap : wxNullBitmap;

    if (bitmap)
        sipReleaseType(bitmap, sipType_wxBitmap, state);

    task.args = args;
    task.description = description;
    task.title = title;

    Py_DECREF(seq);
    return true;
}

static bool getTasksFromSeq(vector<JumpListTask>& tasks, PyObject* a1)
{
    PyObject* seq = PySequence_Fast(a1, "arguments to SetUpJumpList must be sequences");
    if (!seq)
        return false;

    bool success = true;

    const Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
    PyObject** elems = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < n; ++i) {
        PyObject* elem = *elems++;

        JumpListTask task;
        if (!pyGetTask(elem, task)) {
            success = false;
            break;
        }
        tasks.push_back(task);
    }

    Py_DECREF(seq);
    return success;
}

static bool getTaskGroup(JumpListTaskGroup& group, PyObject* taskGroup)
{
    Py_UNICODE* category;
    PyObject* tasksSeq;
    if (!PyArg_ParseTuple(taskGroup, "uO", &category, &tasksSeq))
        return false;

    if (!getTasksFromSeq(group.tasks, tasksSeq))
        return false;

    group.category = category;
    return true;
}

%End

bool SetUpJumpList(const wchar_t* appID, SIP_PYOBJECT);
%MethodCode
    PyObject* seq = PySequence_Fast(a1, "arguments to SetUpJumpList must be sequences");
    if (!seq)
        sipIsErr = 1;
    else {
        const Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
        PyObject** elems = PySequence_Fast_ITEMS(seq);

        TaskGroupVector groups;
        for (Py_ssize_t i = 0; i < n; ++i) {
            JumpListTaskGroup group;
            if (!getTaskGroup(group, *elems++)) {
                sipIsErr = 1;
                break;
            }
            groups.push_back(group);
        }

        Py_DECREF(seq);

        if (!sipIsErr)
            sipRes = SetUpJumpList(a0, groups);
    }
%End

