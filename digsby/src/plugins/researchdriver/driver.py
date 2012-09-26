from __future__ import with_statement
from fileutil import cd
from path import path
from subprocess import Popen, PIPE
from threading import RLock
from util import default_timer
import ctypes
import logging
import os
import time
import traceback
import sys

log = logging.getLogger('research')
#if __debug__:
#    def info_s(foo, *bar):
#        try:
#            print foo % bar
#        except Exception:
#            pass
#    log.info = info_s

DEFAULT_IDLE_MINUTES = 5
DEFAULT_REVIVE_INTERVAL = 60 * 60

def REVIVE_INTERVAL():
    from common import pref
    return pref('research.revive_interval_seconds', default=DEFAULT_REVIVE_INTERVAL, type=int)

def MAX_PERCENT():
    '''
    cpu max
    hard limit for chassis type.  don't change unless we're increasing the real max.
    '''
    return .75
#current setting, this is the one to change, will be limited by max
DEFAULT_CPU_PERCENT   = .75
DEFAULT_BANDWIDTH_PERCENT   = .90

STARTED = True
FAILED_TO_START = False
ALREADY_RUNNING = 'ALREADY_RUNNING'

KEY_WOW64_64KEY = 0x0100

DEBUG_PLURA = False #I'm not using sys.DEV, because I don't want the difference in behavior right now.

KIBIBYTE = 2**10
MEBIBYTE = 2**20
GIBIBYTE = 2**30

PERMGEN_SPACE = 32 * MEBIBYTE

MEMORY_LIMIT_BUFFER = 1.2

def expected_memory(size):
    return (size + PERMGEN_SPACE) * MEMORY_LIMIT_BUFFER

def find_java_home():
    k = k2 = None
    # on Mac / Linux, it's usually either in /usr/bin or set by an env. variable.
    if not sys.platform.startswith('win'):
        if "JAVA_HOME" in os.environ:
            path = os.environ['JAVA_HOME']
            if os.path.exists(path):
                return path
        else:
            return "/usr"

    try:
        try:
            import _winreg
        except ImportError: #will want mac/linux impl.
            return False
        try:
            try:
                k = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Runtime Environment\\", 0, _winreg.KEY_READ | KEY_WOW64_64KEY)
            except Exception:
                #KEY_WOW64_64KEY not allowed on Windows 2000
                k = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Runtime Environment\\", 0, _winreg.KEY_READ)
            ver, tp = _winreg.QueryValueEx(k, 'CurrentVersion')
        except Exception:
            return False
        if tp != _winreg.REG_SZ:
            return False
        try:
            if float(ver[:3]) <= 1.5:
                return False
        except ValueError:
            return False
        try:
            k2 = _winreg.OpenKey(k, ver, 0, _winreg.KEY_READ)
            java_home, tp = _winreg.QueryValueEx(k2, 'JavaHome')
        except Exception:
            return False
        if tp != _winreg.REG_SZ:
            return False
        return java_home
    finally:
        if k2 is not None:
            k2.Close()
        if k is not None:
            k.Close()

def java_exe(java_home):
    def exe(filename):
        if sys.platform.startswith('win'):
            return filename + '.exe'
        return filename

    java = path(java_home) / 'bin' / exe('java')
    javaw = path(java_home) / 'bin' / exe('javaw')
    if javaw.isfile():
        return javaw
    return java

IDLE_PRIORITY_CLASS = 0x00000040

