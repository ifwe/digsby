'''

monitor CPU usage

'''

from __future__ import division

import os, sys
from threading import Thread
from ctypes import WinError, byref, c_ulonglong
from time import clock, sleep
from traceback import print_exc
from cStringIO import StringIO

from datetime import datetime
from common.commandline import where

from util.threads.bgthread import BackgroundThread

from logging import getLogger; log = getLogger('perfmon')

PROCESS_QUERY_INFORMATION = 0x400
THREAD_QUERY_INFORMATION  = 0x0040

from ctypes import windll
kernel32 = windll.kernel32
GetProcessTimes = kernel32.GetProcessTimes
GetThreadTimes  = kernel32.GetThreadTimes
OpenProcess     = kernel32.OpenProcess
CloseHandle     = kernel32.CloseHandle
OpenThread      = kernel32.OpenThread

# number of consecutive high cpu ticks before prompting the user to send information
if getattr(sys, 'DEV', False):
    NUM_CONSECUTIVE_HIGHS = 5
else:
    NUM_CONSECUTIVE_HIGHS = 10

TICK_FREQUENCY = 5         # number of seconds: interval to measure CPU usage at
PROFILE_TICKS = 5         # number of ticks to profile for before sending diagnostic information
CPU_THRESHOLD = .95        # CPU usage above which is considered "high"

TICKS_PER_SEC = 1e7        # GetProcessTimes returns 100 nanosecond units
                           # (see http://msdn2.microsoft.com/en-us/library/ms683223(VS.85).aspx)

from util.introspect import all_profilers

def enable_profilers():
    profilers = all_profilers().values()
    for profiler in profilers: profiler.enable()
    _log_enabled_profilers(profilers)

def disable_profilers():
    profilers = all_profilers().values()
    for profiler in profilers: profiler.disable()
    _log_enabled_profilers(profilers)

def _log_enabled_profilers(profilers):
    log.info('%d/%d profilers enabled' % (len([p for p in profilers if p.enabled]), len(profilers)))

def profilers_enabled():
    return all(p.enabled for p in all_profilers().itervalues())

def get_stack_info():
    'Returns a string showing the current stack for each running thread.'
    io = StringIO()
    where(duplicates = True, stream = io)
    stack_info = io.getvalue()

    return '\n\n'.join([datetime.now().isoformat(), stack_info])


class CPUWatch(object):
    # todo: modelling a state machine with dynamic dispatch is ok, but this could
    # be clearer.

    def usage(self, user, kernel):
        return getattr(self, self.state + '_usage')(user, kernel)

    def watching_usage(self, user, kernel):
        self.user   = user
        self.kernel = kernel

        if user + kernel >= self.threshold:
            self.count += 1
            log.info('cpu usage is high (not profiling yet: %s/%s): %s', self.count, NUM_CONSECUTIVE_HIGHS, (user + kernel))

            if self.count > NUM_CONSECUTIVE_HIGHS:
                import wx
                wx.CallAfter(self.prompt_for_profiling)
        else:
            self.count = 0

    def profiling_usage(self, user, kernel):
        # log.info('profiling CPU usage: %s (user: %s, kernel: %s)', user + kernel, user, kernel)

        self.user   = user
        self.kernel = kernel

        if user + kernel >= self.threshold:
            log.info('cpu usage is high: %s' % (user + kernel))
            self.stack_info.append(get_stack_info())
            self.count += 1
            if self.count > PROFILE_TICKS:
                self.disable()
                self.send_info()
        else:
            log.info('cpu usage was low again: %s' % (user + kernel))
            log.info('')
            self.count = 0
            self.state = 'watching'

    def disabled_usage(self, user, kernel):
        pass

    def send_info(self):
        log.info('sending diagnostic information...')

        from util.diagnostic import Diagnostic
        import wx

        try:
            d =  Diagnostic(description = 'CPU usage was too high.')
            d.prepare_data()
            if d.do_no_thread_post():
                return wx.CallAfter(wx.MessageBox, _('A log of the problem has been sent to digsby.com.\n\nThanks for helping!'),
                                     _('Diagnostic Log'))
        except Exception:
            print_exc()

        wx.CallAfter(wx.MessageBox, _('There was an error when submitting the diagnostic log.'))


    def prompt_for_profiling(self):
        if self.__in: return
        self.__in = True
        log.info('prompting for profiling info')

        dev = getattr(sys, 'DEV', False)

        if profilers_enabled():
            self.state = 'profiling'
            return log.info('profiler is already enabled')
        
        line1 = _('Digsby appears to be running slowly.')
        line2 = _('Do you want to capture diagnostic information and send it to digsby.com?')
        msg = u'%s\n\n%s' % (line1, line2)

        import wx
        if dev or wx.YES == wx.MessageBox(msg, _('Digsby CPU Usage'), style = wx.YES_NO | wx.ICON_ERROR):

            log.info('enabling profiler')
            enable_profilers()
            self.count = 0
            self.state = 'profiling'
        else:
            self.disable()

        self.__in = False

    def disable(self):
        self.state = 'disabled'
        disable_profilers()
        self.cpu_monitor.done = True

    def __init__(self, threshold = CPU_THRESHOLD):
        if not (0 < threshold <= 1):
            raise ValueError('0 < threshold <= 1')

        self.state = 'watching'

        self.threshold = threshold
        self.count = 0
        self.ignore = False
        self.cpu_monitor = CPUMonitor(self.usage)
        self.cpu_monitor.start()
        self.__in = False

        self.stack_info = []

