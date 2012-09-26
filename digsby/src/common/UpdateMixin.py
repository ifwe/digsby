from logging import getLogger

log = getLogger('updatemixin'); info = log.info

from Protocol import StateMixin
from util import RepeatTimer
from util.primitives.funcs import get, Delegate

nothing = lambda *a, **k: None

class UpdateMixin(StateMixin):
    updatefreq = 300 # in seconds
    update_mixin_timer = True

    def __init__(self, updatefreq=None, *a, **k):
        StateMixin.__init__(self, *a, **k)
        if updatefreq is not None:
            try:
                updatefreq = int(updatefreq)
            except ValueError:
                pass
            else:
                if updatefreq < 1:
                    updatefreq = 60
                self.updatefreq =  max(updatefreq, 15)
        self.on_connect = Delegate()
        self.on_disable = Delegate()

    def disconnect(self):
        if self.update_mixin_timer:
            self.timer.stop()

    def update_now(self):
        raise NotImplementedError

    def get_options(self):
        options = dict((a, getattr(self, a)) for a in ('enabled', 'updatefreq'))
        if self.alias is not None:
            options['alias'] = self.alias
        return options

    def get_enabled(self):
        return get(self, '_enabled', False)

    def set_enabled(self, value):
        # the first time "enabled" is set, create a timer
        has_been_set = hasattr(self, '_enabled')
        if not has_been_set:
            self.change_reason(self.Reasons.NONE)

            if self.update_mixin_timer:
                info('%s creating a timer with update frequency %s', self,self.updatefreq)
                self.timer = RepeatTimer(int(self.updatefreq), self.update_now)
                self.timer.start(); self.timer.stop()
                if get(self, 'on_connect', None) is not None and self.update_now not in self.on_connect:
                    self.on_connect += self.update_now

        # when enabled, start the timer.
        self._enabled = value
        if value:
            info('enabling timer for %s', self)
            if self.OFFLINE and getattr(self, '_needs_connect', True):
                self._needs_connect = False
                get(self, 'Connect', nothing)()
            if self.update_mixin_timer:
                self.timer.reset(int(self.updatefreq))
        # when disabled, stop the timer.
        else:
            if has_been_set:
                if not self.OFFLINE:
                    get(self, 'Disconnect',nothing)()
                self._needs_connect = True

                if self.update_mixin_timer:
                    info('stopping timer for %s', self)
                    self.timer.stop()

                get(self, 'on_disable', nothing)()

    enabled = property(get_enabled, set_enabled)

    def pause_timer(self):
        with self.timer._cv:
            if not self.timer.paused:
                self.timer.pause()

    def start_timer(self):
        with self.timer._cv:
            if self.timer.paused:
                self.timer.start()

