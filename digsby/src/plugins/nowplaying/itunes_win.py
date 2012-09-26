'''

Simple current track info from iTunes (on Windows) via COM

'''
import threading
from nowplaying import ComSongChecker, register

class iTunesSongChecker(ComSongChecker):
    PROCESS_NAME = u'iTunes.exe'
    COM_NAME = 'iTunes.Application'

    app_name = 'iTunes'
    name_id = 'itunes_win'

    def _currentSong(self):
        import comtypes
        assert threading.currentThread().getName() == 'MainThread'
        try:
            song = self.client.CurrentTrack
        except comtypes.COMError, e:
            ecode = e.args[0]
            if ecode == -0x7ffeffff:
                # "Call was rejected by callee." - this happens if we ask while user is doing 'get info' on a track
                return getattr(self, '_lastsong', None)
            elif ecode == -0x7ffefef8:
                # "The object invoked has disconnected from its clients." - user quit iTunes
                self._release()
                return None
            elif ecode == -0x7ffbfe10:
                # 'CoInitialize has not been called.'
                comtypes.CoInitializeEx()
                return getattr(self, '_lastsong', None)
            else:
                raise e

        if song is None:
            thissong = None # no song currently playing
        else:
            thissong = dict(status   = 'playing' if bool(self.client.PlayerState) else 'stopped',
                            title    = song.Name,
                            filename = song.Name,
                            length   = song.Duration,
                            artist   = song.Artist,
                            playlist_position = song.Index,
                            rating   = song.Rating,
                            size     = song.Size)

        self._lastsong = thissong

        return self._lastsong

register(iTunesSongChecker)

if __name__ == '__main__':
    from time import clock
    before = clock()
    checker = iTunesSongChecker()
    print 'here1'
    checker.get_instance()
    print 'here2'
    info = checker._currentSong()
    duration = clock () - before

    from pprint import pprint
    pprint(info)
    print
    print 'duration', duration
