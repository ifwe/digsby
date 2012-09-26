'''
Twitter registers custom rows in the notification GUI for each custom feed
(group or search) the user creates through Hook handlers in this module.
'''

import hooks

_did_register_hooks = False

from logging import getLogger; log = getLogger('twitter'); debug = log.debug

def _register_hooks():
    '''Registers all global Twitter Hooks for dealing with notifications.'''

    global _did_register_hooks
    if _did_register_hooks: return
    _did_register_hooks = True

    if False:
        hooks.register('digsby.notifications.get_topics', _on_get_topics)
        hooks.register('digsby.notifications.changed', _on_nots_changed)

def active_twitter_protocols():
    '''Yields all active connected TwitterProtocol objects.'''

    from common import profile
    from .twitter import TwitterAccount

    for acct in profile.account_manager.socialaccounts:
        if isinstance(acct, TwitterAccount):
            if acct.enabled:
                conn = getattr(acct, 'connection', None)
                if conn is not None:
                    yield conn

def _on_nots_changed():
    '''Called when notifications are changed locally or via the server.'''

    for conn in active_twitter_protocols():
        _notifications_changed(conn)

def _on_get_topics(nots):
    '''Allows active twitter connections to possibly populate nots with more
    notification templates.'''

    for conn in active_twitter_protocols():
        _get_notification_info(conn, nots)


def _get_notification_info(self, info):
    return

    from common import profile
    nots = profile.notifications.setdefault(None, {})
    prefix = self.account_prefix

    template = dict(header='${tweet.user.screen_name}',
                    minor='${tweet.text.decode("xml")}',
                    pages='tweets',
                    update='paged',
                    icon='skin:serviceicons.twitter')

    def templ(desc):
        t = template.copy()
        t['description'] = desc
        return t

    # add notification templates for all unique searches and groups
    for key in nots.keys():
        if key.startswith(prefix):
            feed_name = key[len(prefix)+1:]
            if feed_name in self.feeds_by_name:
                feed = self.feeds_by_name[feed_name]

                if feed['type'] == 'search':
                    info[key] = templ(_('Twitter - %(feed_label)s (%(username)s)') % dict(feed_label=feed['label'], username=self.username))
                elif feed['type'] == 'group':
                    info[key] = templ(_('Twitter - Group: %(feed_label)s (%(username)s)') % dict(feed_label=feed['label'], username=self.username))

def _update_notifications(self, feeds):
    return

    def feed_notification_name(feed):
        assert feed['name']
        return '.'.join([self.account_prefix, feed['name']])

    from common import profile
    nots = profile.notifications.setdefault(None, {})

    popup_reaction = {'reaction': 'Popup'}

    # add or remove popup reactions for feeds
    for feed in feeds:
        notify_name = feed_notification_name(feed)
        popup = feed.get('popups', sentinel)
        if popup and popup is not sentinel:
            if notify_name not in nots:
                nots[notify_name] = [popup_reaction]
                debug('adding popup for %r to notifications', notify_name)
            elif popup_reaction not in nots[notify_name]:
                nots[notify_name].append(popup_reaction)
                debug('adding popup for %r to notifications', notify_name)
        elif notify_name in nots and popup == False:
            if popup_reaction in nots[notify_name]:
                nots[notify_name].remove(popup_reaction)
                debug('removing popup for %r', notify_name)

    # remove entries for feeds that don't exist
    for key in nots.keys():
        if key.startswith(self.account_prefix):
            fname = key[len(self.account_prefix)+1:]
            if fname not in self.feeds_by_name:
                debug('feed name %r not found in feeds, removing', fname)
                nots.pop(key)

def _notifications_changed(self):
    return

    from common import profile
    popup_reaction = {'reaction': 'Popup'}
    nots = profile.notifications.setdefault(None, {})
    for key in nots.keys():
        if key.startswith(self.account_prefix):
            fname = key[len(self.account_prefix)+1:]
            if fname in self.feeds_by_name:
                feed = self.feeds_by_name[fname]
                in_not = popup_reaction in nots[key]
                if feed.get('popups', sentinel) != in_not:
                    feed['popups'] = in_not
                    self.webkitcontroller.edit_feed(feed)

