'''
A simple performance tracker.
'''

import time
import hooks

DISABLE_STATS = False

def get_tzoffset():
    daylight = time.gmtime(time.time()).tm_isdst
    return time.altzone if time.daylight and daylight else time.timezone

def dump():
    import simplejson
    return simplejson.dumps(dict(
        tzOffset = get_tzoffset(),
        events = stats.events(),
        eventNames = stats.eventNames(),
        samples = stats.samples(),
        sampleNames = stats.sampleNames(),
    ))
    

class MockStatistics(object):
    def event(self, eventName):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def events(self): return []
    def samples(self): return []
    def eventNames(self): return {}
    def sampleNames(self): return {}

def on_account_state_changed(acct, state):
    if acct.protocol is not None and state:
        event('.'.join(['account', acct.protocol, state]))

metrics_hooks = [('account.state', on_account_state_changed),
                 ('imwin.created', None)]

def register_hooks():
    for hook, cb in metrics_hooks:
        if cb is None: cb = lambda *a, **k: event(hook)
        hooks.register(hook, cb)

try:
    stats
except NameError:
    if DISABLE_STATS:
        stats = MockStatistics()
    else:
        try:
            import cgui
            stats = cgui.Statistics(15 * 1000)
        except:
            stats = MockStatistics()
    
    stats.start()
    event = stats.event

