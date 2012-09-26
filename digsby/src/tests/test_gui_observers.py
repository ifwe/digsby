import util
import util.observe as observe
from weakref import ref

import gc
import wx

prefs = observe.ObservableDict()
prefs['test_attr'] = True

if False:
    def link(mapping, attr, cb):

        try:
            obs = mapping._observers
        except Exception:
            obs = mapping._observers = []

        obs.append(ref(cb))
else:
    def link(mapping, attr, cb):
        return mapping.link(attr, cb)

def main():
    f = wx.Frame(None)
    link(prefs, 'test_attr', lambda val, show=f.Show: show())
    f.Destroy()

    weak_f = ref(f)
    del f
    #linked.unlink()
    #del linked
    gc.collect()


    if weak_f() is not None:
        print gc.get_referrers(weak_f())
        from util.gcutil import gctree
        gctree(weak_f())
        wx.GetApp().MainLoop()

    assert weak_f() is None

if __name__ == '__main__':
    from tests.testapp import testapp
    a=testapp()#wx.PySimpleApp()
    main()
