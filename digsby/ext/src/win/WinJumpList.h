#include <windows.h>
#include <wx/bitmap.h>
#include <string>
#include <vector>
using std::wstring;
using std::vector;

struct JumpListTask
{
    wstring args, description, title;
    wxBitmap bitmap;
};

struct JumpListTaskGroup
{
    wstring category; // may be empty
    vector<JumpListTask> tasks;
};

typedef vector<JumpListTaskGroup> TaskGroupVector;

bool SetUpJumpList(LPCWSTR appID, const TaskGroupVector& taskGroups);


