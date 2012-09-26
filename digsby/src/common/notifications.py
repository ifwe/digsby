'''
Notifications for program events.

See the docstring for the "fire" method for a detailed description.
'''
from __future__ import with_statement
import wx, os.path
import config
from util.primitives import traceguard, dictadd
from util.introspect import memoize
import util.data_importer as importer
from path import path
from common.slotssavable import SlotsSavable
from os.path import exists as path_exists
from common import profile, pref
from itertools import chain
from logging import getLogger; log = getLogger('notifications')

from Queue import Queue, Empty
from weakref import ref

class cancellables(Queue):
    def __init__(self):
        Queue.__init__(self)
        self.reaction_names = set()

    def put(self, item):
        item = item() # weakref
        if item is not None:
            self.reaction_names.add(item.__class__.__name__)
        return Queue.put(self, item)

    def had_reaction(self, reaction_name):
        return reaction_name in self.reaction_names

    def cancel(self):
        n = 0
        try:
            while True:
                item = self.get(block = False)
                if isinstance(item, ref):
                    item = item()

                if item is not None:
                    try:
                        wx.CallAfter(item.cancel)
                    except wx.PyDeadObjectError:
                        pass
                    except Exception:
                        from traceback import print_exc
                        print_exc()
                    else:
                        n += 1
        except Empty:
            pass
        log.info('cancelled %d notification reactions', n)

def add_reaction(notifications, notification_name, reaction_name):
    reactions = notifications[None].setdefault(notification_name, [])
    reaction = dict(reaction=reaction_name)
    if reaction not in reactions:
        reactions.append(reaction)

def add_required_notifications(nots):
    '''
    Adds notifications that cannot be disabled.
    '''

    if nots and config.platform == 'mac':
        add_reaction(nots, 'message.received', 'BounceDockIcon')

from copy import deepcopy
def get_user_notifications():
    user_notifications = deepcopy(dict(profile.notifications))
    add_required_notifications(user_notifications)
    return user_notifications

def fire(topic, **info):
    '''
    Presents a simple interface for firing notification events.

    >> fire('error', title = 'Connection Error', msg = 'A connection could not be established')

    topic  one or more of the topic keys listed in src/gui/notificationview.py,
           i.e., "message.received.initial"

    info   special keyword arguments giving information about the event.
           Each notification topic expects different arguments, and some
           "Reactions" (i.e., Popup windows) also look for options here.

    Extra arguments are passed to "Reactions" the user has set up to trigger
    for specific topics.

    Topics use dotted notation to indicate a hierarchy. If "message.received.initial"
    is fired and there is a sound effect set to trigger for "message.received",
    it will play. Only one type of each "Reaction" is allowed to fire for each event,
    so if a sound effect is set for "message" as well, it will not play.
    '''
    assert '_' not in topic, 'underscores not allowed in topic names'

    # topic can be a string, or a list of strings.
    if isinstance(topic, basestring): topic = [topic]
    else: assert isinstance(topic, list) # todo: iterable

    # fire the longest topic strings first, since they will be deepest in the tree.
    topics = sorted(set(chain(*(_topics_from_string(t) for t in topic))), reverse=True)

    log.debug('fired topics %r', topics)

    types   = set()
    cancels = cancellables()

    fired = False

    try:
        notifications = get_user_notifications()
    except AttributeError:
        return log.warning('no notifications yet')

    # If this topic is in a set of topics to always fire, mark
    # 'always_show' as True in the info dict. (See below)
    always_show = info.get('always_show', [])
    always_show = set(always_show) if always_show is not None else set()
    for topic in topics:
        always_show.update(always_fire.get(topic, []))

    if 'buddy' in info:
        # First, try buddy specific events.

        try:
            idstr = info['buddy'].idstr()
            buddy_events = notifications.get(idstr, [])
        except:
            buddy_events = []

        log.debug('found %d buddy specific events', len(buddy_events))
        if buddy_events:
            fired = True
            firetopics(topics, buddy_events, types = types, cancels = cancels, **info)

    # Then fire "generic" events set for all buddies.
    generic_events = notifications.get(None, [])
    if generic_events:
        fired = True
        firetopics(topics, generic_events,
                   types = types, cancels = cancels, **info)

    if always_show:
        # Optionally, "mandatory" reaction types can be specified.
        # If we haven't fired them yet, do so.
        import gui.notificationview as nview

        # map reaction names -> reaction classes
        G = globals()
        reactions = set(G[name] for name in always_show)

        # TODO: this block should be factored out and replaced by another call to firetopics
        ninfo = nview.get_notification_info()
        didFireType = set()
        for topic in topics:
            for reaction in reactions - types:
                if reaction in didFireType:
                    continue

                args = dictadd(ninfo.get(topic, {}), info)

                def doit(cancels=cancels, reaction=reaction, args=args):
                    cancellable = reaction()(**args)
                    if hasattr(cancellable, 'cancel'):
                        cancels.put(ref(cancellable))

                didFireType.add(reaction)
                wx.CallAfter(doit)
                fired = True

    # Call "on_done" if specified.
    try: on_done = info['on_done']
    except KeyError: pass
    else:
        if not fired:
            log.info('Calling on_done callback')
            with traceguard: on_done()

    # return a delegate lowercased typenames of all event types that were triggered
    return cancels

