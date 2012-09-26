import random
import wx
from Queue import Queue
from threading import Thread


class BgThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.q = Queue()

    def run(self):
        q = self.q
        while True:
            item = q.get()
            print item
            q.task_done()

def main():
    a = wx.PySimpleApp()

    threads = []
    for x in xrange(50):
        bg = BgThread()
        bg.setDaemon(True)
        bg.start()
        threads.append(bg)

    f = wx.Frame(None)
    b = wx.Button(f, -1, 'button')

    def on_button(e=None):
        random.choice(threads).q.put(wx.EvtHandler())

    b.Bind(wx.EVT_BUTTON, on_button)

    timers = []
    for x in xrange(20):
        t = wx.PyTimer(on_button)
        t.Start(5, False)
        timers.append(t)

    s=f.Sizer=wx.BoxSizer(wx.HORIZONTAL)
    s.Add(b)
    f.Show()

    a.MainLoop()

if __name__ == '__main__':
    main()