class CPUMonitor(BackgroundThread):
    def __init__(self, usage_cb, update_freq_secs = TICK_FREQUENCY):
        BackgroundThread.__init__(self, name = 'CPUMonitor')
        self.setDaemon(True)

        self.done = False
        self.update_freq_secs = 5
        self.perfinfo = ProcessPerfInfo()

        assert callable(usage_cb)
        self.usage_cb = usage_cb

    def run(self):
        self.BeforeRun()
        while not self.done:
            setattr(self, 'loopcount', getattr(self, 'loopcount', 0) + 1)
            self.usage_cb(*self.perfinfo.update())
            sleep(self.update_freq_secs)
        self.AfterRun()

class PerfInfo(object):
    __slots__ = ['last_update',
                 'handle',

                 'creationTime',     # <-- all c_ulonglongs corresponding to FILETIME structs
                 'exitTime',
                 'kernelTime',
                 'userTime',
                 'oldKernel',
                 'oldUser']

    def __init__(self):
        self.last_update = clock()

        for name in ('creationTime', 'exitTime', 'kernelTime', 'userTime', 'oldKernel', 'oldUser'):
            setattr(self, name, c_ulonglong())

        self.handle = self.get_handle()
        self.update()

    def get_handle(self):
        raise NotImplementedError

    def update(self):
        if not self.times_func(self.handle,
                               byref(self.creationTime),
                               byref(self.exitTime),
                               byref(self.kernelTime),
                               byref(self.userTime)):
            raise WinError()

        now  = clock()
        diff = now - self.last_update

        userPercent   = (self.userTime.value - self.oldUser.value) / TICKS_PER_SEC / diff
        kernelPercent = (self.kernelTime.value - self.oldKernel.value) / TICKS_PER_SEC / diff

        self.last_update     = now
        self.oldUser.value   = self.userTime.value
        self.oldKernel.value = self.kernelTime.value

        return userPercent, kernelPercent

    def __del__(self):
        CloseHandle(self.handle)


class ProcessPerfInfo(PerfInfo):
    "For measuring a process's CPU time."

    __slots__ = []

    def __init__(self):
        PerfInfo.__init__(self)

    def get_handle(self):
        return obtain_process_handle()

    @property
    def times_func(self):
        return GetProcessTimes

class ThreadPerfInfo(PerfInfo):
    __slots__ = ['thread_id']

    def __init__(self, thread_id):
        self.thread_id = thread_id
        PerfInfo.__init__(self)

    def get_handle(self):
        return obtain_thread_handle(self.thread_id)

    @property
    def times_func(self):
        return GetThreadTimes


def num_processors():
    # TODO: is there a more reliable way to get this?
    return os.environ.get('NUMBER_OF_PROCESSORS', 1)

def obtain_process_handle(pid = None):
    '''
    Gets a process handle for a process ID.
    If pid is not given, uses this process's ID.

    Don't forget to CloseHandle it!
    '''
    handle = OpenProcess(PROCESS_QUERY_INFORMATION, False, os.getpid() if pid is None else pid)

    if not handle:
        raise WinError()

    return handle

def obtain_thread_handle(thread_id):
    'Thread ID -> Thread Handle.'

    handle = OpenThread(THREAD_QUERY_INFORMATION, False, thread_id)

    if not handle:
        raise WinError()

    return handle

def main():
    import wx
    a = wx.PySimpleApp()
    f = wx.Frame(None)
    b = wx.Button(f, -1, 'info')

    def foo():
        while True:
            pass

    t = Thread(target = foo)

    cpumonitor = CPUMonitor()
    cpumonitor.start()

    def onbutton(e):
        t.start()

    b.Bind(wx.EVT_BUTTON, onbutton)

    f.Show()
    a.MainLoop()


if __name__ == '__main__':
    main()
