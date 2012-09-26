from gui.toolbox import GetTextFromUser
import wx
from logging import getLogger; log = getLogger('oscargui')

def format_screenname(oscar, set):

    oldval = str(oscar.self_buddy.nice_name)

    while True:
        line1 = _('Enter a formatted screenname for {username}').format(username=oscar.username)
        line2 = _('The new screenname must be the same as the old one, except for changes in capitalization and spacing.')
        
        val = GetTextFromUser(u'%s\n\n%s' % (line1, line2),
                              caption = _('Edit Formatted Screenname'),
                              default_value = oldval)

        if val is None: return

        elif val.lower().replace(' ', '') == oldval.lower().replace(' ', ''):
            print 'setting new formatted name', val
            return set(str(val))


def set_account_email(oscar, set):
    def show(email = None):
        val = GetTextFromUser(_('Enter an email address:'),
                              _('Edit Account Email: {username}').format(username=oscar.self_buddy.name),
                              default_value = email or '')

        if val is None or not val.strip():
            return

        log.info('setting new account email %r', val)
        return set(val)

    timer = wx.PyTimer(show)

    def success(email):
        if timer.IsRunning():
            timer.Stop()
            show(email)
        else:
            log.info('server response was too late: %r', email)

    def error():
        log.info('error retreiving account email for %r', oscar)
        if timer.IsRunning():
            timer.Stop()
            show()

    timer.StartOneShot(2000)
    oscar.get_account_email(success = success, error = error)
