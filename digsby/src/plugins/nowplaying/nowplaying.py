'''
Adds a status message showing your currently playing song from one of
several media players.
'''
from __future__ import with_statement
import traceback, sys
from common.statusmessage import StatusMessage
from common import profile, pref

from util import import_module, RepeatTimer, memoize, Storage as S, odict, iproperty
from util.lrucache import LRU
from util.threads import threaded
from util.primitives import LazySortedDict
from util.net import UrlQuery, get_tinyurl as get_short_url

from urlparse import urlparse, urlunparse
from traceback import print_exc
import platform, wx
from gui import skin

from logging import getLogger; log = getLogger('nowplaying')

# a unicode character showing two eighth notes joined by a bar
NOTES_SYMBOL = unichr(9835)
NOWPLAYING_STATUS_PREF = 'plugins.nowplaying.initial_status'

# this message is used when you have the "now playing" status selected, but
# aren't playing any music
NO_SONG_MESSAGE = _('Listening to music')

# these are names of modules containing "currentSong" methods
# each module is checked in order for a currently playing song
player_order = [
   ('winamp', 'Winamp'),
   ('itunes_win', 'iTunes')
]

song_checkers = odict()

def register(cls):
    if cls.app_name in song_checkers:
        song_checkers.pop(cls.app_name).release()

    song_checkers[cls.name_id] = cls()

class ThreadSafeLRU(LRU):
    def __getitem__(self, key):
        with self.lock:
            return LRU.__getitem__(self, key)

def change_hostname(url, newhost):
    url = list(urlparse(url))
    url[1] = newhost
    return urlunparse(url)

class SniprSongLRU(ThreadSafeLRU):
    def __missing__(self, song):
        """
        returns None and retrieves the snipr url for the given song,
        inserting the return value from that API.
        """
        self[song] = None
        try:
            return self[song]
        finally:
            url = UrlQuery('http://www.amazon.com/gp/search',
                           LazySortedDict(dict(ie       = 'UTF8',
                                               keywords = song.encode('utf-8'),
                                               tag      = 'dmp3-20',
                                               index    = 'digital-music',
                                               linkCode = 'ur2',
                                               camp     = '1789',
                                               creative = '9325')))
            f = threaded(get_short_url)
            f.verbose = True
            f(url, success = lambda val: self.__setitem__(song, change_hostname(val, 'music.digsby.com')),
                                         error   = lambda _e: self.pop(song))

def amazon_format(args):
    artist = args.get('artist', '')
    title = args.get('title', '')
    return u'%s - %s' % (artist, title)

class SongChecker(object):
    PROCESS_NAME = None

    def __init__(self, processes=None):
        if type(self) is SongChecker:
            raise NotImplementedError

        #self.running(processes)

    def currentSong(self, processes=None):
        if not self.running(processes):
            return None
        try:
            return self._currentSong()
        except Exception, e:
            print_exc()
            self._release()
            return None

    def running(self, processes=None):
        '''
        Checks the list of processes (or process_list()) and returns whether or not the
        program is running.

        If the process is running, makes sure there is a handle to the process (or whatever)
        If the process is not running, makes sure to release the handle to the process (or whatever).
        '''
        if processes is None:
            from gui.native.win.process import process_list
            processes = process_list()

        running = self.PROCESS_NAME in processes

        if running:
            self._get_instance()
        elif not self.running:
            self._release()

        return running

    def _release(self):
        self.release()

    def _get_instance(self):
        self.get_instance()

class ComSongChecker(SongChecker):
    COM_NAME = None
    def __init__(self):
        if type(self) is ComSongChecker:
            raise NotImplementedError
        SongChecker.__init__(self)
        self.client = None

    def get_instance(self):
        '''
        Warning: this may take a while!
        '''
        from comtypes.client import CreateObject
        if self.client is None:
            self.client = CreateObject(self.COM_NAME)

    def release(self):
        if self.client is not None:
            self.client.Release()
            self.client = None


def get_song_checker(player_name):
    'Returns the "currentSong" function for the specified player.'

    if player_name not in song_checkers:
        modname ='nowplaying.%s' % player_name
        if modname not in sys.modules:
            sys.modules[modname] = import_module(modname)
    try:
        return song_checkers[player_name]
    except KeyError:
        return None

