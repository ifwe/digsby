'''

Functions for accessing the Digsby server's web account management functionality.

'''
from util import threaded, UrlQuery
from hashlib import sha256

import traceback

import urllib2

from logging import getLogger; log = getLogger('digsby.web')

ACCOUNT_URL = 'https://accounts.digsby.com/login.php'

class DigsbyHttpError(Exception):
    pass

class DigsbyHttp(object):
    '''
    for talking to login.php
    '''

    def __init__(self, username, password, url = ACCOUNT_URL):
        self.username = username
        self.password = sha256(password).hexdigest()
        self.url = url

    def __repr__(self):
        return '<%s to %s>' % (self.__class__.__name__, self.url)

    def _urlopen(self, **params):
        resp = digsby_webget_no_thread(self.url, user = self.username, key = self.password, **params)

        # TODO: use real HTTP status codes...
        if resp == 'ERR':
            raise DigsbyHttpError('server indicated error: %r' % resp)

        return resp

    GET = _urlopen

    # TODO: post?

def digsby_acct_http(username, password, **params):
    'Account management with the digsby server.'

    return digsby_webget_no_thread(ACCOUNT_URL,
                                   user = username,
                                   key  = sha256(password).hexdigest(),
                                   **params)

@threaded
def digsby_webget(url, **params):
    return digsby_webget_no_thread(url, **params)

def digsby_webget_no_thread(url, **params):
    log.info('GETting url %s', url)
    url = UrlQuery(url, **params)
    log.info_s('full query is %s', url)

    req = urllib2.Request(str(url))
    req.add_header("Cache-Control", 'no-cache')
    req.add_header("User-Agent", 'Digsby')

    response = None
    try:
        response = urllib2.urlopen(req)
        res = response.read()
    except Exception, e:
        log.error('Error opening %r: %r', url, e)
        traceback.print_exc()
        return None
    finally:
        if response is not None:
            response.close()

    log.info('response: %r', res)
    return res
