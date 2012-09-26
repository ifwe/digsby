
if __name__ == '__main__':
    import os, sys
    import tests.testapp as TA
    app = TA.testapp()
    os.chdir(sys.path[0])
    import protocols

def _main():
    import wx
    import hooks
    import services.service_provider as SP
    sps = [p.provider_id for p in wx.GetApp().plugins if p.info.type == 'service_provider']
    msp = SP.get_meta_service_provider('pop')
    diag = hooks.first("digsby.services.create", msp)
    diag.Show()
    diag.Bind(wx.EVT_CLOSE, lambda e: (e.Skip(), app.ExitMainLoop()))
    app.SetTopWindow(diag)
    app.MainLoop()

if __name__ == '__main__':
    _main()