class NowPlayingStatus(StatusMessage):
    __slots__ = StatusMessage.__slots__ + ['format_args', 'format_string', 'app', '_use_notes_symbol', '_a_href']
    __slots__.remove('message')

    # this indicates to status GUI that the message is not editable
    edit_toggle = False

    def __init__(self, message = None, status = None, editable = None, **kws):
        #log.info('NowPlayingStatus.__init__(message = %r, editable = %s, kws = %r)', message, editable, kws)
        # store extra formatting for protocols which want specific information
        self.format_args = kws.get('format_args', None)
        self.format_string = kws.get('format_string', None)
        self.app = kws.get('app', None)

        self._use_notes_symbol = kws.get('_use_notes_symbol', True)
        self._a_href = kws.get('_a_href', False)

        StatusMessage.__init__(self,
                               title    = _('Listening To...'),
                               status   ='available' if status is None else status,
                               message  = None,
                               editable = False,
                               edit_toggle = kws.get('edit_toggle', self.edit_toggle))

    def copy(self, message  = None,
                   status   = None,
                   editable = None,
                   format   = None,
                   app = None,
                   format_args = None,
                   format_string = None,
                   **kws):
        kws.update(locals())
        kws.pop('self')
        kws.pop('kws')


        for k, v in kws.items():
            if v is None:
                kws[k] = getattr(self, k)

        kws['_use_notes_symbol'] = self._use_notes_symbol
        kws['_a_href'] = self._a_href
        return NowPlayingStatus(**kws)

    def for_account(self, acct):
        'Returns a status object for a specific account.'

        if acct.protocol == 'yahoo':
            # Yahoo's first party client fails at displaying extended
            # characters in status messages (like the unicode music
            # symbol), so leave it out for them.
            copied_msg = self.copy()
            copied_msg._use_notes_symbol = False
            return copied_msg
        # AIM doesn't support HTML in the status message when the status is avail.
        if acct.protocol in ('aim',) and (self.status or '').lower() == 'away':
            print 'setting _a_href to True'
            copied_msg = self.copy()
            copied_msg._a_href = True
            return copied_msg

        return self

    @property
    def media(self):
        # for MSN's extra media support
        return None
#        return S(format_string = self.format_string,
#                 format_args = self.format_args,
#                 app = self.app)

    @property
    def icon(self):
        return skin.get('statusicons.nowplaying', None)

    def _get_message(self):
        s, a = self.format_string, self.format_args

        N = (NOTES_SYMBOL + ' ') if self._use_notes_symbol else ''
        if s and a and not a.get('is_blank', False):

            message = N + s % a

            link = NowPlaying.snipr_cache[amazon_format(a)] if pref('plugins.nowplaying.show_link', True) else None
            if link and getattr(self, '_a_href', False):
                href = '<html><a href="%s">%s</a></html>'
                try:
                    return href % (link, message)
                except UnicodeError:
                    return message
            try:
                return message + (' - ' + link if link else '')
            except UnicodeError:
                return message
        else:
            return N + NO_SONG_MESSAGE

    def _set_message(self, val):
        pass

    message = iproperty('_get_message', '_set_message')

from peak.util.addons import AddOn
Plugin = AddOn # TODO: plugin API

# Add a status message to the global list.
def status_factory():
    '''
    Yes, a factory.
    '''
    start_status = pref('plugins.nowplaying.initial_status', 'available')
    if start_status == 'idle':
        start_status = 'available'
    return NowPlayingStatus(status = start_status)

class NowPlaying(Plugin):

    edit_toggle = False
    SONG_THRESHOLD = 1
    snipr_cache = SniprSongLRU(20)
    inited = False

    def setup(self):
        self.links = []
        self.timer = RepeatTimer(5, lambda: wx.CallAfter(self.on_timer))
        self.song = (None, 0)
        self.status = None
        self.on_before_status_change(profile.status)

    def link(self):
        self.links.append(profile.prefs.link('plugins.nowplaying.format', self.format_string_change, callnow=False))
        self.links.append(profile.prefs.link('plugins.nowplaying.backup_format', self.format_string_change, callnow=False))

    def unlink(self):
        while self.links:
            link = self.links.pop(0)
            link.unlink()

    def format_string_change(self, value):
        log.info('Format string changed to %r', value)
        self.check_song(force=True)

    def on_before_status_change(self, status):
        '''
        Invoked when the profile's status message changes.
        '''
        log.info('on_status_change')

        is_music_status = isinstance(status, NowPlayingStatus)
        timer           = getattr(self, 'timer', None)
        timer_alive     = timer is not None and self.timer.isAlive()

        # If the status is a "music status" and our timer isn't running, start it.
        if is_music_status and not timer_alive:
            self.link()
            log.debug('starting now playing timer')
            if timer is None:
                self.timer = timer = RepeatTimer(5, lambda: wx.CallAfter(self.on_timer))
            timer.start()
            # call it now to look responsive! yay
        # Otherwise if the status is not a "music status" and the timer IS running, stop it.
        elif not is_music_status and timer_alive:
            log.debug('stopping now playing timer')
            self.song = (None, 0)
            self.unlink()
            self.timer.stop()
            releaseAll()
        if is_music_status:
            s = status.status
            if pref(NOWPLAYING_STATUS_PREF, type = str, default = 'available') != s:
                profile.prefs.__setitem__(NOWPLAYING_STATUS_PREF, s.lower())

        if not is_music_status:
            return status

        try:
            if status is not self.status:
                self.check_song(force=True, status=status)
            return self.status
        except Exception:
            traceback.print_exc()
            return status

    def on_timer(self):
        'Invoked when the song check timer goes off. Which happens a lot.'
        status = profile.status
        if not isinstance(status, NowPlayingStatus):
            # early exit for when the status message is not a music status
            if hasattr(self, 'timer'):
                self.timer.stop()
            return

        self.check_song()
        try:
            new_message = self.status.message
        except Exception:
            traceback.print_exc()
            return

        if new_message != profile.status.message:
            log.info('current message: %r', profile.status.message)
            log.info('setting new now playing status: message=%r, cursong=%r', new_message, profile.status.message)
            profile.set_status(self.status)

    def check_song(self, force=False, status=None):
        cursong = currentSong()
        song = cursong.format_string % cursong.format_args
        new_message = ' '.join([NOTES_SYMBOL, song])

        oldsong, songcount = self.song

        def got_new_song():
            # on a new song, store the name, and the "count" of times we've
            # seen it
            self.snipr_cache[amazon_format(cursong.format_args)]
            self.song = (cursong, 0)

        def set_new_song(status = status):
            if status is None:
                status = profile.status
            self.status = status.copy(message = new_message, **cursong)

        if oldsong is None:
            got_new_song()
            set_new_song()

        elif cursong != oldsong:
            got_new_song()
            if force:
                set_new_song()
        else:
            # only set the profile status after a certain period of time passed
            # with the same song present
            songcount += 1
            self.song = (cursong, songcount)

            # only set the song after (N * five) seconds of play time
            if force or (songcount >= self.SONG_THRESHOLD):
                set_new_song()

