from util.ffi import cimport
from ctypes.wintypes import DWORD, HMODULE, MAX_PATH
from ctypes import byref, WinError, sizeof, create_unicode_buffer, Structure, c_ulong
import os

SIZE_T = c_ulong

cimport(Psapi = ['GetModuleBaseNameW', 'EnumProcesses', 'EnumProcessModules', 'GetModuleBaseNameW', 'GetProcessMemoryInfo', 'EmptyWorkingSet'],
        kernel32 = ['OpenProcess', 'SetProcessWorkingSetSize', 'CloseHandle', 'GetCurrentProcess', 'GetCurrentThread', 'SetThreadPriority'],
        user32 = ['GetGuiResources'])

N = 500
dword_array = DWORD * N
aProcesses = dword_array()
cBytes = DWORD()

# constants for OpenProcess
PROCESS_QUERY_INFORMATION = 0x400
PROCESS_VM_READ           = 0x10
PROCESS_SET_QUOTA         = 0x0100

OPEN_PROCESS_FLAGS = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ

szProcessName = create_unicode_buffer(MAX_PATH)
hMod = HMODULE()
cBytesNeeded = DWORD()

class PROCESS_MEMORY_COUNTERS(Structure):
    _fields_ = [
        ("cb", DWORD),
        ("PageFaultCount", DWORD),
        ("PeakWorkingSetSize", SIZE_T),
        ("WorkingSetSize", SIZE_T),
        ("QuotaPeakPagedPoolUsage", SIZE_T),
        ("QuotaPagedPoolUsage", SIZE_T),
        ("QuotaPeakNonPagedPoolUsage", SIZE_T),
        ("QuotaNonPagedPoolUsage", SIZE_T),
        ("PagefileUsage", SIZE_T),
        ("PeakPagefileUsage", SIZE_T)
      ]

class PROCESS_MEMORY_COUNTERS_EX(Structure):
    _fields_ = [
        ("cb", DWORD),
        ("PageFaultCount", DWORD),
        ("PeakWorkingSetSize", SIZE_T),
        ("WorkingSetSize", SIZE_T),
        ("QuotaPeakPagedPoolUsage", SIZE_T),
        ("QuotaPagedPoolUsage", SIZE_T),
        ("QuotaPeakNonPagedPoolUsage", SIZE_T),
        ("QuotaNonPagedPoolUsage", SIZE_T),
        ("PagefileUsage", SIZE_T),
        ("PeakPagefileUsage", SIZE_T),
        ("PrivateUsage", SIZE_T)
      ]

def page_out_ram():
    '''
    Warning: Evil RAM hack!

    TODO: call repeatedly when taskman.exe is present >:D
    '''

    print 'paging out ram'

    hProcess = OpenProcess(PROCESS_SET_QUOTA, False, os.getpid())

    if not hProcess:
        raise WinError()

    if not SetProcessWorkingSetSize(hProcess, -1, -1):
        raise WinError()

    CloseHandle(hProcess)

def process_list():
    'Returns a list of running processes.'

    if not EnumProcesses(byref(aProcesses), N, byref(cBytes)):
        raise WinError

    processes = []
    for processID in aProcesses:
        if processID == 0: continue

        hProcess = OpenProcess(OPEN_PROCESS_FLAGS, False, processID)
        if not hProcess: continue
        try:

            if EnumProcessModules(hProcess, byref(hMod), sizeof(hMod), byref(cBytesNeeded)):
                if GetModuleBaseNameW(hProcess, hMod, szProcessName, sizeof(szProcessName) / 2):
                    processes.append(szProcessName.value)
        finally:
            CloseHandle(hProcess)

    return processes

_no_pmc_ex = False
pmc = PROCESS_MEMORY_COUNTERS_EX()

