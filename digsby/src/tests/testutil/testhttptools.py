import urllib2
import util
import util.httptools as httptools
import util.threads.threadpool as threadpool
import digsbysite, logextensions, netextensions
import tests.testapp as testapp

if __name__ == '__main__':
    _app = testapp.testapp()
    def success(resp):
        print 'success:', repr(resp.read())

    def error(err = None):
        print 'error:', None


    req = urllib2.Request('http://www.google.com')
    opener = util.net.build_opener()

    ro = httptools.RequestOpener(util.threaded(opener.open), req)
    ro.open(success = success, error = error)

    tp = threadpool.ThreadPool(2)
    _app.toggle_crust()
    _app.MainLoop()
    tp.joinAll()
