import util.net as net
import time

def testSpacify():
    tests = [
        ('', ''),
        (' ', ' '),
        ('  ', '  '),
        ('   ', ' &nbsp; '),
        (' ' * 1000, ' ' + ''.join(['&nbsp;'] * 998) + ' '),
    ]


    for i, (input, expected) in enumerate(tests):
        result = net.spacify(input)

        if result != expected:
            print "%d) FAIL result: %r, expected: %r" % (i, result, expected)
        else:
            print '%d) OK' % i


linkify_test_strings = (
    'n.com',                  'n.com',
    'x.com',                  '<a href="http://x.com">x.com</a>',
    'http://www.digsby.com',  '<a href="http://www.digsby.com">http://www.digsby.com</a>',
    'http://digsby.com',      '<a href="http://digsby.com">http://digsby.com</a>',
    'www.digsby.com.',        '<a href="http://www.digsby.com">www.digsby.com</a>.',
    '{digsby.com}',           '{<a href="http://digsby.com">digsby.com</a>}',
    'www.digsby.com/woot!!!', '<a href="http://www.digsby.com/woot">www.digsby.com/woot</a>!!!',
    'not.a.link',             'not.a.link',
    'gopher://awesome',       '<a href="gopher://awesome">gopher://awesome</a>',
    'http://digsby.com:8080', '<a href="http://digsby.com:8080">http://digsby.com:8080</a>',
    'http://user:pass@www.digsby.com', '<a href="http://user:pass@www.digsby.com">http://user:pass@www.digsby.com</a>',
    '(www.digsby.com/path/to/stuff)',       '(<a href="http://www.digsby.com/path/to/stuff">www.digsby.com/path/to/stuff</a>)',
    'http://en.wikipedia.org/wiki/Robots_(computer_game)', '<a href="http://en.wikipedia.org/wiki/Robots_(computer_game)">http://en.wikipedia.org/wiki/Robots_(computer_game)</a>',
    'https://www.selectblinds.com/fauxwoodblinds/faux-wood-blinds-detail.aspx?pid=94&c=1', '<a href="https://www.selectblinds.com/fauxwoodblinds/faux-wood-blinds-detail.aspx?pid=94&c=1">https://www.selectblinds.com/fauxwoodblinds/faux-wood-blinds-detail.aspx?pid=94&c=1</a>',
    'http://mini/mike/digsySetup.exe', '<a href="http://mini/mike/digsySetup.exe">http://mini/mike/digsySetup.exe</a>',
    'http://img.thedailywtf.com/images/200801/Error\'d/Unvisable.jpg', '''<a href="http://img.thedailywtf.com/images/200801/Error'd/Unvisable.jpg">http://img.thedailywtf.com/images/200801/Error'd/Unvisable.jpg</a>''',
    'http://www.flickr.com/photos/55972631@N00/2281143312/', '<a href="http://www.flickr.com/photos/55972631@N00/2281143312/">http://www.flickr.com/photos/55972631@N00/2281143312/</a>',
    'https://edit.europe.yahoo.com/config/replica_agree?.done=http%3a//mail.yahoo.com&.scrumb=JwNajALT0z3', '<a href="https://edit.europe.yahoo.com/config/replica_agree?.done=http%3a//mail.yahoo.com&.scrumb=JwNajALT0z3">https://edit.europe.yahoo.com/config/replica_agree?.done=http%3a//mail.yahoo.com&.scrumb=JwNajALT0z3</a>',
    'sup', 'sup',
    'This is just a test.', 'This is just a test.',
    'False positives.suck', 'False positives.suck',
    'svn://mini/svn/dotSyntax', '<a href="svn://mini/svn/dotSyntax">svn://mini/svn/dotSyntax</a>',
    'http://www.google.com/search?q=digsby&ie=utf-8&oe=utf-8&aq=t&rls=org.mozilla:en-US:official&client=firefox-a', '<a href="http://www.google.com/search?q=digsby&ie=utf-8&oe=utf-8&aq=t&rls=org.mozilla:en-US:official&client=firefox-a">http://www.google.com/search?q=digsby&ie=utf-8&oe=utf-8&aq=t&rls=org.mozilla:en-US:official&client=firefox-a</a>',
    '#', '#',
    '.', '.',
    '/', '/',
    '("http://mini/digsby_setup_r12699.exe")',
    '("<a href="http://mini/digsby_setup_r12699.exe">http://mini/digsby_setup_r12699.exe</a>")',

    'http://www.weather.com/outlook/events/sports/tenday/75075?from=36hr_topnav_sports',
    '<a href="http://www.weather.com/outlook/events/sports/tenday/75075?from=36hr_topnav_sports">http://www.weather.com/outlook/events/sports/tenday/75075?from=36hr_topnav_sports</a>',

    'http://aapplemint.blogspot.com/2007/02/ghanian-palm-nut-soup.html',
    '<a href="http://aapplemint.blogspot.com/2007/02/ghanian-palm-nut-soup.html">http://aapplemint.blogspot.com/2007/02/ghanian-palm-nut-soup.html</a>',

    '(http://mini/cgi-bin/ticket/2494)',
    '(<a href="http://mini/cgi-bin/ticket/2494">http://mini/cgi-bin/ticket/2494</a>)',

    '3.ly',
    '<a href="http://3.ly">3.ly</a>',

    'fg.dm,fg', '<a href="http://fg.dm">fg.dm</a>,fg',

    'http://translationparty.com/#993473',
    '<a href="http://translationparty.com/#993473">http://translationparty.com/#993473</a>',

    # from http://twitter.com/Scott_Ian/status/9308822323
    '''Vote for Pearl here:http://www.goldengodsawards.com/vote.html''',
    '''Vote for Pearl here:<a href="http://www.goldengodsawards.com/vote.html">http://www.goldengodsawards.com/vote.html</a>''',

    '''http://site.com/search.php?section=people&ginv=191#c[city]=181&c[country]=4&c[noiphone]=1&c[section]=people&c[sort]=1&offset=10''',
    '''<a href="http://site.com/search.php?section=people&ginv=191#c[city]=181&c[country]=4&c[noiphone]=1&c[section]=people&c[sort]=1&offset=10">http://site.com/search.php?section=people&ginv=191#c[city]=181&c[country]=4&c[noiphone]=1&c[section]=people&c[sort]=1&offset=10</a>''',

    'http://v.digsby.com/?id=kr7njks1&wid=0kknv56hq1',
    '<a href="http://v.digsby.com/?id=kr7njks1&wid=0kknv56hq1">http://v.digsby.com/?id=kr7njks1&wid=0kknv56hq1</a>',

    'http://live.xbox.com/en-US/profile/Achievements/ViewAchievementDetails.aspx?tid=%09]%3acn*i7',
    '<a href="http://live.xbox.com/en-US/profile/Achievements/ViewAchievementDetails.aspx?tid=%09]%3acn*i7">http://live.xbox.com/en-US/profile/Achievements/ViewAchievementDetails.aspx?tid=%09]%3acn*i7</a>',

    'http://www.amazon.com/gp/offer-listing/B0009VXBAQ/ref=dp_olp_1?ie=UTF8&qid=1210776182&sr=1-1',
    '<a href="http://www.amazon.com/gp/offer-listing/B0009VXBAQ/ref=dp_olp_1?ie=UTF8&qid=1210776182&sr=1-1">http://www.amazon.com/gp/offer-listing/B0009VXBAQ/ref=dp_olp_1?ie=UTF8&qid=1210776182&sr=1-1</a>',

    'www.\xe2\x98\x83.com'.decode('utf8'),
    '<a href="http://www.\xe2\x98\x83.com">www.\xe2\x98\x83.com</a>'.decode('utf8'),
)

