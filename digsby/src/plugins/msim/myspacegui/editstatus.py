import util
import gui.toolbox


@util.callsback
def get_new_status(callback=None):
    res = gui.toolbox.GetTextFromUser(message=_('Your Status:'), caption=_('MySpace Status'))
    if res is None:
        callback.error()
    callback.success(res)
