from common import pref
import util.net as net
import wx
import time

def TAGGED_DOMAIN():
    return pref('tagged.domain', '.tagged.com')

def SECURE():
    return '' if TAGGED_DOMAIN() == '.tag-local.com' else 's'

def WEBROOT():
    return 'http://www' + TAGGED_DOMAIN()

def weblink(resource = ''):
    return net.httpjoin(WEBROOT(), resource)

def launchbrowser(where):
    wx.LaunchDefaultBrowser(weblink(where))

def format_currency(amount):
    amount = str(amount)
    segments = reversed([amount[max(0, i-3):i] for i in range(len(amount), 0, -3)])
    return '$' + ','.join(segments)

def format_event_time(event_time):
    MINUTE = 60
    HOUR = 60 * MINUTE
    DAY = 24 * HOUR
    WEEK = 7 * DAY
    MONTH = 30 * DAY

    # In seconds
    delta  = int(time.time()) - int(event_time)

    if delta < MINUTE:
        return _('{seconds} seconds ago').format(seconds = delta)
    elif delta < MINUTE * 2:
        return _('A minute ago')
    elif delta < HOUR:
        return _('{minutes} minutes ago').format(minutes = delta / MINUTE)
    elif delta < HOUR * 2:
        return _('An hour ago')
    elif delta < DAY:
        return _('{hours} hours ago').format(hours = delta / HOUR)
    elif delta < DAY * 2:
        return _('A day ago')
    elif delta < WEEK:
        return _('{days} days ago').format(days = delta / DAY)
    elif delta < WEEK * 2:
        return _('A week ago')
    elif delta < MONTH:
        return _('{weeks} weeks ago').format(weeks = delta / WEEK)
    elif delta < MONTH * 2:
        return _('A month ago')
    elif delta < MONTH * 3:
        return _('Over 2 months ago')
    else:
        return _('Over 3 months ago')
