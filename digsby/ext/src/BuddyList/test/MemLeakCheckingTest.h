#ifndef MemLeakCheckingTest_h
#define MemLeakCheckingTest_h

#include <gtest/gtest.h>

#if defined(WIN32) && defined(_DEBUG)

// Used to redirect _CrtXXX functions output to stderr, instead of the MSVC
// trace window.
int __cdecl crtReportHook(int reportType, char *szMsg, int *retVal)
{
    (*retVal) = reportType == _CRT_ASSERT;
    fprintf(stderr, "%s", szMsg);
    return 1;
}

// Implements a SetUp/TearDown pair that uses MSVC's _CrtMemCheckpoint and
// related functions to check each test for memory leaks individually.
//
// Leaks are test failures.
class Win32MemLeakCheckingTest : public testing::Test
{
protected:
    virtual ~Win32MemLeakCheckingTest() {}

    static void SetUpTestCase()
    {
        // Install our report hook, so that heap debugging info goes to stderr.
        _CrtSetReportHook2(_CRT_RPTHOOK_INSTALL, &crtReportHook);
    }

    static void TearDownTestCase()
    {
        _CrtSetReportHook2(_CRT_RPTHOOK_REMOVE, &crtReportHook);
    }

    virtual void SetUp()
    {
        // Save the state of the CRT heap.
        _CrtMemCheckpoint(&m_startState);
    }

    virtual void TearDown()
    {
        // Ensure the heap wasn't corrupted.
        ASSERT_TRUE(_CrtCheckMemory());

        if (!HasFatalFailure()) {
            // Ensure there were no memory leaks.
            _CrtMemState endState, diff;
            _CrtMemCheckpoint(&endState);
            if (_CrtMemDifference(&diff, &m_startState, &endState)) {
                _CrtMemDumpAllObjectsSince(&diff);
                _CrtMemDumpStatistics(&diff);
                FAIL() << "Memory leak.";
            }
        }
    }

    _CrtMemState m_startState;
};

#endif

#endif