class Driver(object):
    profile  = None
    instance = None
    lock     = RLock()
    numstarts = 0
    numfounddead = 0
    dead_at = 0
    dead = False

    def __init__(self):
        assert False

    @classmethod
    def res_path(cls):
        pth = path(__file__).parent
        return pth / 'res'

    @classmethod
    def jar_path(cls):
        return cls.res_path() / 'process.jar'

    @classmethod
    def jar2_path(cls):
        return cls.res_path() / 'security.jar'

    @classmethod
    def policy_path(cls):
        return cls.res_path() / 'java.policy'

    @classmethod
    def java_path(cls):
        return java_exe(find_java_home())

    @classmethod
    def username(cls):
        uname = getattr(getattr(cls, 'profile', None), 'username', None)
        if uname:
            from util.primitives.strings import to_hex, string_xor
            uname = to_hex(string_xor(x='digsbygrid', y=uname.encode('utf-8'), adjustx=True), '')
            return ['-u', uname]
        return []

    @classmethod
    def chassis_desired_cpuUsage(cls):
        try:
            chassis_types = getattr(cls, 'chassis_types', None)

            if chassis_types is None:
                if sys.platform.startswith('win'):
                    import comtypes.client
                    wmi = comtypes.client.CoGetObject("winmgmts:")
                    encs = wmi.InstancesOf("Win32_SystemEnclosure")
                    enc = list(encs)[0]
                    cls.chassis_types = chassis_types = enc.Properties_(strName='ChassisTypes').Value
                    log.info('chassis types (success): %r', cls.chassis_types)
                else:
                    log.warning('hardcoding chassis type for this platform')
                    cls.chassis_types = chassis_types = [2]

            from engine import rpm
            speeds = [rpm.get(chassis, DEFAULT_CPU_PERCENT) for chassis in chassis_types] + [MAX_PERCENT()]
            lowest = min(speeds)
            return lowest if lowest != sys.maxint else min(DEFAULT_CPU_PERCENT, MAX_PERCENT())
        except Exception:
            traceback.print_exc()
            cls.chassis_types = [2] # don't do the comtypes lookup more than once.
            # 2 == unknown

            log.info('chassis types (fail): %r', cls.chassis_types)
            return min(DEFAULT_CPU_PERCENT, MAX_PERCENT())

    @classmethod
    def cpuUsage(cls):
        default = cls.chassis_desired_cpuUsage()
        try:
            return get_cpu_percent(default) / 100.0
        except ImportError: #lets this run unit tests
            assert __name__ == '__main__'
        return default

    @classmethod
    def cpuUsageStr(cls):
        return ['-p', str(int(cls.cpuUsage()*1000))]

    @classmethod
    def numCpus(cls):
        return [] #['-n', '1']

    @classmethod
    def bandwidthUsage(cls):
        default = DEFAULT_BANDWIDTH_PERCENT * 100
        try:
            from common import pref
            percent = pref('research.bandwidth_percent', default, type=float)
            if percent >= 0 and percent <= 100:
                percent = percent / 100.0
            if percent >= 0:
                return percent
        except ImportError: #lets this run unit tests
            assert __name__ == '__main__'
        return default

    @classmethod
    def bandwidthUsageStr(cls):
        return ['-b', str(int(cls.bandwidthUsage()*1000))]

    @classmethod
    def memoryLimits(cls):
        if not sys.platform.startswith('win'):
            #assume, for now, that mac/linux have plenty of RAM
            return ['-Xmx512m']
        try:
            import gui.native.sysinfo
            s = gui.native.sysinfo.SystemInformation()
            ram = s._ram()
        except Exception:
            return ['-Xmx256m']
        else:
            AvailPhys = ram.get('ullAvailPhys')
            TotalPhys = ram.get('ullTotalPhys')
            #TODO: make this a table
#            return ['-Xmx' + str(int((.75 * AvailPhys) / MEBIBYTE)) + 'm']
#            if AvailPhys >= expected_memory(2 * GIBIBYTE) and TotalPhys >= (3 * GIBIBYTE):
#                return ['-Xmx2048m']
            if AvailPhys >= expected_memory(GIBIBYTE) and TotalPhys >= (2 * GIBIBYTE):
                return ['-Xmx1024m']
            elif AvailPhys >= expected_memory(512 * MEBIBYTE) and TotalPhys >= (GIBIBYTE):
                return ['-Xmx512m']
            elif AvailPhys >= expected_memory(256 * MEBIBYTE):
                return ['-Xmx256m']
            elif TotalPhys >= (GIBIBYTE):
                return ['-Xmx256m']
            else:
                #if you don't have this much free RAM, how do you manage to run digsby?
                return ['-Xmx128m']

    @classmethod
    def commandline(cls):
        return [str(cls.java_path()), '-Djava.security.manager=com.pluraprocessing.node.security.PluraSecurityManager',
                '-Djava.security.policy='+str(cls.policy_path())+''] + \
                cls.memoryLimits() + \
                ['-jar', str(cls.jar_path())] + cls.username() + cls.cpuUsageStr() + cls.bandwidthUsageStr()

    @classmethod
    def running(cls):
        with cls.lock:
            proc = getattr(cls, 'proc', None)
            return proc is not None and proc.poll() is None

    @classmethod
    def set_dead(cls):
        cls.dead = True
        cls.dead_at = default_timer()

    @classmethod
    def is_dead(cls):
        if cls.dead:
            revive_at = cls.dead_at + REVIVE_INTERVAL()
            now = default_timer()
            #past due or time ran backwards.
            if now > revive_at or now < cls.dead_at:
                cls.dead         = False
                cls.numfounddead = 0
                cls.dead_at      = 0
                return False
            return True
        else:
            return False

    @classmethod
    def start(cls, profile):
        return FAILED_TO_START

    @classmethod
    def kill(cls):
        # Shouldn't ever need to call this anymore, but let's just let it try anyway :)
        with cls.lock:
            start = time.clock()
            proc = getattr(cls, 'proc', None)
            if proc is not None:
                log.info('closing stdin')
                try:
                    proc.stdin.close()
                except Exception:
                    log.error('error closing stdin')
                    traceback.print_exc()
                log.info('killing process')
                try:
                    if not sys.platform.startswith('win'): #hasattr(cls.proc, 'kill'):
                        cls.proc.kill()
                    else:
                        #if windows.
                        h = int(cls.proc._handle)
                        if h >= 0:
                            ctypes.windll.kernel32.TerminateProcess(h, 1) #@UndefinedVariable
                            try:
                                seconds_run = get_process_runtime_secs(h)
                            except Exception:
                                log.error('error finding run time')
                                traceback.print_exc()
                            else:
                                log.debug('ran for %s seconds', seconds_run)
                                import hooks
                                hooks.notify('digsby.research.run_time', seconds_run)
                        else:
                            log.error('not killing process, invalid handle: %r', h)
                except Exception:
                    log.error('error killing process')
                    traceback.print_exc()
                else:
                    while cls.proc.poll() is None:
                        time.sleep(.001)
                del cls.proc
            end = time.clock()
            return end - start

    stop = kill

    _start_time = 0

