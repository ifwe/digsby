'''
Yahoo! 360 updates.

Incoming XML from the Yahoo server is parsed and stored in buddy.y360updates.
'''

from util import Storage
from datetime import datetime
from util import soupify, odict
from logging import getLogger; log = getLogger('yahoo360'); info = log.info
from util.BeautifulSoup import BeautifulStoneSoup

FEED_TEXT = u'New RSS Feed'

def handle(yahoo, y360xml, updates_cb = None):
    'Handle incoming Yahoo! 360 XML, updating buddy states as necessary.'
    log.info(y360xml)

    s = BeautifulStoneSoup(y360xml,
                              convertEntities=BeautifulStoneSoup.ALL_ENTITIES,
                              fromEncoding = 'utf-8')
    if not s or not s.mingle: return
    G = globals()

    updates = []
    for buddy in s.mingle.vitality.findAll('buddy'):
        vitals = buddy.findAll('vital')

        buddyobj = yahoo.buddies[buddy['id']]

        try:
            buddyobj.setnotifyif('y360hash', buddy['hash'])
        except KeyError:
            buddyobj.setnotifyif('y360hash', buddy['u'][len('http://360.yahoo.com/profile-'):])


        for vital in vitals:
            vitaltype = 'vital_' + vital['p'][:-1]
            print 'vitaltype', vitaltype
            if vitaltype in G:
                url, vid = vital.get('u', profile_link(buddy['hash'])), int(vital['id'])
                cdata = vital.renderContents(None)
                content = (u' - %s' % cdata) if cdata.strip() else ''

                # Remove any old RSS Feed entries if we got a new one
                if vitaltype == 'vital_feeds':
                    old_updates = buddyobj.y360updates
                    if old_updates:
                        for (update, tstamp) in list(old_updates):
                            if update[1].startswith(FEED_TEXT):
                                old_updates.remove((update, tstamp))


                updates.append( (G[vitaltype](url, vid, content),  # "profile" formatted
                                 int(vital['t'])) )                 # timestamp
            else:
                log.warning('unhandled 360 vital %s', vitaltype)

        if updates:
            if updates_cb: return updates_cb(updates)

            log.info('received %d yahoo 360 updates for %s', len(updates),  buddy['id'])


            ups = list(buddyobj.y360updates)
            ups.extend([update for update in updates if update not in ups])

            buddyobj.setnotifyif('y360updates', ups)

def profile_link(hash):
    return 'http://360.yahoo.com/profile-' + hash

def vital_blog(url, vid, content):
    return url, u'New Blog Post' + content

def vital_feeds(url, vid, content):
    return url, FEED_TEXT + content

def vital_profile(url, vid, content):
    if vid == 2:
        text = u'New Blast' + content
    else:
        text = u'Updated Profile' + content

    return url, text

def vital_lists(url, vid, content):
    return url, u'New Lists' + content

if __name__ == '__main__':
    s = '''
<mingle><vitality base-url="http://360.yahoo.com" expire-mins="48">
    <buddy id="digsby02" d="9" hash="ZrlqYs41cqED_oUFxKyvYg--" p="profile-">
        <vital id="2" t="1177094411" p="profile-"/>
    </buddy>
    <buddy id="digsby02" d="9" hash="ZrlqYs41cqED_oUFxKyvYg--" p="profile-"/>
    <buddy id="penultimatefire" d="9" hash="lM75WJshfqj_SUhuW3jIElKMsMlyxDg-" p="profile-"/>
</vitality></mingle>'''

    from pprint import pprint
    handle(None, s, lambda u: pprint(u))

'''
some samples for reference:

a blog update

<mingle><vitality event="change">
    <buddy p="profile-" hash="7UJrD9U6frDanyka2U2PgPXoDfk4vQfq" id="kevinwatters2005" u="http://360.yahoo.com/profile-7UJrD9U6frDanyka2U2PgPXoDfk4vQfq">
        <vital id="3" t="1169064623" p="blog-" u="http://blog.360.yahoo.com/blog-7UJrD9U6frDanyka2U2PgPXoDfk4vQfq">Entry for January 17, 2007 24321321: another one!!!</vital>
    </buddy>
</vitality></mingle>


a blast change (with url)

<mingle><vitality event="change">
    <buddy p="profile-" hash="7UJrD9U6frDanyka2U2PgPXoDfk4vQfq" id="kevinwatters2005" u="http://360.yahoo.com/profile-7UJrD9U6frDanyka2U2PgPXoDfk4vQfq">
        <vital id="2" t="1169064791" p="profile-" u="http://www.woot.com">this is my blast message</vital>
    </buddy>
</vitality></mingle>

another blast change (with url)

<mingle><vitality event="change">
    <buddy p="profile-" hash="7UJrD9U6frDanyka2U2PgPXoDfk4vQfq" id="kevinwatters2005" u="http://360.yahoo.com/profile-7UJrD9U6frDanyka2U2PgPXoDfk4vQfq">
        <vital id="2" t="1169064917" p="profile-" u="http://www.dotsyntax.com">another blast</vital>
    </buddy>
</vitality></mingle>

a profile update

<mingle><vitality event="change">
    <buddy p="profile-" hash="7UJrD9U6frDanyka2U2PgPXoDfk4vQfq" id="kevinwatters2005" u="http://360.yahoo.com/profile-7UJrD9U6frDanyka2U2PgPXoDfk4vQfq">
        <vital id="11" t="1169068045" p="profile-" u="http://360.yahoo.com/profile-7UJrD9U6frDanyka2U2PgPXoDfk4vQfq"/>
    </buddy>
</vitality></mingle>



a list edit

<mingle><vitality event="change">
    <buddy p="profile-" hash="7UJrD9U6frDanyka2U2PgPXoDfk4vQfq" id="kevinwatters2005" u="http://360.yahoo.com/profile-7UJrD9U6frDanyka2U2PgPXoDfk4vQfq">
        <vital id="12" t="1169065181" p="lists-" u="http://360.yahoo.com/lists-7UJrD9U6frDanyka2U2PgPXoDfk4vQfq"></vital>
    </buddy>
</vitality></mingle>


'''