known_failures = (
    "log.info('yahoo",
    "log.info('yahoo",

    'top left icon worked (http://mini/cgi-bin/ticket/2494)...do you remember',
    'top left icon worked (<a href="http://mini/cgi-bin/ticket/2494">http://mini/cgi-bin/ticket/2494</a>)...do you remember',

    'face.com\'s',
    '<a href="http://face.com">face.com\'s</a>',

    "google.com's",
    '''<a href="http://google.com">google.com</a>'s''',

)

linkify_test_strings = zip(linkify_test_strings[::2], linkify_test_strings[1::2])

def testLinkify(linkifyfunc):

    from sys import stdout
    success = 0
    for url, result in linkify_test_strings:
        myresult = linkifyfunc(url)

        if myresult == result:
            sout, out = stdout, stdout.write
            out('OK\n')
            success += 1
        else:
            sout, out = stdout, stdout.write
            out('FAIL\n')

        out('  result:    %s\n' % myresult)
        out('  expected:  %s\n\n' % result)
        sout.flush()

    print;print '%d/%d correct.' % (success, len(linkify_test_strings))

def testProxiesURLs(test_proxies):
    '''
    Tests urllib2 and httplib2 with various proxy settings
    '''

    import sys
    myproxy = dict()

    class fake: pass
    fake_proxy_settings = fake()
    fake_proxy_settings.get_proxy_dict = lambda: myproxy

    sys.modules['util.proxy_settings'] = fake_proxy_settings

    import util.net as net
    import util.httplib2 as httplib2

    test_urls = (
                 ('http ', 'http://www.google.com'),
                 ('https', 'https://mail.google.com'),
                 )

    import urllib2

    test_openers = (
                    ('urllib2 ', urllib2.urlopen,                          lambda response: response.code),
                    ('httplib2', lambda url: httplib2.Http().request(url), lambda response: response[0].status),
                    )

    for pname, proxy in test_proxies:
        myproxy.clear()
        myproxy.update(proxy)

        for uname, url in test_urls:
            for oname, opener, get_status in test_openers:
                print ('%s with proxy = %r with url=%r' % (oname, pname, uname)),
                try:
                    result = opener(url)
                    status = get_status(result)
                    if not net.httpok(status):
                        raise Exception(status)
                except Exception, e:
                    print '...fail (%r)' % e
                    #traceback.print_exc()

                else:
                    print '...success'


