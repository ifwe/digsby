
%Include basictypes.sip

namespace talk_base {

class Task /Abstract/ {

%TypeHeaderCode
#include "talk/base/sigslot.h"
#include "talk/base/task.h"
%End

 private:
  Task(const talk_base::Task &);
  Task();

 public:
  Task(talk_base::Task *parent /TransferThis/);

  int32 get_unique_id();

  void Start();
  void Step();
  int GetState() const;
  bool HasError() const;
  bool Blocked() const;
  bool IsDone() const;
  int64 ElapsedTime();

  talk_base::Task *GetParent();
  talk_base::TaskRunner *GetRunner();
  virtual talk_base::Task *GetParent(int code);

  // Called from outside to stop task without any more callbacks
  void Abort(bool nowake = false);

  // For managing children
  bool AllChildrenDone();
  bool AnyChildError();

  bool TimedOut();

  int64 get_timeout_time();
  void set_timeout_seconds(int timeout_seconds);

//  sigslot::signal0<> SignalTimeout;

  // Called inside the task to signal that the task may be unblocked
  void Wake();

};

};