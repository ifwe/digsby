# XXX: 2012-02-21: I don't believe this has been tested in a long time. It may need to be completely re-tooled. -md
import os
import sys

def update_and_restart(tempdir):
    import wx

    updater = os.path.join(os.getcwd(), "mac_updater.pyc")

    from Authorization import Authorization, kAuthorizationFlagDestroyRights
    auth = Authorization(destroyflags=(kAuthorizationFlagDestroyRights,))
    try:
        python = sys.executable
        pipe = auth.executeWithPrivileges(python, updater, tempdir)

        output = pipe.read()

        if output.find("error") != -1:
            wx.MessageBox(_("Error while updating Digsby. Please restart and try again, or grab the latest version from digsby.com. Digsby will now shut down."))
            pipe.close()
            wx.GetApp().ExitMainLoop()
            return

        pipe.close()

        wx.MessageBox(_("Updated successfully. Digsby now needs to restart."))

        os.spawnv(os.P_NOWAIT, python, ["python", updater, "restart"])
        wx.GetApp().ExitMainLoop()

    except:
        wx.MessageBox(_("Unable to authenticate. Please restart and try again."))

def platform_cleanup():
    return []
