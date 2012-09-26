'''
The __dict__ attribute of this module is used to back the localprefs dictionary (as defaults).

if localprefs gets something from this that is callable, it calls it (with no arguments). otherwise it just returns
whatever value it found.
'''

def save_to_dir():
    import wx, gui.native
    gui.native.extendStdPaths()

    import stdpaths
    return stdpaths.userdesktop

def chatlogdir():
    import wx, gui.native
    gui.native.extendStdPaths()

    import stdpaths
    from common import pref
    return pref('log.outputdir') or stdpaths.documents

buddylist_dock_enabled = False
buddylist_dock_autohide = False
buddylist_dock_revealms = 300

def get_research_enabled():
    import wx
    from common import pref
    had_prefs = wx.GetApp().local_settings_exist_at_startup
    if had_prefs:
        value = pref('research.enabled', default = True)
    else:
        value = pref('research.last_known_local', default = False)
    _set_research_pref(value)

    return value

def _set_research_pref(val):
    import common
    common.setprefif('research.enabled', val)
    common.setprefif('research.last_known_local', val)

    return val

def set_research_enabled(val):
    return _set_research_pref(val)
