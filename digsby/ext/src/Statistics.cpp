#include "Statistics.h"

#include "Noncopyable.h"
#include "RingBuffer.h"
#include "Sample.h"

#include <string>
#include <wx/timer.h>

// todo: BOOST_NO_EXCEPTIONS wasn't working, why?
namespace boost{ template<class E> void throw_exception(E const & e) { throw e; } }
#include <boost/circular_buffer.hpp>

static inline void recordTime(SampleBase& sample)
{
    time(&sample.time);
}

#define SAMPLE_BUFFER_SIZE_BYTES 300 * 1024
#define SAMPLE_BUFFER_SIZE_ELEMS SAMPLE_BUFFER_SIZE_BYTES / sizeof(Sample)

#define EVENT_BUFFER_SIZE_BYTES 100 * 1024
#define EVENT_BUFFER_SIZE_ELEMS EVENT_BUFFER_SIZE_BYTES / sizeof(Event)

typedef unsigned char StatsEventId;

class StatsImplBase : Noncopyable
{
public:

    StatsImplBase()
        : m_nextEventId(0)
        , m_samples(SAMPLE_BUFFER_SIZE_ELEMS)
        , m_events(EVENT_BUFFER_SIZE_ELEMS)
    {}

    ~StatsImplBase() {}

    const SampleBuffer& samples() const { return m_samples; }
    const EventBuffer& events() const { return m_events; }
    const EventNameMap& eventNames() const { return m_eventNames; }

    void event(const char* eventName)
    {
        event(eventIdForName(eventName));
    }

    void event(StatsEventId eventId)
    {
        Event event;
        recordTime(event);
        event.eventId = eventId;

        wxMutexLocker locker(m_eventsMutex);
        m_events.push_back(event);
    }

    StatsEventId eventIdForName(const char* eventName)
    {
        wxMutexLocker locker(m_eventNamesMutex);
        EventNameMap::iterator i = m_eventNames.find(std::string(eventName));
        if (i != m_eventNames.end())
            return i->second;

        StatsEventId eventId = m_nextEventId++;
        m_eventNames[eventName] = eventId;
        return eventId;
    }

protected:

    SampleBuffer m_samples;
    EventBuffer m_events;

    wxMutex m_eventsMutex;
    wxMutex m_eventNamesMutex;

    EventNameMap m_eventNames;
    StatsEventId m_nextEventId;
};

#ifdef WIN32
typedef struct {
  DWORD  cb;
  DWORD  PageFaultCount;
  SIZE_T PeakWorkingSetSize;
  SIZE_T WorkingSetSize;
  SIZE_T QuotaPeakPagedPoolUsage;
  SIZE_T QuotaPagedPoolUsage;
  SIZE_T QuotaPeakNonPagedPoolUsage;
  SIZE_T QuotaNonPagedPoolUsage;
  SIZE_T PagefileUsage;
  SIZE_T PeakPagefileUsage;
} PROCESS_MEMORY_COUNTERS;

typedef BOOL (WINAPI *GetProcessMemoryInfo_t) (HANDLE, PROCESS_MEMORY_COUNTERS*, DWORD);
static GetProcessMemoryInfo_t GetProcessMemoryInfo = (GetProcessMemoryInfo_t)-1;

static inline void loadSymbols()
{
    if (GetProcessMemoryInfo == (GetProcessMemoryInfo_t)-1) {
        GetProcessMemoryInfo = 0;
        if (HMODULE dll = ::LoadLibrary(L"psapi.dll"))
            GetProcessMemoryInfo = (GetProcessMemoryInfo_t)::GetProcAddress(dll, "GetProcessMemoryInfo");
    }
}

