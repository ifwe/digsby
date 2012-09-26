
%Include basictypes.sip

%ModuleHeaderCode
#include "talk/base/time.h"
%End

namespace talk_base {

// Returns the current time in milliseconds.
  uint32 Time();

// Approximate time when the program started.
  uint32 StartTime();

// Elapsed milliseconds since StartTime()
  uint32 ElapsedTime();

// Comparisons between time values, which can wrap around.
  bool TimeIsBetween(uint32 later, uint32 middle, uint32 earlier);
  int32 TimeDiff(uint32 later, uint32 earlier);

}; // namespace talk_base