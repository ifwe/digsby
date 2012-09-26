'''
buddy icons
'''

ICON_REQUEST_LIMIT_SECS = 60 * 60
ICON_REQUEST_WARNING_LIMIT = 30

from time import time
from common import netcall
from logging import getLogger; log = getLogger('buddyicons')

def _rate_limited_icon_get(buddy):
    '''
    May call buddy.protocol.get_buddyicon, if enough time has passed since
    the last call. Stores "last time" on the buddy.
    '''

    last_get = getattr(buddy, '_last_icon_get', 0)
    now = time()

    # limit buddy icon requests
    if now - last_get > ICON_REQUEST_LIMIT_SECS:
        buddy._last_icon_get = now

        # log a warning if we've gotten this buddy's icon a lot
        buddy._icon_requests += 1
        if buddy._icon_requests > ICON_REQUEST_WARNING_LIMIT:
            log.warning("asking for %r's buddy icon too often", buddy)
            buddy._icon_requests = 0

        netcall(lambda: buddy.protocol.get_buddy_icon(buddy.name))

