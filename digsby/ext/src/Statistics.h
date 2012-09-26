#ifndef _CGUI_STATISTICS_H_
#define _CGUI_STATISTICS_H_

#include "Sample.h"

// todo: BOOST_NO_EXCEPTIONS wasn't working, why?
namespace boost{ template<class E> void throw_exception(E const & e); }
#include <boost/circular_buffer.hpp>

#include <hash_map>
using stdext::hash_map;

typedef boost::circular_buffer<Sample> SampleBuffer;
typedef boost::circular_buffer<Event> EventBuffer;
typedef hash_map<std::string, unsigned char> EventNameMap;


class StatsImpl;
class StatisticsTimer;

class Statistics
{
public:
    Statistics(unsigned int intervalMs = 1000 * 10);
    ~Statistics();
    void timerFired();

    void event(const char* eventName);

    bool start();
    bool stop();

    const SampleBuffer& samples() const;
    const EventBuffer& events() const;
    const EventNameMap& eventNames() const;

protected:
    StatsImpl* m_impl;
    StatisticsTimer* m_timer;
    unsigned int m_interval;
};

#endif // _CGUI_STATISTICS_H_

