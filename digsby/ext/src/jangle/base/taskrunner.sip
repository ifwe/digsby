
%Include basictypes.sip

namespace talk_base {

%TypeHeaderCode
#include "talk/base/sigslot.h"
#include "talk/base/taskrunner.h"
%End

const int64 kSecToMsec;
const int64 kMsecTo100ns;
const int64 kSecTo100ns;

class TaskRunner : talk_base::Task {
 public:
  TaskRunner();
  virtual ~TaskRunner();

  virtual void WakeTasks() = 0;

  // This method returns the current time in 100ns units since 1/1/1601.  This
  // Is the GetSystemTimeAsFileTime method on windows.
  virtual int64 CurrentTime() = 0 ;

  void StartTask(talk_base::Task *task);
  void RunTasks();
  void PollTasks();

  void UpdateTaskTimeout(talk_base::Task *task);

  // dummy state machine - never run.
  virtual int ProcessStart();

};

};