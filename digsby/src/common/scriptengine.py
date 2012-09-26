from __future__ import with_statement
from types import GeneratorType
import collections
import os.path
import sys

def runfile(filename):
    filename = os.path.expanduser(filename)

    with open(filename) as f:
        contents = f.read()
        runscript(contents, filename)

def runscript(script, filename):

    script_globals = {}
    exec script in script_globals

    try:
        main = script_globals['main']
    except KeyError:
        raise AssertionError('script %r did not define a main() function' % filename)

    if not hasattr(main, '__call__'):
        raise AssertionError('script %r main is not callable')

    exec 'main()' in script_globals


class Trampoline(object):
    """Manage communications between coroutines"""

    # thanks PEP 342

    running = False

    def __init__(self):
        self.queue = collections.deque()

    def add(self, coroutine):
        """Request that a coroutine be executed"""
        self.schedule(coroutine)

    def run(self):
        result = None
        self.running = True
        try:
            while self.running and self.queue:
                func = self.queue.popleft()
                result = func()
            return result
        finally:
            self.running = False

    def stop(self):
        self.running = False

    def schedule(self, coroutine, stack=(), value=None, *exc):
        def resume():
            try:
                if exc:
                    val = coroutine.throw(value, *exc)
                else:
                    val = coroutine.send(value)
            except:
                if stack:
                    # send the error back to the "caller"
                    self.schedule(
                        stack[0], stack[1], *sys.exc_info()
                    )
                else:
                    # Nothing left in this pseudothread to
                    # handle it, let it propagate to the
                    # run loop
                    raise

            print 'val is', val

            if isinstance(val, GeneratorType):
                # Yielded to a specific coroutine, push the
                # current one on the stack, and call the new
                # one with no args
                self.schedule(val, (coroutine, stack))

            elif stack:
                # Yielded a result, pop the stack and send the
                # value to the caller
                self.schedule(stack[0], stack[1], val)

            elif hasattr(val, 'schedule'):
                print 'stopping', stack
                val.schedule(self)
                self.stop()
                self.schedule(coroutine, stack)

            # else: this pseudothread has ended

        self.queue.append(resume)

def main():
    t = Trampoline()
    #t.add(api.guilogin(t, 'kevin', 'password'))
    #t.run()
    #return

    sys.path.append('src/tests/scripts')
    import open_im_window
    t.add(open_im_window.main())

    import wx
    class MyApp(wx.App):
        def __init__(self, trampoline):
            self.trampoline = trampoline
            wx.App.__init__(self)

        def OnInit(self):
            self.trampoline.run()
            #wx.Frame(None).Show()

    a = MyApp(t)
    a.MainLoop()

if __name__ == '__main__':
    main()
