import wx
import sys

class RefreshTimer(wx.Timer):
    """
       This calls refresh on all registered objects every second
    """

    def __init__(self):
        wx.Timer.__init__(self)
        self.registered = set()
        self.inited = True

    def Register(self,item):
        """
            Adds the item to the item set, and starts the timer if not yet started.
            It's fine to add an item more than once, becasue all items are stored
            as a set items added more tan once will still refresh only once.
        """

        self.registered.add(item)

        if not self.IsRunning():
#            print '--------------------Starting RefreshTimer--------------------'
            self.Start(1000)

    def UnRegister(self,item):
        """
            Removes and item fro mthe set, since only one refernce is held
            to the item this will stop the item from being refreshed no matter
            how many times it was registered.  It has also been made safe to
            unregister and item that isn't currently registered
        """
        try:
            self.registered.remove(item)
        except Exception:
            pass

        if not len(self.registered) and self.IsRunning():
#            print '--------------------Stoping RefreshTimer--------------------'
            self.Stop()

    def Notify(self):
        """
            Refreshes every item in the set, if there is an error with calling
            refresh it removes that item from the set
        """
#        print '--------------------Notify RefreshTimer--------------------'
        for item in set(self.registered):
            try:
                item.Refresh()
            except Exception:
                sys.stderr.write(''.join(['Error refreshing ',str(item),', removing from list']))
                self.UnRegister(item)


_refresh_timer_instance = None

def refreshtimer():
    global _refresh_timer_instance
    if _refresh_timer_instance is None:
        _refresh_timer_instance = RefreshTimer()

    return _refresh_timer_instance