def memory_info(processID = None, p=False):
    if processID is None:
        processID = os.getpid()

    hProcess = OpenProcess(OPEN_PROCESS_FLAGS, False, processID)

    if not hProcess:
        raise WinError()

    global _no_pmc_ex
    global pmc

    if _no_pmc_ex or not GetProcessMemoryInfo(hProcess, byref(pmc), sizeof(PROCESS_MEMORY_COUNTERS_EX)):
        # windows pre-xp service pack 2 doesn't have PROCESS_MEMORY_COUNTERS_EX
        _no_pmc_ex = True
        ret = GetProcessMemoryInfo(hProcess, byref(pmc), sizeof(PROCESS_MEMORY_COUNTERS_EX))
    else:
        ret = True

    if ret:
        if p:
            print "\tPageFaultCount:             %10d" % pmc.PageFaultCount
            print "\tPeakWorkingSetSize:         %10d" % pmc.PeakWorkingSetSize
            print "\tWorkingSetSize:             %10d" % pmc.WorkingSetSize
            print "\tQuotaPeakPagedPoolUsage:    %10d" % pmc.QuotaPeakPagedPoolUsage
            print "\tQuotaPagedPoolUsage:        %10d" % pmc.QuotaPagedPoolUsage
            print "\tQuotaPeakNonPagedPoolUsage: %10d" % pmc.QuotaPeakNonPagedPoolUsage
            print "\tQuotaNonPagedPoolUsage:     %10d" % pmc.QuotaNonPagedPoolUsage
            print "\tPagefileUsage:              %10d" % pmc.PagefileUsage
            print "\tPeakPagefileUsage:          %10d" % pmc.PeakPagefileUsage
            print "\tPrivateUsage:               %10d" % pmc.PrivateUsage
    else:
        raise WinError()

    CloseHandle(hProcess);
    return pmc

def str_meminfo(pmc):
    return '\r\n'.join(filter(None, ['{',
    "\t'PageFaultCount':             %10d," % pmc.PageFaultCount,
    "\t'PeakWorkingSetSize':         %10d," % pmc.PeakWorkingSetSize,
    "\t'WorkingSetSize':             %10d," % pmc.WorkingSetSize,
    "\t'QuotaPeakPagedPoolUsage':    %10d," % pmc.QuotaPeakPagedPoolUsage,
    "\t'QuotaPagedPoolUsage':        %10d," % pmc.QuotaPagedPoolUsage,
    "\t'QuotaPeakNonPagedPoolUsage': %10d," % pmc.QuotaPeakNonPagedPoolUsage,
    "\t'QuotaNonPagedPoolUsage':     %10d," % pmc.QuotaNonPagedPoolUsage,
    "\t'PagefileUsage':              %10d," % pmc.PagefileUsage,
    "\t'PeakPagefileUsage':          %10d," % pmc.PeakPagefileUsage,
    (("\t'PrivateUsage':               %10d," % pmc.PrivateUsage)
     if isinstance(pmc, PROCESS_MEMORY_COUNTERS_EX) else ''),
     '}']))


GR_GDIOBJECTS = 0
GR_USEROBJECTS = 1
current_process_handle = GetCurrentProcess()

def count_gdi_objects():
    return GetGuiResources(current_process_handle, GR_GDIOBJECTS)

def count_user_objects():
    return GetGuiResources(current_process_handle, GR_USEROBJECTS)

THREAD_MODE_BACKGROUND_BEGIN = 0x00010000
THREAD_MODE_BACKGROUND_END = 0x00020000

THREAD_PRIORITY_ABOVE_NORMAL = 1
THREAD_PRIORITY_BELOW_NORMAL = -1
THREAD_PRIORITY_HIGHEST = 2
THREAD_PRIORITY_IDLE = -15
THREAD_PRIORITY_LOWEST = -2
THREAD_PRIORITY_NORMAL = 0
THREAD_PRIORITY_TIME_CRITICAL = 15

def set_bgthread(background = True, thread_handle = None):
    if thread_handle is None:
        thread_handle = GetCurrentThread()

    priority = THREAD_PRIORITY_IDLE if background else THREAD_PRIORITY_NORMAL

    print thread_handle, priority
    if not SetThreadPriority(thread_handle, priority):
        raise WinError()

if __name__ == '__main__':
    from time import clock
    now = clock()
    print process_list()
    print clock() - now
