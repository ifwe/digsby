import util.callbacks as callbacks
from util.threads.timeout_thread import call_later
from .fberrors import FacebookError
import traceback

import logging
log = logging.getLogger('facebook.permchecks')

PERM_QUERY = "SELECT %s FROM permissions WHERE uid=%d"

class PermCheck(object):
    max_errcount = 3
    def __init__(self, api, perms=None):
        self.api = api
        self.perms = perms or []
        self.errcount = 0

    @callbacks.callsback
    def check(self, callback=None):
        log.critical('checking with callback: %r', callback)
        self.callback = callback
        if not self.perms:
            return self.callback.success({})
        self.api.query(PERM_QUERY % (','.join(self.perms), int(self.api.uid)),
                       success=self.check_success, error=self.check_error)

    def check_success(self, ret):
        log.info('check_success(%r)', ret)
        if not ret: #200 (http) empty, fix your damned API, Facebook! #4465, b80854
            return self.check_error(ret)
        try:
            perms = ret[0]
        except (TypeError, ValueError, AttributeError, KeyError): #200 empty is usually {}, KeyError here.
            traceback.print_exc()
            return self.check_error(ret)
        try:
            perms = dict(perms)
            log.info('perms: %r', perms)
        except (TypeError, ValueError):
            traceback.print_exc()
            return self.check_error(ret)
        if not all(perms.get(perm) for perm in self.perms):
            log.info('not all')
            return self.not_all_perms(perms)
        return self.callback.success(perms)

    def not_all_perms(self, perms):
        return self.callback.error(perms)

    def not_logged_in(self, ret):
        return self.callback.error(ret)

    def check_error(self, ret, *a):
        log.info("check_error: %r, %r", ret, a)
        if isinstance(ret, FacebookError):
            from .facebookprotocol import not_logged_in
            if not_logged_in(ret):
                log.info_s('not logged in: api: %r, session: %r', self.api.name, self.api.session_key)
                return self.not_logged_in(ret)
        self.errcount += 1
        if self.errcount >= self.max_errcount:
            return self.callback.error(ret)
        if self.api.mode == 'async':
            return call_later(1, self.check, callback = self.callback)
        else:
            return self.check(callback = self.callback)
