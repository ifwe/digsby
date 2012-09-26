//
// inputmanager.h
//

#include <wx/window.h>
#include <wx/event.h>

#include <map>
#include <vector>
using std::vector;
using std::map;

class Context
{
public:
	virtual bool testWindow(wxWindow* window) = 0;
};

class NameContext : public Context
{
public:
	NameContext(const wxString& windowName)
		: name(windowName)
	{
	}

	virtual bool testWindow(wxWindow* window)
	{
		return window->GetName() == name;
	}

	wxString name;
};

class ClassContext : public Context
{
public:
	ClassContext(wxClassInfo* classInfo)
		: cInfo(classInfo)
	{
	}

	virtual bool testWindow(wxWindow* window)
	{
		return window->IsKindOf(cInfo);
	}

	wxClassInfo* cInfo;
};

class InputManager : public wxEvtHandler
{
public:
	InputManager();
	virtual ~InputManager();

	void OnKey(wxKeyEvent& e);
	void OnChar(wxKeyEvent& e);
	void AddContext(Context* context);
	bool RemoveContext(Context* context);

	vector<Context*> contexts;

	typedef map<Context*, ActionSet*> ActionMap;
	typedef ActionMap::iterator ActionMapIter;

	// wxEventType -> ActionMap
	typedef map<wxEventType, ActionMap> EventTypeMap;
	typedef EventTypeMap::iterator EventTypeIter;
	EventTypeMap actions;

	// wxString    -> PyObject*
	// actionnames -> callbacks
	typedef map<wxString, PyObject*> DelegateMap;
	typedef DelegateMap::iterator DelegateIter;
	DelegateMap handlers;
};
