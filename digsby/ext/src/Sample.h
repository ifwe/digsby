#ifndef EXT_Sample_h
#define EXT_Sample_h

#include <windows.h>

typedef time_t tick_t;

#define SAMPLE_VERSION 1

#pragma pack(push) // all structs in this header should be packed
#pragma pack(1)

struct SampleBase
{
    tick_t time;
};

struct Event : public SampleBase
{
    unsigned char eventId;
};

#ifdef WIN32

struct Sample : public SampleBase
{
    SIZE_T pagefileUsage;
};

#else
struct Sample : SampleBase
{
    tick_t time;
    // TODO
}
#endif // WIN32

#pragma pack(pop)



#endif