#ifndef NDEBUG
static void printPMC(const PROCESS_MEMORY_COUNTERS& pmc)
{
    printf( "\tPageFaultCount: 0x%08X\n", pmc.PageFaultCount );
    printf( "\tPeakWorkingSetSize: 0x%08X\n", 
              pmc.PeakWorkingSetSize );
    printf( "\tWorkingSetSize: 0x%08X\n", pmc.WorkingSetSize );
    printf( "\tQuotaPeakPagedPoolUsage: 0x%08X\n", 
              pmc.QuotaPeakPagedPoolUsage );
    printf( "\tQuotaPagedPoolUsage: 0x%08X\n", 
              pmc.QuotaPagedPoolUsage );
    printf( "\tQuotaPeakNonPagedPoolUsage: 0x%08X\n", 
              pmc.QuotaPeakNonPagedPoolUsage );
    printf( "\tQuotaNonPagedPoolUsage: 0x%08X\n", 
              pmc.QuotaNonPagedPoolUsage );
    printf( "\tPagefileUsage: 0x%08X\n", pmc.PagefileUsage ); 
    printf( "\tPeakPagefileUsage: 0x%08X\n", 
              pmc.PeakPagefileUsage );
}
#endif

class StatsImpl : public StatsImplBase
{
public:
    StatsImpl()
        : m_hProcess(0)
        , m_errorOpeningProcess(false)
    {}

    ~StatsImpl()
    {
        if (m_hProcess)
            ::CloseHandle(m_hProcess);
    }

    void measure()
    {
        Sample sample;
        recordTime(sample);
        measureMemoryUsage(sample);
        m_samples.push_back(sample);
    }

    bool measureMemoryUsage(Sample& sample)
    {
        PROCESS_MEMORY_COUNTERS pmc;

        bool success = false;
        loadSymbols();        
        if (openProcess() && GetProcessMemoryInfo) {
            success = GetProcessMemoryInfo(m_hProcess, &pmc, sizeof(pmc)) == TRUE;
            if (success)
                sample.pagefileUsage = pmc.PagefileUsage;
        }

        return success;
    }

protected:
    bool openProcess()
    {
        if (m_hProcess)
            return true;

        if (m_errorOpeningProcess)
            return false;

        m_hProcess = ::OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, ::GetCurrentProcessId());
        if (!m_hProcess) {
            m_errorOpeningProcess = true;
            return false;
        }

        return true;
    }

    HANDLE m_hProcess;
    bool m_errorOpeningProcess;
};
#else
class StatsImpl : StatsImplBase
{
    // TODO
public:
    StatsImpl() {}
    ~StatsImpl() {}
    void measure() {}
};
#endif

class StatisticsTimer : public wxTimer
{
public:
    StatisticsTimer(Statistics* stats)
        : m_stats(stats)
    {}

    virtual void Notify()
    {
        if (m_stats)
            m_stats->timerFired();
    }

    virtual void Stop()
    {
        m_stats = 0;
        wxTimer::Stop();
    }

protected:
    Statistics* m_stats;
};

Statistics::Statistics(unsigned int intervalMs)
    : m_timer(new StatisticsTimer(this))
    , m_interval(intervalMs)
    , m_impl(new StatsImpl())
{
}

Statistics::~Statistics()
{
    m_timer->Stop();
    delete m_timer;
    m_timer = 0;

    delete m_impl;
}

const SampleBuffer& Statistics::samples() const
{
    return m_impl->samples();
}

const EventBuffer& Statistics::events() const
{
    return m_impl->events();
}

const EventNameMap& Statistics::eventNames() const
{
    return m_impl->eventNames();
}

bool Statistics::start()
{
    if (!m_timer->IsRunning()) {
        timerFired();
        m_timer->Start(m_interval);
        return true;
    } else
        return false;
}

bool Statistics::stop()
{
    bool wasRunning = m_timer->IsRunning();
    m_timer->Stop();
    return wasRunning;
}

void Statistics::timerFired()
{
    m_impl->measure();
}

void Statistics::event(const char* eventName)
{
    m_impl->event(eventName);
}


