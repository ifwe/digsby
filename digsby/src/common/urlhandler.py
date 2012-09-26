'''
register callbacks for URLs digsby handles
'''

import re
import traceback

matchers = []

URL_OPEN_IN_BROWSER = object()

class URLHandlerResult(object):
    '''
    Returned by "handle"
    '''

    __slots__ = ('cancel_navigation', 'url')

    def __init__(self, url, cancel_navigation=False):
        assert isinstance(url, basestring)
        self.url = url
        self.cancel_navigation = cancel_navigation

    def cancel(self, cancel=True):
        assert isinstance(cancel, bool)
        self.cancel_navigation = cancel

def handle(url):
    result = URLHandlerResult(url)

    # for now, only dispatch digsby:// urls
    if not url.startswith('digsby://'):
        return result

    url = url[len('digsby://'):]

    # try all compiled regexes against the rest of the URL
    for compiled_matcher, handler in matchers:
        match = compiled_matcher.match(url)
        if match is not None:
            try:
                handle_result = lazy_call(handler, *match.groups())
            except Exception:
                traceback.print_exc()
            else:
                if handle_result is not URL_OPEN_IN_BROWSER:
                    result.cancel()

    return result

def register(match_re, handler):
    '''
    Register a url handler.
    '''
    matchers.append((re.compile(match_re), handler))

def unregister(url, handler):
    global matchers
    new_matchers = []
    for compiled_matcher, url_handler in matchers:
        if url_handler is not handler or compiled_matcher.pattern != url:
            new_matchers.append((compiled_matcher, url_handler))

    matchers = new_matchers

def lazy_call(handler, *args):
    if not hasattr(handler, '__call__'):
        assert isinstance(handler, basestring)
        from util import import_function
        handler = import_function(handler)
        assert hasattr(handler, '__call__')

    return handler(*args)