def testProxiesSockets(test_proxies):
    '''
    Tests socksockets with varios proxy settings.
    '''
    import netextensions
    import logextensions
    import digsbysite

    import sys, socket, time
    myproxy = dict()


    class fake: pass
    fake_proxy_settings = fake()
    fake_proxy_settings.get_proxy_dict = lambda: myproxy

    sys.modules['util.proxy_settings'] = fake_proxy_settings

    import threading

    import util
    myip = util.get_ips_s()[0]
    TEST_ADDR = (myip, 443)
    class TestSocketServer(threading.Thread):
        def run(self):
            self.__stop = False

            import socket
            server = socket.socket()
            server.bind(TEST_ADDR)
            server.listen(1)
            server.settimeout(2)
            while not self.__stop:
                try:
                    client, addr = server.accept()
                except socket.timeout:
                    continue
                else:
                    try:
                        print client.recv(1024)
                        client.close()
                    except Exception, e:
                        print '...fail (%r)' % e
            server.close()

        def join(self):
            self.__stop = True
            threading.Thread.join(self)

    socket_thread = TestSocketServer()
    socket_thread.start()
    import socks
    try:
        for pname, proxy in test_proxies:
            time.sleep(.1)
            myproxy.clear()
            myproxy.update(proxy)

            print ('socket with proxy = %r' % pname),
            try:
                testsck = socks.socksocket()
                testsck.setproxy(**net.GetProxyInfo())
                testsck.settimeout(1)
                testsck.connect(TEST_ADDR)
                testsck.sendall('...success')
                testsck.close()
            except Exception, e:
                print '...fail: (%r)' % e
