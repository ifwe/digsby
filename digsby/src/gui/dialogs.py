from util.callbacks import callsback
import wx

@callsback
def NonModalMessageDialog(*a, **k):
    '''
    workaround to get an effectively non-modal Message Dialog
    callback.success called with the return code from ShowModal
    '''
    callback=k['callback']
    def doNonModal(parent=None, *a):
        f = wx.Frame(parent)
        d = wx.MessageDialog(f, *a)
        ret = d.ShowModal()
        d.Destroy()
        f.Destroy()
        callback.success(ret)
    wx.CallAfter(doNonModal, *a)