def firetopics(topics, events, types, cancels, **info):
    import gui.notificationview as nview
    if types is None:
        types = set()

    ninfo = nview.get_notification_info()

    for topic in topics:
        for event in events.get(topic, []):
            reaction, eventinfo = getReaction(event, topic)
            if reaction in types or reaction is None:
                continue

            template_info = ninfo.get(topic, {})

            def doit(cancels = cancels, reaction = reaction, args = dictadd(template_info, info), eventinfo = eventinfo):
                cancellable = reaction(**eventinfo)(**args)
                if hasattr(cancellable, 'cancel'):
                    cancels.put(ref(cancellable))


            wx.CallAfter(doit)
            types.add(reaction)

    return types

def getReaction(mapping, topic):
    mapping  = dict(mapping)
    reaction = mapping.pop('reaction')

    if isinstance(reaction, basestring):
        reaction = globals().get(reaction, None)

    if not reaction in reactions_set:
        return None, None

    #TODO: temporary...until we allow customizable soundsets.
    if reaction is Sound:
        from gui.notifications.sounds import active_soundset, SoundsetException

        try:
            soundset = active_soundset()
        except SoundsetException:
            soundset = {}
        try:
            sound_filename = soundset[topic]
        except KeyError:
            log.warning("Sound specified for topic %r but no sound descriptor found in sounds.yaml. using default", topic)
            sound_filename = soundset.get('default')
            if sound_filename is None:
                log.warning("\tNo default found in soundset. No sound will be played")
                return None, None

        mapping.update(soundfile = sound_filename)

    return reaction, mapping


#
# these object are possible reactions to events occuring.
#
# calling them invokes the event.
#

class Reaction(object):

    def preview(self):
        'This method is invoked via the GUI as a demonstration.'
        pass

    @property
    def allowed(self):
        'notifications.enable_%s'
        cname = type(self).__name__.lower()
        try:
            away = profile.status.away
        except AttributeError:
            return True
        else:
            return bool(pref('notifications.enable_%s' % cname, True) and
                    not (away and pref('messaging.when_away.disable_%s' % cname, False)))

class Sound(Reaction):
    'Play a sound'

    desc = 'Play sound %(filename)s'

    def __init__(self, soundfile):
        self.soundfile = soundfile

    def __call__(self, **k):
        if not self.allowed:
            return

        import gui.native.helpers as helpers
        if pref('fullscreen.disable_sounds', False) and helpers.FullscreenApp():
            return

        if path_exists(self.soundfile):
            wx.Sound.PlaySound(self.soundfile)

    def preview(self):
        self()

    def __repr__(self):
        return '<Sound %s>' % path(self.filename).basename()

class Alert(Reaction):
    "Display an alert"

    desc = 'Show alert "%(msg)s"'

    def __init__(self, msg):
        self.msg = msg

    def __call__(self, **info):
        if not self.allowed:
            return
        wx.MessageBox(self.msg)

class Popup(Reaction):
    'Show a popup notification'

    @classmethod
    def desc(cls, info):
        return 'Show a popup notification'

    def __init__(self, sticky = False):
        self.sticky = sticky

    def __call__(self, **info):
        cpy = vars(self).copy()
        cpy.update(info)

        if 'Popup' in (cpy.get('always_show', None) or []):
            cpy['always_show'] = True
        else:
            cpy['always_show'] = False

        if not (self.allowed or cpy.get('always_show', False)):
            return

        from gui.toast import popup
        return popup(**cpy)

class ShowContactList(Reaction):
    'Show the contact list'
    DEFAULT_DURATION_SEC = 3

    desc = 'Show the contact list for %(duration)s seconds'

    def __init__(self, duration):
        self.duration = duration

    def __call__(self):
        print 'do buddylist stuff for', self.duration, 'sec'


class LogMessage(Reaction):
    'Log a message to the console'

    def __init__(self, msg):
        self.msg = msg

    def __call__(self, **info):
        if self.msg.find('%') != -1 and info.get('buddy', None) is not None:
            log.info(self.msg, info['buddy'])
        else:
            log.info(self.msg)

class StartCommand(Reaction):
    'Start an external command'

    desc = 'Start external command "%(path)s"'

    def __init__(self, path):
        self.path = path

    def __call__(self, **info):
        os.startfile(self.path)

    def preview(self): self()


