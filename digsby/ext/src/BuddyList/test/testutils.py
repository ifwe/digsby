#__LICENSE_GOES_HERE__
import os

if os.name == 'nt':
    from ctypes import windll, Structure, c_size_t, byref, WinError, sizeof
    from ctypes.wintypes import HANDLE, POINTER, DWORD

    class PROCESS_MEMORY_COUNTERS(Structure):
        _fields_ = [("cb", DWORD),
                    ("PageFaultCount", DWORD),
                    ("PeakWorkingSetSize", c_size_t),
                    ("WorkingSetSize", c_size_t),
                    ("QuotaPeakPagedPoolUsage", c_size_t),
                    ("QuotaPagedPoolUsage", c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", c_size_t),
                    ("QuotaNonPagedPoolUsage", c_size_t),
                    ("PagefileUsage", c_size_t),
                    ("PeakPagefileUsage", c_size_t)]
        def __init__(self):
            self.cb = sizeof(self)

        def dump(self):
            for n, _ in self._fields_[2:]:
                print n, getattr(self, n)/1e6

    windll.psapi.GetProcessMemoryInfo.argtypes = (HANDLE, POINTER(PROCESS_MEMORY_COUNTERS), DWORD)

    def wss():
        # Return the working set size (memory used by process)
        pmi = PROCESS_MEMORY_COUNTERS()
        if not windll.psapi.GetProcessMemoryInfo(-1, byref(pmi), sizeof(pmi)):
            raise WinError()
        return pmi.WorkingSetSize

