import calendar
import re
import rfc822
import string
import time
from util import linkify, preserve_newlines
from util.net import UrlShortener
from util.primitives.functional import compose

at_someone = re.compile(r'(?<!\w)(@\w+)(/\w+)?', re.UNICODE)
direct_msg = re.compile(r'^d\s+(\S+)\s+(.+)', re.DOTALL)
hashtag    = re.compile(r'(?<![\w/])(#[\w\-_]+)', re.UNICODE)
all_numbers = re.compile('^#\d+$')
href = '<a href="%s">%s</a>'

def _at_repl(match):
    name = match.group(0)[1:] # strip the @
    return '@' + (href % ('http://twitter.com/' + name, name))

def at_linkify(s):
    return at_someone.sub(_at_repl, s)

# Regexes that are given to the spellchecker so that it knows to ignore certain
# words like @atsomeone and #hashtags.
spellcheck_regex_ignores = [at_someone, hashtag]

def add_regex_ignores_to_ctrl(ctrl):
    for r in spellcheck_regex_ignores:
        ctrl.AddRegexIgnore(r)

def old_twitter_linkify(s):
    pieces = filter(None, at_someone.split(preserve_newlines(s)))
    s = ''.join(namelink(linkify(piece)) for piece in pieces)
    return hashtag_linkify(s)

def search_link(term):
    return ''.join(['<a href="http://search.twitter.com/search?q=%23',
                    term, '">#', term, '</a>'])

def _hashtag_repl(match):
    're.sub function for hashtag_linkify'

    tag = match.group(1)
    if all_numbers.match(tag) and len(tag) == 2:
        return match.group(0)
    return search_link(tag[1:])

def hashtag_linkify(text):
    'turn #hashtags into links to search.twitter.com'

    return hashtag.sub(_hashtag_repl, text)

twitter_linkify = compose([
    preserve_newlines,
    at_linkify,
    linkify,
    hashtag_linkify
])

def namelink(name):
    if not name.startswith('@'):
        return name
    if len(name) == 1:
        return name
    if name[1] in string.whitespace:
        return name

    return '@' + (href % ('http://twitter.com/' + name[1:], name[1:]))

def at_linkified_text(self):
    pieces = filter(None, at_someone.split(self.text))
    return u''.join(namelink(linkify(piece)) for piece in pieces)

def d_linkified_text(self):
    return linkify(self.text)

def format_tweet_date(tweet):
    fudge = 1.5
    seconds = calendar.timegm(rfc822.parsedate(tweet.created_at))
    delta  = int(time.time()) - int(seconds)

    if delta < (60 * fudge):
        return _('about a minute ago')
    elif delta < (60 * 60 * (1/fudge)):
        return _('about {minutes} minutes ago').format(minutes=(delta / 60) + 1)
    elif delta < (60 * 60 * fudge):
        return _('about an hour ago')
    elif delta < (60 * 60 * 24 * (1/fudge)):
        return _('about {hours} hours ago').format(hours=(delta / (60 * 60)) + 1)
    elif delta < (60 * 60 * 24 * fudge):
        return _('about a day ago')
    else:
        return _('about {days} days ago').format(days=(delta / (60 * 60 * 24)) + 1)

def twitter_mini_img_url(url):
    '''
    twitter users have profile_image_url.
    if you add a _mini to the end of the filename, you get a 20x20 version.
    '''
    i = url.rfind('.')
    first = url[:i]
    if i != -1 and first.endswith('_normal'):
        first = first[:-7]
        url = first + '_mini' + url[i:]
    return url

class TweetShrink(UrlShortener):
    endpoint = 'http://tweetshrink.com/shrink'

    def get_args(self, url):
        return dict(text=url)

    def process_response(self, resp):
        ret = UrlShortener.process_response(self, resp)
        import simplejson
        return simplejson.loads(ret)['text']

shrink_tweet = TweetShrink().shorten