#    def stop(self):
#        import time
#        start = time.clock()
#        self.proc.stdin.close() #close the pipe, causing main() to finish (i.e. clean shutdown)
#        while self.proc.poll() is None:
#            time.sleep(.001)
#        end = time.clock()
#        del self.proc
#        return end - start

def get_process_runtime_secs(handle):
    f = ctypes.wintypes.FILETIME()
    ctypes.windll.kernel32.GetSystemTimeAsFileTime(ctypes.byref(f))

    c, e, k, u = ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME()
    ctypes.windll.kernel32.GetProcessTimes(handle, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u))

    seconds_run = ((f.dwHighDateTime << 32) + f.dwLowDateTime - ((c.dwHighDateTime << 32) + c.dwLowDateTime)) / (1.0 * 10**7)
    return seconds_run

def test_conditions(useridlems):
    from common import pref
    idle_time = pref('research.idle_time_ms',
                     default=pref('research.idle_time_min',
                                  default=DEFAULT_IDLE_MINUTES,
                                  type=int) * 60 * 1000,
                     type=int)

    if useridlems < idle_time:
        if not pref('research.always_on', default=False):
            return False

    import wx
    if wx.GetPowerType() != wx.POWER_SOCKET and not pref('research.battery_override', False):
        return False

    return bool(get_research_pref())

def get_research_pref():
    import common
    return common.profile.localprefs['research.enabled']

def set_research_pref(val):
    import common
    common.profile.localprefs['research.enabled'] = val

def get_cpu_percent(chassis_percent = None):
    #if the chassis recommended % is less than the default, limit to that.
    #^ will be true for laptops.  If, for example, we switch desktops to be limited to 80%, but the default is 75, they will default to 75.
    #however, anything less than 75% will be limited to that level.
    if chassis_percent is None:
        chassis_percent = Driver.chassis_desired_cpuUsage()
    import common
    try:
        return int(common.profile.localprefs['research.cpu_percent'])
    except (KeyError, AttributeError) as _e:
        chassis_percent = float(chassis_percent)
        chassis_percent *= 100
        try:
            if chassis_percent < common.profile.defaultprefs.get('research.cpu_percent', chassis_percent):
                return min(chassis_percent, common.pref('research.cpu_percent', chassis_percent, type=float)) #default for this chasis
            else:
                return common.pref('research.cpu_percent', chassis_percent, type=float)
        except AttributeError as _e2:
            return common.pref('research.cpu_percent', chassis_percent, type=float)

def get_bandwidth_percent():
    import common
    try:
        return common.profile.localprefs['research.bandwidth_percent']
    except KeyError:
        return common.pref('research.bandwidth_percent', DEFAULT_BANDWIDTH_PERCENT * 100, type=float)

def control(useridlems):
    if Driver.is_dead():
        return 2000
    if not test_conditions(useridlems):
        try:
            Driver.stop()
        except Exception:
            traceback.print_exc()
        else:
            if Driver._start_time != 0:
                log.debug('tried to run for %s', default_timer() - Driver._start_time)
        Driver._start_time = 0
    else:
        try:
            from common import profile
            ret = Driver.start(profile)
        except Exception:
            traceback.print_exc()
        else:
            if ret == STARTED:
                Driver._start_time = default_timer()
            elif ret == FAILED_TO_START:
                Driver._start_time = 0
            elif ret == ALREADY_RUNNING:
                return 500
            return 500
    return 2000

def check_cli_args(*a):
    import sys
    set_val = sys.opts.set_plura_option
    if set_val is None:
        return

    else:
        log.info('setting intial research pref to %r', set_val)
        set_research_pref(set_val)

#def initialize():
#    import wx
#    if 'wxMSW' in wx.PlatformInfo:
#        from peak.util.plugins import Hook
#        try:
#            import researchtoast
#            Hook('digsby.research.started').register(researchtoast.on_research)
#        except Exception:
#            traceback.print_exc()
#        Hook('digsby.app.idle', 'research').register(control)
#        Hook('blobs.update.prefs').register(check_cli_args)
#        init()

inited = False

def init(*a, **k):
    global inited
    if not inited:
        inited = True
        import atexit
        atexit.register(Driver.kill)

