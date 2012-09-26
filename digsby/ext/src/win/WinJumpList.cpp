#include <comip.h>

#include <shobjidl.h>
#include <uxtheme.h>
#include <propvarutil.h>
#include <propkey.h>
#include <wchar.h>

#include <vector>
using std::vector;

#ifdef __GNUC__
#include <ext/hash_map>
#else
#include <hash_map>
#endif
using stdext::hash_map;

#include <wx/wx.h>
#include <wx/stdpaths.h>

typedef hash_map<wxObjectRefData*, wxString> IconCache;

#include "WinJumpList.h"
#include "IconUtils.h"

typedef _com_ptr_t<_com_IIID<IObjectArray,&IID_IObjectArray>>  ObjArrPtr;
typedef _com_ptr_t<_com_IIID<IShellLinkW, &IID_IShellLinkW>>   IShellLinkWPtr;
typedef _com_ptr_t<_com_IIID<ICustomDestinationList, &IID_ICustomDestinationList>> ICustomDestinationListPtr;
typedef _com_ptr_t<_com_IIID<IObjectCollection, &IID_IObjectCollection>> IObjectCollectionPtr;
typedef _com_ptr_t<_com_IIID<IPropertyStore, &IID_IPropertyStore>> IPropertyStorePtr;

static bool addBitmap(const wxBitmap& bitmap, IShellLinkWPtr& link, IconCache& iconCache)
{
    // Jump list icons must be files on disk or resources in executables, so
    // save out the bitmap to a temporary location.
    if (bitmap.IsOk()) {
        wxString filename;

        IconCache::iterator i = iconCache.find(bitmap.GetRefData());
        if (i != iconCache.end())
            filename = i->second;
        else {
            if (!tempImageFile(wxStandardPaths::Get().GetTempDir() + L"\\digsby_jumplist",
                               wxString::Format(L"_icon_%d.bmp", iconCache.size()), 
                               bitmap, filename, wxBITMAP_TYPE_ICO))
                return false;
        }

        iconCache[bitmap.GetRefData()] = filename;
        if (FAILED(link->SetIconLocation(filename, 0)))
            return false;
    }

    return true;
}

// returns true if removedItems has an IShellLink object with the same value for
// GetArguments as given by "arguments"
bool itemInArray(const wstring& arguments, const ObjArrPtr& removedItems)
{
    if (arguments.size() == 0)
        return false;

    size_t n;
    if (FAILED(removedItems->GetCount(&n)))
        return false;

    for (size_t i = 0; i < n; ++i) {
        IShellLinkWPtr removedLink;
        if (FAILED(removedItems->GetAt(i, IID_PPV_ARGS(&removedLink))))
            return false;

        wchar_t s[MAX_PATH+1];
        removedLink->GetArguments(&s[0], MAX_PATH);
        if (arguments == s)
            return true;
    }

    return false;
}

static bool isSeparator(const JumpListTask& task)
{
    return task.args.empty() && task.description.empty() && task.title.empty();
}

static bool AddJumpListSeparator(IObjectCollection* objColl)
{
    // Create a shell link COM object.
    HRESULT hr;
    IShellLinkWPtr link;

    if (FAILED(hr = link.CreateInstance(CLSID_ShellLink, NULL, CLSCTX_INPROC_SERVER)))
        return false;

    // Get an IPropertyStore interface.
    IPropertyStorePtr propStore = link;
    PROPVARIANT pv;

    if (!propStore || FAILED(hr = InitPropVariantFromBoolean(TRUE, &pv)))
        return false;

    // Set the property that makes the task a separator.
    hr = propStore->SetValue(PKEY_AppUserModel_IsDestListSeparator, pv);
    PropVariantClear(&pv);
    if (FAILED(hr))
        return false;

    // Save the property changes.
    if (FAILED(propStore->Commit()))
        return false;

    // Add this shell link to the object collection.
    return SUCCEEDED(objColl->AddObject(link));
}