def get_notification_info(_cache = []):
    try:
        nots = _cache[0]
    except IndexError:
        pass

        from gui import skin
        mod = importer.yaml_import('notificationview', loadpath = [skin.resourcedir()])

        nots = _process_notifications_list(mod.__content__)

        _cache.append(nots)

    # allow plugins to add their own notification topics here.
    import hooks
    hooks.notify('digsby.notifications.get_topics', nots)

    return nots

def _process_notifications_list(nots_list):
    from util.primitives.mapping import odict_from_dictlist
    nots = odict_from_dictlist(nots_list)

    ordered_underscores_to_dots(nots)
    update_always_fire(nots)
    return nots

def add_notifications(nots_list):
    to_update = get_notification_info()
    mynots = _process_notifications_list(nots_list)

    for k in mynots:
        to_update[k] = mynots[k]

    # Now, keep "error" at the end.
    error = to_update.pop('error', None)
    if error is not None:
        to_update['error'] = error

def add_default_notifications(not_defaults):
    default_notifications[None].update(not_defaults)

always_fire = {}

def update_always_fire(nots):
    always_fire.clear()

    for name, info in nots.iteritems():
        if 'always_show' in info:
            reactions = info.get('always_show')
            if isinstance(reactions, basestring):
                reactions = [reactions]

            assert all(isinstance(o, basestring) for o in reactions)
            always_fire[name] = reactions

def ordered_underscores_to_dots(d):
    'like above, for odicts'

    ordered_keys = d._keys[:]

    for i, key in enumerate(list(ordered_keys)):
        if key and '_' in key:
            new_key         = key.replace('_', '.')
            d[new_key]      = d.pop(key)
            ordered_keys[i] = new_key

    d._keys = ordered_keys


from common.message import StatusUpdateMessage

class IMWinStatusUpdate(Reaction):
    def __init__(self, **info):
        self.info = info

    def __call__(self, **info):
        self.info.update(info)

        on_done = info.pop('on_done', lambda *a, **k: None)

        from gui.imwin.imhub import on_status
        wx.CallAfter(on_status, StatusUpdateMessage(**self.info), on_done)

#
# these reactions fill the dropdown in the notification editor
# for choosing a new event.
#
reactions = [Popup, Alert, Sound, ShowContactList, StartCommand, IMWinStatusUpdate]

# Add mac specific Reactions
if 'wxMac' in wx.PlatformInfo:

    class BounceDockIcon(Reaction):
        'Bounce the Dock icon'

        def __call__(self, **info):
            tlw = wx.GetApp().GetTopWindow()
            if tlw:
                # not really an error, but we can only choose info or error,
                # and info doesn't give us the right behavior
                tlw.RequestUserAttention(wx.USER_ATTENTION_ERROR)

    reactions.extend([BounceDockIcon])

reactions_set = set(reactions)

#
# DO NOT ADD ENTRIES TO THIS LIST
# please see the note in _incoming_blob_notifications in digsbyprofile.py
#
default_notifications = {
 None: {'contact.returnsfromidle': [],
        'email.new': [{'reaction': 'Popup'}],
        'error': [{'reaction': 'Popup'}],

        'filetransfer.ends': [{'reaction': 'Popup'}],
        'filetransfer.error': [{'reaction': 'Popup'}],
        'filetransfer.request': [{'reaction': 'Popup'}],
        'message.received.background': [{'reaction': 'Popup'}],
        'message.received.initial': [{'reaction': 'Sound'}],
        'message.received.hidden': [{'reaction': 'Popup'}],
        'myspace.alert': [{'reaction': 'Popup'}],
        'myspace.newsfeed': [{'reaction': 'Popup'}],

        # omg do not want
        'twitter.newdirect': [{'reaction':'Popup'}],
        'twitter.newtweet':  [{'reaction':'Popup'}],
    }
}


for topic in ['contact.signon', 'contact.signoff','contact.available', 'contact.away', 'contact.returnsfromidle', 'contact.idle']:
    seq = default_notifications[None].setdefault(topic, [])
    seq += [{'reaction': 'IMWinStatusUpdate'}]


class Notification(SlotsSavable):
    pass


TOPIC_SEP = '.'


@memoize
def _topics_from_string(topic):
    _check_topic_string(topic)

    topiclist = topic.split(TOPIC_SEP)
    topics = reversed([TOPIC_SEP.join(topiclist[:x])
                       for x in xrange(1, len(topiclist)+1)])
    return list(topics)

def _check_topic_string(topic):
    if not isinstance(topic, basestring):
        raise TypeError('topic must be a string')
    if topic.find('..') != -1:
        raise ValueError('consecutive periods not allowed in topic')
    if topic.startswith('.') or topic.endswith('.'):
        raise ValueError('topic cannot start or end with a topic')

