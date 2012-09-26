__all__ = ['show_research_popup',
           'show_research_popup_once']

HEADER = _('Keep Digsby Free')
MINOR = _("Digsby will use your computer's free time using it to conduct both free and paid research.")

def _on_options():
    from gui.pref import prefsdialog
    prefsdialog.show('helpdigsby')

def show_research_popup():
    from gui.toast import popup

    buttons = [(_('Options'), _on_options),
               (_('OK'), lambda: None)]

    popup(header=HEADER,
          minor=MINOR,
          sticky=True,
          buttons = buttons)

def show_research_popup_once():
    from common import pref, setpref

    if not pref('research.showed_notification', default=False, type=bool):
        show_research_popup()

    setpref('research.showed_notification', True)