bool AddJumpListTask(IObjectCollection* objColl, const JumpListTask& task, LPCTSTR exePath, IconCache& iconCache, const ObjArrPtr& removedItems)
{
    if (isSeparator(task))
        return AddJumpListSeparator(objColl);

    // Create a shell link COM object.
    IShellLinkWPtr link;

    if (FAILED(link.CreateInstance(CLSID_ShellLink, NULL, CLSCTX_INPROC_SERVER)))
        return false;

    // Set the executable path
    if (FAILED(link->SetPath(exePath)))
        return false;

    if (FAILED(link->SetShowCmd(SW_SHOWMINNOACTIVE)))
        return false;

    // Set the arguments
    if (FAILED(link->SetArguments(task.args.c_str())))
        return false;

    if (!addBitmap(task.bitmap, link, iconCache))
        return false;

    // Set the working directory
    wchar_t workingDir[MAX_PATH];
    if (!_wgetcwd(workingDir, MAX_PATH))
        return false;

    if (FAILED(link->SetWorkingDirectory(workingDir)))
        return false;

    // Set the link description (tooltip on the jump list item)
    if (FAILED(link->SetDescription(task.description.c_str())))
        return false;

    // Set the link title (the text of the jump list item). This is kept in the
    // object's property store, so QI for that interface.
    IPropertyStorePtr propStore = link;
    PROPVARIANT pv;

    if (!propStore)
        return false;

    if (FAILED(InitPropVariantFromString(task.title.c_str(), &pv)))
        return false;

    // Set the title property.
    HRESULT hr = propStore->SetValue(PKEY_Title, pv);
    PropVariantClear(&pv);
    if (FAILED(hr))
        return false;

    // Save the property changes.
    if (FAILED(propStore->Commit()))
        return false;

    // Don't add items disallowed by Windows via the removedItems list
    if (itemInArray(task.args, removedItems))
        return true;

    // Add this shell link to the object collection.
    return SUCCEEDED(objColl->AddObject(link));
}

bool AddJumpListTasks(IObjectCollection* objColl, const vector<JumpListTask>& tasks, const ObjArrPtr& removedItems)
{
    // Get the path to the EXE, which we use as the path and icon path for each jump list task.
    TCHAR exePath[MAX_PATH];
    GetModuleFileName(NULL, exePath, _countof(exePath));

    IconCache iconCache;

    for (vector<JumpListTask>::const_iterator i = tasks.begin();
         i != tasks.end(); ++i) {
        // Add the next task to the object collection.
        if (!AddJumpListTask(objColl, *i, exePath, iconCache, removedItems))
            return false;
    }

    return true;
}

static bool AddTaskGroup(ICustomDestinationListPtr& destList, const vector<JumpListTask>& tasks, const wxString& category, const ObjArrPtr& removedItems)
{
    if (!tasks.size())
        return true;

    // Create an object collection to hold the custom tasks.
    IObjectCollectionPtr objColl;
    if (FAILED(objColl.CreateInstance(CLSID_EnumerableObjectCollection, NULL, CLSCTX_INPROC_SERVER)))
        return false;

    // Add our custom tasks to the collection.
    if (!AddJumpListTasks(objColl, tasks, removedItems))
        return false;

    // Get an IObjectArray interface for AddUserTasks.
    ObjArrPtr tasksArray = objColl;
    if (!tasksArray)
        return false;

    // Add the tasks to the jump list.
    if (category.size()) {
        if (FAILED(destList->AppendCategory(category, tasksArray)))
            return false;
    } else {
        if (FAILED(destList->AddUserTasks(tasksArray)))
            return false;
    }

    return true;
}

bool SetUpJumpList(LPCWSTR appID, const vector<JumpListTaskGroup>& taskGroups)
{
    ICustomDestinationListPtr destList;

    // Create a jump list COM object.
    if (FAILED(destList.CreateInstance(CLSID_DestinationList, NULL, CLSCTX_INPROC_SERVER )))
        return false;

    // Tell the jump list our AppID.
    if (FAILED(destList->SetAppID(appID)))
        return false;

    // Create a new, empty jump list. We aren't adding custom destinations,
    // so cMaxSlots and removedItems aren't used.
    UINT cMaxSlots;
    ObjArrPtr removedItems;

    if (FAILED(destList->BeginList(&cMaxSlots, IID_PPV_ARGS(&removedItems))))
        return false;

    for (vector<JumpListTaskGroup>::const_iterator i = taskGroups.begin();
         i != taskGroups.end();
         ++i) {

        const JumpListTaskGroup& taskGroup = *i;
        AddTaskGroup(destList, taskGroup.tasks, taskGroup.category, removedItems);
    }

    // Save the jump list.
    return SUCCEEDED(destList->CommitList());
}

