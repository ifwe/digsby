import logging
import threading
import util.primitives.funcs as funcs

from gettext import ngettext

log = logging.getLogger('common.ach_mixin')

class AchievementMixin(object):
    MILESTONE_MESSAGES = {
        'twit_post':('has sent %(number)d tweets using Digsby!',                       'twitter'),
        'face_post':('has set %(his)s Facebook status %(number)d times using Digsby!', 'facebook'),
        'mysp_post':('has set %(his)s MySpace status %(number)d times using Digsby!',  'myspace'),
        'link_post':('has set %(his)s LinkedIn status %(number)d times using Digsby!', 'linkedin'),
        'im_sent':  ('has sent %(number)d IMs using Digsby!',                          'digsby'),

        'face_comment':('has commented on %(number)d Facebook posts using Digsby!',    'facebook'),
        'face_like'   :("has 'Liked' %(number)d Facebook posts using Digsby!",         'facebook'),
        'face_photo'  :('has looked at %(number)d Facebook photos using Digsby!',      'facebook'),

        'mysp_photo'  :('has looked at %(number)d MySpace photos using Digsby!',        'myspace'),
    }

    def __init__(self, **options):
        self.post_ach_all = options.setdefault('post_ach_all', self.default('post_ach_all'))
        self.informed_ach = options.setdefault('informed_ach', self.default('informed_ach'))

        self.ach_lock = threading.RLock()
        self.achievements_paused = True
        self.achievements_stored = funcs.Delegate()

    def should_do_ach(self):
        return self.informed_ach and self.post_ach_all

    def should_update(self):
        return self.informed_ach

    def update_complete(self):
        if self.achievements_paused:
            self.unpause_achievements()

    def get_options(self):
        try:
            get_opts = super(AchievementMixin, self).get_options
        except AttributeError:
            opts = {}
        else:
            opts = get_opts()
        for attr in ('post_ach_all', 'informed_ach'):
            if getattr(self, attr, None) != self.default(attr):
                opts[attr] = getattr(self, attr, None)

        return opts

    def try_connect(self, on_ready):
        if self.should_update():
            on_ready()
        else:
            def do_connect(do_post):
                log.info('return code %r', do_post)
                self.informed_ach = True
                self.post_ach_all = do_post
                self.update_info()
                on_ready()

            self.show_ach_dialog(success = do_connect)
            return False

    @property
    def do_post_achievements(self):
        return self.enabled and self.should_do_ach()

    def AchieveAccountAdded(self, protocol = None, name = None, *a, **k):
        log.info('AchieveAccountAdded, %r, %r, %r, %r', protocol, name, a, k)

    def AchieveAccounts(self, *a, **k):
        log.info('AchieveAccounts, %r, %r', a, k)

    def AchieveThreshold(self, type = None, threshold_passed = None, current_value = None, *a, **k):
        log.info('AchieveThreshold, %r, %r, %r, %r, %r', type, threshold_passed, current_value, a, k)

    def doAchieve(self, func):
        if self.do_post_achievements:
            with self.ach_lock:
                if self.achievements_paused:
                    self.achievements_stored += lambda: self.doAchieve(func)
                    return
            # else if not paused:
            func()

    def unpause_achievements(self):
        with self.ach_lock:
            paused, self.achievements_paused = self.achievements_paused, False

        if paused:
            self.achievements_stored.call_and_clear()

    def pause_achievements(self):
        with self.ach_lock:
            _paused, self.achievements_paused = self.achievements_paused, True


def get_num_accounts_string():
    import common
    p = common.profile()
    num_accounts = len(p.all_accounts)
    accounts = ngettext('%(num_accounts)d account',
                        '%(num_accounts)d accounts',
                        num_accounts)
    return accounts % locals()

