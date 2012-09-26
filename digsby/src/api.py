import wx

def guilogin(trampoline, username, password):
    print 'logging in', username
    yield

def wait(ms):
    print 'wait', ms
    return Wait(ms)

class Scheduler(object):
    pass

class Wait(Scheduler):
    stop_trampoline = True

    def __init__(self, ms):
        self.ms = ms

    def schedule(self, trampoline):
        self.trampoline = trampoline
        self.timer = wx.PyTimer(self.on_timer)
        print 'starting a timer for %d ms' % self.ms
        self.timer.Start(self.ms, True)

    def on_timer(self):
        print 'on_timer'
        self.timer.Stop()

        trampoline = self.trampoline
        del self.trampoline

        trampoline.run()

    def __repr__(self):
        return '<Wait %dms>' % self.ms
