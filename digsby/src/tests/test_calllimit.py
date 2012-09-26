def main():
    from gui.toolbox import calllimit
    import wx

    from time import sleep, clock
    print 'ready...', clock()
    sleep(1.5)
    print 'go'


    a = wx.PySimpleApp()

    class Foo(object):
        @calllimit(1)
        def bar(self):
            print 'foo', clock()

    foo = Foo()

    for x in xrange(100):
        foo.bar()

    f = wx.Frame(None)
    a.MainLoop()

if __name__ == '__main__':
    main()