#                traceback.print_exc()

    finally:
        socket_thread.join()


def testProxiesAsync(test_proxies):
    '''
    Tests async sockets with various proxy settings
    '''

    import sys
    print >>sys.stderr, "AsyncSocket proxy tests are incomplete and currently non-working"
    return

    myproxy = dict()

    class fake: pass
    fake_proxy_settings = fake()
    fake_proxy_settings.get_proxy_dict = lambda: myproxy

    sys.modules['util.proxy_settings'] = fake_proxy_settings

    import common

    class TestClientSocket(common.socket):
        def __init__(self, on_done):
            self.when_done = on_done
            common.socket.__init__(self)
        def handle_close(self):
            self.when_done()
            self.close()
            time.sleep(.1)

        def collect_incoming_data(self, data):
            common.socket.collect_incoming_data(self, data)

        def handle_connect(self):
            self.socket.sendall('...success\n')
            self.handle_close()

    class TestServerHandler(common.socket):
        def handle_close(self):
            if not getattr(self, '_got_term', None):
                print '...fail'
            self.close()
            time.sleep(.1)

        def found_terminator(self):
            self._got_term = True
            if self.data:
                print self.data.strip()
                self.data = ''
                self.handle_close()

    class TestServerSocket(common.socket):
        def handle_accept(self):
            conn, addr = self.accept()
            x = TestServerHandler(conn)
            x.set_terminator('\n')

    TEST_ADDR = ('192.168.1.101', 443)

    server = TestServerSocket()
    server.bind(TEST_ADDR)
    server.listen(2)
    test_proxies = list(test_proxies)
    global client
    client = None

    def test_one_proxy():
        global client
        if not test_proxies:
            print 'done'
            client.close()
            server.close()
            import AsyncoreThread; AsyncoreThread.end_thread()
            return

        pname, proxy = test_proxies.pop(0)
        myproxy.clear()
        myproxy.update(proxy)

        if client is not None:
            client.close()

        print ('asyncsocket with proxy = %r' % pname),
        client = TestClientSocket(on_done = test_one_proxy)
        client.connect(TEST_ADDR)

    test_one_proxy()
    time.sleep(.1)


def main():
    import sys
    sys.modules['__builtin__']._ = lambda s: s
    testLinkify(net.linkify)
    testSpacify()
    test_proxies = (
                    ('no proxy  ', dict(override='NOPROX', username=None, proxytype=None, addr=None, password=None, port=None)),
                    #('http squid', dict(username='', proxytype='HTTP',   addr='192.168.1.50',  override='SETPROX', password='', port='8080')),
                    ('my http   ', dict(username='', proxytype='HTTP',   addr='192.168.1.103', loverride='SETPROX', password='', port='8080')),
                    ('my socks4 ', dict(username='', proxytype='SOCKS4', addr='192.168.1.103', override='SETPROX', password='', port='1080')),
                    ('my socks5 ', dict(username='', proxytype='SOCKS5', addr='192.168.1.103', override='SETPROX', password='', port='1080')),
                    ('pw http   ', dict(username='digsby', proxytype='HTTP',   addr='192.168.1.103', override='SETPROX', password='password', port='8080')),
                    ('pw socks4 ', dict(username='digsby', proxytype='SOCKS4', addr='192.168.1.103', override='SETPROX', password='password', port='1080')),
                    ('pw socks5 ', dict(username='digsby', proxytype='SOCKS5', addr='192.168.1.103', override='SETPROX', password='password', port='1080')),
                    )

    testProxiesURLs(test_proxies)
    testProxiesSockets(test_proxies)
    testProxiesAsync(test_proxies) # Doesnt work yet!

if __name__ == '__main__':
    import digsbysite
    import traceback
#    import logging
#    logging.root.setLevel(1)
#    logging.basicConfig()
    main()
