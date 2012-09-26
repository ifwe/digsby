from tests.testapp import testapp
from time import clock
import os.path

def main():
    app = testapp()

    import cPickle

    fbdata_file = os.path.join(os.path.dirname(__file__), r'fbdata.dat')
    fbdata = cPickle.loads(open(fbdata_file, 'rb').read())

    from util import Storage
    account = Storage(
        protocol = 'fb20',
        connection = Storage(
            last_stream = fbdata['stream'],
            last_alerts = fbdata['alerts'],
            last_status = fbdata['status']))


    from fb20.fbacct import FBIB
    
    def doit():
        before = clock()
        FBIB(account).get_html(None)
        return clock() - before

    print 'first ', doit()
    print 'second', doit()

if __name__ == '__main__':
    main()