def mutate_status(status, profile=profile):
    if hasattr(profile, '__call__'):
        profile = profile()
    return NowPlaying(profile).on_before_status_change(status)

def _no_song():
    return S(format_string = '%(title)s',
             format_args   = dict(title = NO_SONG_MESSAGE, is_blank = True,),
             app           = '')

def message_for_song(song):
    '''
    Given a "song" dictionary returned by the player specific modules, returns
    format_string and format_dict.
    '''
    if song is None:
        return _no_song()

    for k,v in song.items():
        if v is None:
            song.pop(k)

    g = song.get

    title    = g('title', None) or ''
    artist   = g('artist', None) or ''
    filename = g('filename', None) or ''

    status = g('status', False)

    # show [stopped] or [paused] if not playing
    if status and status != 'playing':
        status_string = ' [%(status)s]'
    else:
        status_string = ''

    format_dict = song

    formats = []
    add = lambda x: formats.append(x + status_string)

    add(pref('plugins.nowplaying.format', default=u'%(title)s - %(artist)s'))
    add(pref('plugins.nowplaying.backup_format', default=u'%(filename)s'))

    for fmt in formats[:]:
        if type(fmt) is not unicode:
            fmt = fmt.decode('ascii')

        try:
            fmt % format_dict
        except (KeyError, TypeError), e:
            formats.remove(fmt)

    if formats:
        retval = S(format_string = formats[0],
                   format_args   = format_dict,
                   app           = g('app'))
    else:
        retval = _no_song()

    return retval

def currentSong():
    '''
    Discover the current song.

    Checks MODULE.currentSong() where MODULE is one of the modules listed above
    in player_order.
    '''
    songs = []

    for player, player_name in player_order[:]:
        try:
            checker = get_song_checker(player)
        except Exception:
            # If there was an error importing the player module, don't try it again.
            print_exc()
            checker = None

        if checker is None:
            player_order.remove((player, player_name))
            if player in song_checkers:
                song_checkers.pop(player_name).release()
            continue

        try:
            # Get a song dictionary describing the currently playing song for this player.
            song = checker.currentSong()
        except Exception:
            print_exc()
            continue

        #log.debug('Got song info from player %r. Info is: %r', player_name, song)

        # if we found a song that's playing, return it now
        if song is not None:
            if not 'app' in song:
                song['app'] = player_name

            if song['status'] == 'playing':
                return message_for_song(song)
            else:
                # otherwise save it for later
                songs.append(song)

    # we only found nothing, or stopped/paused music
    return message_for_song(songs[0] if songs else None)

def releaseAll():
    for player, player_name in player_order[:]:
        try:
            checker = get_song_checker(player)
        except Exception:
            print_exc()
            continue

        checker.release()

if __name__ == '__main__':
    print currentSong()

#def initialize():
#    import wx
#    if 'wxMSW' in wx.PlatformInfo:
#        from peak.util.plugins import Hook
#        Hook('digsby.profile.addons', 'nowplaying').register(NowPlaying)
#        Hook('digsby.im.statusmessages', 'nowplaying').register(status_factory)
#        Hook('digsby.im.statusmessages.set.pre', 'nowplaying').register(mutate_status)

#initialize()

