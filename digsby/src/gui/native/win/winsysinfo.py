import os
import ctypes
from ctypes import c_ulong, c_ulonglong, c_void_p, byref, POINTER, windll
from ctypes.wintypes import DWORD, WORD

kernel32 = windll.kernel32
DWORD_PTR = POINTER(DWORD)

class SYSTEM_INFO(ctypes.Structure):
    _fields_ =[
        ('dwOemId',                     DWORD),
        ('dwPageSize',                  DWORD),
        ('lpMinimumApplicationAddress', c_void_p),
        ('lpMaximumApplicationAddress', c_void_p),
        ('dwActiveProcessorMask',       DWORD_PTR),
        ('dwNumberOfProcessors',        DWORD),
        ('dwProcessorType',             DWORD),
        ('dwAllocationGranularity',     DWORD),
        ('wProcessorLevel',             WORD),
        ('wProcessorRevision',          WORD),
    ]

class MEMORYSTATUS(ctypes.Structure):
    _fields_ = [
        ('dwLength', c_ulong),
        ('dwMemoryLoad', c_ulong),
        ('dwTotalPhys', c_ulong),
        ('dwAvailPhys', c_ulong),
        ('dwTotalPageFile', c_ulong),
        ('dwAvailPageFile', c_ulong),
        ('dwTotalVirtual', c_ulong),
        ('dwAvailVirtual', c_ulong)
    ]

DWORDLONG = c_ulonglong

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
         ('dwLength', DWORD),
         ('dwMemoryLoad', DWORD),
         ('ullTotalPhys', DWORDLONG),
         ('ullAvailPhys', DWORDLONG),
         ('ullTotalPageFile', DWORDLONG),
         ('ullAvailPageFile', DWORDLONG),
         ('ullTotalVirtual', DWORDLONG),
         ('ullAvailVirtual', DWORDLONG),
         ('ullAvailExtendedVirtual', DWORDLONG)
    ]

try:
    GetSystemInfo = kernel32.GetSystemInfo
except ImportError:
    pass
else:
    def get_num_processors():
        info = SYSTEM_INFO()
        GetSystemInfo(byref(info))
        return info.dwNumberOfProcessors

class SystemInformation(object):

    def _ram(self):
        kernel32 = ctypes.windll.kernel32

        memoryStatus = MEMORYSTATUS()
        memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUS)
        kernel32.GlobalMemoryStatus(ctypes.byref(memoryStatus))

        ret = dict((k, getattr(memoryStatus, k))
                    for k, _type in MEMORYSTATUS._fields_)
        ret.update(self._ramex())
        return ret

    def _ramex(self):
        kernel32 = ctypes.windll.kernel32

        memoryStatus = MEMORYSTATUSEX()
        memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(memoryStatus))

        return dict((k, getattr(memoryStatus, k))
                    for k, _type in MEMORYSTATUSEX._fields_)

    def _disk_c(self):
        drive = unicode(os.getenv("SystemDrive"))
        freeuser = ctypes.c_int64()
        total = ctypes.c_int64()
        free = ctypes.c_int64()
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(drive,
                                        ctypes.byref(freeuser),
                                        ctypes.byref(total),
                                        ctypes.byref(free))
        d = dict(drive=drive,
                 freeuser = freeuser.value,
                 total = total.value,
                 free  = free.value)
        return d
