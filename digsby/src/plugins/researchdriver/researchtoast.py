RESEARCH_URL = 'http://wiki.digsby.com/doku.php?id=cpuusage'
SHOWN_RESEARCH_POPUP = 'digsby.research.help_stay_free_popup_shown'

_didshowresearch = False

def on_research():
    global _didshowresearch
    if _didshowresearch:
        return
    from common import pref
    if pref(SHOWN_RESEARCH_POPUP, default=False, type=bool):
        _didshowresearch = True
        return

    _show_research_popup()

def _show_research_popup():
    import wx
    assert wx.IsMainThread()
    import gui.skin
    from common import setpref
    from gui.toast.toast import popup

    def learnmore(*a, **k):
        import gui.pref.prefsdialog as prefsdialog
        prefsdialog.show('research')

    _didshowresearch = True
    setpref(SHOWN_RESEARCH_POPUP, True)
    popup(header = _('Help Digsby Stay Free'),
          major  = None,
          minor  = _("You are helping Digsby stay free by allowing Digsby to use your PC's idle time."),
          sticky = True,
          onclick = learnmore,
          icon = gui.skin.get('appdefaults.taskbaricon'),
          buttons = [(_('Learn More'), learnmore),
                     (_('Close'), lambda *a, **k: None)])
