namespace buzz {

/////////////////////////////////////////////////////////////////////
//
// RATELIMITMANAGER
//
/////////////////////////////////////////////////////////////////////
//
// RateLimitManager imposes client-side rate limiting for xmpp tasks and
// other events.  It ensures that no more than i events with a given name
// can occur within k seconds.
//
// A buffer tracks the previous max_count events.  Before an event is allowed
// to occur, it can check its rate limit with a call to VerifyRateLimit.
// VerifyRateLimit will look up the i-th to last event and if more than
// k seconds have passed since then, it will return true and update the
// appropriate rate limits.  Else, it will return false.
//
/////////////////////////////////////////////////////////////////////

class RateLimitManager {

%TypeHeaderCode
#include "talk/xmpp/ratelimitmanager.h"
%End

 public:

  RateLimitManager();
  ~RateLimitManager();

  // Checks if the event is under the defined rate limit and updates the
  // rate limit if so.  Returns true if it's under the rate limit.
  bool VerifyRateLimit(const std::string event_name, int max_count,
                       int per_x_seconds);

  // Checks if the event is under the defined rate limit and updates the
  // rate limit if so *or* if always_update = true.
  bool VerifyRateLimit(const std::string event_name, int max_count,
                       int per_x_seconds, bool always_update);

 private:

/*
  class RateLimit {
   public:
    RateLimit(int max, int per_x_secs) : counter_(0), max_count_(max),
                                         per_x_seconds_(per_x_secs) {
      event_times_ = new uint32[max_count_];
      for (int i = 0; i < max_count_; i++) {
        event_times_[i] = 0;
      }
    }

    ~RateLimit() {
      if (event_times_) {
        delete[] event_times_;
      }
    }

    // True iff the current time >= to the next song allowed time
    bool IsWithinRateLimit();

    // Updates time and counter for rate limit
    void UpdateRateLimit();

   private:

    // The time at which the i-th (where i = max_count) event occured
    uint32 PreviousTimeAtCounter();

    // The time that the next event is allowed to occur
    uint32 NextTimeAllowedForCounter();

    int counter_; // count modulo max_count of the current event
    int max_count_; // max number of events that can occur within per_x_seconds
    int per_x_seconds_; // interval size for rate limit
    uint32* event_times_; // buffer of previous max_count event
*/
  };
/*
  typedef std::map<const std::string, RateLimit*> RateLimitMap;

  // Maps from event name to its rate limit
  RateLimitMap rate_limits_;
  // Returns rate limit for event with specified name
  buzz::RateLimit* GetRateLimit(const std::string event_name);

  // True iff the current time >= to the next song allowed time
  bool IsWithinRateLimit(const std::string event_name);

  // Updates time and counter for rate limit
  void UpdateRateLimit(const std::string event_name, int max_count,
                       int per_x_seconds);
*/

//};

};