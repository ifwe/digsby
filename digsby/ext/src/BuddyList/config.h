#ifndef BL_config_h
#define BL_config_h

#ifdef WIN32

#ifdef _DEBUG
#define _CRTDBG_MAP_ALLOC
#include <stdlib.h>
#include <crtdbg.h>
#include "dbgnew.h"
#endif

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

//
// DLL export #defines
//
#ifdef BUILDING_BUDDYLIST_DLL
#define BL_EXPORT __declspec(dllexport)
#else
#define BL_EXPORT
#endif

#define BL_ASSERT(x) do { if (!(x)) DebugBreak(); } while(0)

#else // defined(__GNUC__)
//
// DLL export #defines
//
#ifdef BUILDING_BUDDYLIST_DLL
#define BL_EXPORT  __attribute__ ((visibility("default")))
#else
#define BL_EXPORT
#endif

#define BL_ASSERT(x) do { if (!(x)) fprintf(stderr, "ASSERT: Assert failed at: %s:%d\n", __FILE__, __LINE__); } while(0)
#endif

#define BL_ASSERT_NOT_REACHABLE(x) BL_ASSERT(0); return (x);

#ifdef BUILDING_BUDDYLIST_DLL
#define foreach         BOOST_FOREACH
#include <boost/foreach.hpp>
#endif

#if 0

#include <hash_set>
using stdext::hash_set;

#define TRACK_ALLOC_CLASS(T) \
    static unsigned int ms_instanceCount; \
    __declspec(noinline) static size_t instanceCount();

#define TRACK_ALLOC_IMPL(T) \
    unsigned int T::ms_instanceCount; \
    __declspec(noinline) size_t T::instanceCount() { return ms_instanceCount; }

#define TRACK_ALLOC() ms_instanceCount++;
#define TRACK_DEALLOC() ms_instanceCount--;

#else // BLIST_TRACK_ALLOCS

#define TRACK_ALLOC_CLASS(T)
#define TRACK_ALLOC_IMPL(T)
#define TRACK_ALLOC()
#define TRACK_DEALLOC()

#endif // BLIST_TRACK_ALLOCS


#endif
