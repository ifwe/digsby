'''
singleinstance.py

Uses wxSingleInstanceChecker and loopback socket communication to ensure
only one instance of an application runs at the same time.

For example:

    app = SingleInstanceApp(0)
    f = wx.Frame(None, -1, "This app only runs once!")
    f.Show(True)
    app.SetTopWindow(f)
    app.MainLoop()

Try to run this app more than once, and the first frame will pop up.
'''

from __future__ import with_statement
from contextlib import closing
import sys, socket, wx, logging, threading
from traceback import print_exc

def log(msg): # logging not setup yet
    pass

class SingleInstanceApp(wx.App):
    '''
    Single instance checking and notification through inheritance.

    Inherit your app from this class and be sure to call SetTopWindow with
    the frame you wish to be raised.
    '''
    def __init__(self, appname, *args, **kws):
        appname = '%s-%s' % (appname, wx.GetUserId())
        mgr = InstanceChecker(appname, 'localhost',
                              InstanceChecker.default_port)
        self.instance_checker = mgr

        try:
            should_quit = self._check_and_raise_other()
            if should_quit:
                log('instance already running. quitting!')
                self._do_quit()
        except Exception:
            print_exc()

        # wx.App's __init__ calls OnInit, which may spawn frames, so
        # we do this last
        wx.App.__init__(self, *args, **kws)

    def start_server(self):
        if self.instance_checker.isServerRunning():
            return

        port_taken = self.instance_checker.startServer()
        if port_taken:
            if self._check_and_raise_other():
                self._do_quit()

    def _do_quit(self):
        sys.exit(0)

    def _check_and_raise_other(self):
        another = self.instance_checker.isAnotherRunning()
        log('another instance running: %r' % another)

        if another:
            sent_raise = self.instance_checker.sendRaisePreviousFrameCommand()
            log('sent raise command: %r' % sent_raise)

        if another and sent_raise:
            return True

    def StopSingleInstanceServer(self):
        return self.instance_checker.stopServer()

    def SetTopWindow(self, w):
        wx.App.SetTopWindow(self, w)
        self.instance_checker.setFrame( w )
        self.start_server()

    def MainLoop(self, *args, **kws):
        if not hasattr(self, 'instance_checker'):
            raise AssertionError('must call SetTopWindow on this app first')

        try:
            wx.App.MainLoop(self, *args, **kws)
        finally:
            self.instance_checker.stopServer()

SERVER_NOT_STARTED = 0
SERVER_STARTED = 1
SERVER_PORT_TAKEN = 2

class ServerThread(threading.Thread):
    '''
    Class which simply runs a socket server in its own thread.

    It exposes some basic functionality, such as starting and stopping.
    '''
    backlog = 5

    def __init__(self, host, port, function, timeout = None, cv=None):
        threading.Thread.__init__(self, name=self.__class__.__name__ + \
                                  "-" + host + ":" + str(port))
        self.host, self.port = host,port
        self.function = function
        self.die = False
        self.timeout = timeout or 1
        self.cv = cv
        self.status = SERVER_NOT_STARTED

    def _notify_status(self, status):
        if not self.cv:
            self.status = status
        else:
            with self.cv:
                self.status = status
                self.cv.notify()

    def run(self):
        '''
        Sets socket up and listens. A timeout occurs every 'timeout' seconds
        (defaults to .2) so that it can check to see if it has been ordered to
        die. If a connection is made then it calls the function that was passed
        in.
        '''

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((self.host, self.port))
        except socket.error, e:
            self._notify_status(SERVER_PORT_TAKEN)
            return
        else:
            self._notify_status(SERVER_STARTED)

        s.listen(self.backlog)
        s.settimeout(self.timeout)

        while not self.die:
            try:
                client, address = s.accept()
                if self.die:
                    break

                try:
                    log('accepted a single instance ping, sending "ok"')
                    client.sendall('ok')
                finally:
                    client.close()

                try:
                    self.function()
                except Exception:
                    print_exc()

            # catches the timeout exception
            except socket.timeout, e:
                if self.die:
                    log('singleinstance s.accept()')
                    break

        # when stopped, close the socket
        try:
            s.close()
        except:
            pass

    def isRunning(self):
        # die and running status are opposite
        return not self.die

    def stop(self):
        self.die = True

def poke_client_port(host, port):
    '''
    Opens a connection with the specified host/port pair, then immediately
    closes the socket.

    Returns True if the connection was successfully made.
    '''
    try:
        # use an unproxied socket to localhost
        log('connecting to (%r, %r)' % (host, port))
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.connect((host, port))
            data = s.recv(512)
            log('received bytes from other digsby process: %r' % (data, ))
            if data != 'ok':
                return False
    except Exception:
        print_exc()
        return False
    else:
        return True

class InstanceChecker(object):
    '''
    Class for calling a given function (defaults to Raise) on a given frame
    when another instance of program starts.
    '''

    default_port = 8791

    def __init__( self, name, host, port, frame = None, func = None ):
        self.name = name
        self.frame = frame
        self.port = port
        self.host = host
        self.logger = logging.getLogger( "" )
        if not func:
            self.func = lambda: wx.CallAfter(self.__raiseFrame)

        self.s_checker = wx.SingleInstanceChecker( self.name )

    def startServer( self ):
        '''
        This is a small server on its own thread that waits for a connection
        and once it recieves it calls the function passed into it. Defaults to
        __raiseFrame.
        '''
        self.logger.info( "Server stuff" )

        self._quit_cv = threading.Condition()
        self.server = ServerThread(self.host, self.port, self.func, cv=self._quit_cv)

        try:
            with self._quit_cv:
                self.server.start()
                while self.server.status == SERVER_NOT_STARTED:
                    self._quit_cv.wait()

                if self.server.status == SERVER_PORT_TAKEN:
                    self.logger.info('instance checker port was already taken, quitting')
                    return True

        except Exception, e:
            self.logger.error('Couldn\'t start single instance checker server because: %r', e)
            raise e

    def sendRaisePreviousFrameCommand( self ):
        '''
        Starts up a simple client that opens up a connection on a pre-defined
        port and closes again.
        '''
        self.logger.info('Poking IPC loopback connection')
        return poke_client_port(self.host, self.port)

    def isServerRunning( self ):
        return hasattr(self, 'server') and self.server.isRunning()

    def stopServer(self):
        # Delete the reference to the wxSingleInstanceChecker
        if hasattr(self, 's_checker'):
            del self.s_checker

        if hasattr(self, 'server') and self.server.isRunning():
            self.server.stop()
            return True
        else:
            self.logger.warning( "Tried to stop a server that wasn't running" )
            return False

    def setFrame(self, f):
        self.frame = f

    def setFunc(self, func):
        self.func = func

    def __raiseFrame(self):
        if self.frame is None:
            log('wxApp.SetTopWindow was not called, cannot raise frame')
            return

        # 1) if the window is hidden, show it
        self.frame.Show(True)

        # 2) if the window is minimized, restore it
        self.frame.Iconize(False)

        # 3) bring it to the top of the window hierachy.
        self.frame.Raise()

        # 4) if it's autohidden (and docked), bring it back.
        if hasattr(self.frame, 'ComeBackFromAutoHide'):
            self.frame.ComeBackFromAutoHide()

    def isAnotherRunning( self ):
        return self.s_checker.IsAnotherRunning()

#
#
#

if __name__ == '__main__':
    app = SingleInstanceApp(0)
    f = wx.Frame(None, -1, "This app only runs once!")
    f.Show(True)
    app.SetTopWindow(f)
    app.MainLoop()
