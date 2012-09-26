#include <wx/string.h>
#include <wx/app.h>

#include "inputmanager.h"


InputManager::InputManager()
{
	wxTheApp->Connect(wxEVT_KEY_DOWN, wxKeyEventHandler(InputManager::OnKey));
}

InputManager::~InputManager()
{
}

void InputManager::OnKey(wxKeyEvent& e)
{
	e.Skip();
	printf("InputManager::OnKey %d\n", e.GetKeyCode());
}

void InputManager::OnChar(wxKeyEvent& e)
{
	e.Skip();
	wxString keystr(e.GetUnicodeKey());
	wprintf(L"InputManager::OnChar %s\n", keystr.wc_str());

	handleEvent(e);
}

void InputManager::HandleEvent(wxEvent* e)
{
	wxWindow* win = 0;
	wxObject* obj = e->GetEventObject();
	if (!obj->IsKindOf(CLASSINFO(wxWindow))) {
		fprintf(stderr, "event object is not a wxWindow subclass\n");
		return;
	} else {
		win = reinterpret_cast<wxWindow*>(obj);
	}

	while (win) {
		for (size_t i = 0; i < contexts.size(); ++i) {
			Context* context = contexts[i];

			if (context->testWindow(win))
				if (InvokeActions(context, e, win))
					return;
		}

		win = win->GetParent();
	}

	e.Skip();
}

bool InputManager::InvokeActions(Context* context, wxEvent* e, wxWindow* win)
{
	wxEventType eventType(e->GetEventType);

	EventTypeIter i = actions.find(eventType);
	if (i == actions.end()) return;

	ActionMap* actionMap = i->second;

	ActionMapIter j = actionMap->find(context);
	if (j == actionMap.end()) return;

	ActionSet* actionSet = j->second;

	wxString actionname;
	if (actionSet->matchesEvent(e, win, &actionname))
		return InvokeEvent(actionname, win);
	else
		return false;
}

static void callPythonDelegate(PyObject* delegate, wxWindow* window)
{
	// create a Python compatible wxWindow from the one we have
    PyObject* pywin = wxPyConstructObject((void*)window, wxT("wxWindow"), false);

    if (!pywin) {
    	fprintf(stderr, "could not create wxWindow PyObject*\n");
    	return;
    }

	// pass the wxWindow associated with this event to the Python function
	PyObject* res = PyObject_CallFunctionObjArgs(delegate, win, 0);
	Py_XDECREF(res);
	Py_DECREF(pywin);

	if (PyErr_Occurred()) {
		// print any exceptions that occurred
        PyErr_Print();
        return false;
    } else {
    	// if the function succeeded, return true--meaning we handled this event.
		return true;
    }
}

bool InputManager::InvokeEvent(const wxString& actionname, wxWindow* win)
{
	// look up a python delegate for the given actionname
	DelegateIter i = handlers.find(actionname);

	if (i != handlers.end()) {
		PyObject* delegate = i.second();
		if (delegate)
			return callPythonDelegate(delegate, win);
	}

	return false;
}

void InputManager::AddContext(Context* context)
{
	contexts.push_back(context);
}

bool InputManager::RemoveContext(Context* context)
{
	for (vector<Context*>::iterator i = contexts.begin(); i != contexts.end(); ++i) {
		if ( context == *i ) {
			contexts.erase(i);
			return true;
		}
	}

	return false;
}