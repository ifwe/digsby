'''
Monkeypatches are made in these files:

urllib.py
    - URLopener.open_data: the original function uses %T in a call to strftime,
      which doesn't exist (at least on windows)
    - the addbase class: replaced with one that has a tell method
    - OneProxy / getproxies_registry

urllib2.py
    - ProxyHandler: "Proxy-Authorization" case change, and later binding for
      proxy objects
'''

from __future__ import with_statement

#############################################
import urllib
#############################################

import base64
import mimetools
import os
import time
import httplib



import os
if os.name == 'nt':

    # The Subprocess module uses CreateProcess with bInheritHandles = TRUE
    # so that it can redirect stdout, stdin, and stderr. Unfortunately this
    # means that the subprocess also inherits all of our sockets. If
    # the process is long living, it will keep those sockets connected.
    #
    # These method patches use the kernel32.dll function SetHandleInformation
    # to make all new sockets uninheritable.
    #
    # TODO: Note that if another thread spawns a process in between the socket
    # creation and the call to SetHandleInformation, we're still out of luck.

    from msvcrt import get_osfhandle
    from ctypes import windll, WinError
    SetHandleInformation = windll.kernel32.SetHandleInformation

    if __debug__:
        def set_noninheritable(socket):
            if not SetHandleInformation(socket.fileno(), 1, 0):
                raise WinError()
    else:
        # don't raise WinErrors on release mode.
        def set_noninheritable(socket):
            SetHandleInformation(socket.fileno(), 1, 0)

    import socket
    original_socket = socket.socket
    _orig_connect    = original_socket.connect
    _orig_connect_ex = original_socket.connect_ex
    _orig_accept     = original_socket.accept

    def connect(self, address):
        res = _orig_connect(self, address)
        set_noninheritable(self)
        return res

    def connect_ex(self, address):
        res = _orig_connect_ex(self, address)
        set_noninheritable(self)
        return res

    def accept(self):
        conn, addr = _orig_accept(self)
        set_noninheritable(conn)
        return conn, addr

    original_socket.connect    = connect
    original_socket.connect_ex = connect_ex
    original_socket.accept     = accept

def open_data(self, url, data=None):
    """Use "data" URL."""
    if not isinstance(url, str):
        raise IOError, ('data error', 'proxy support for data protocol currently not implemented')
    # ignore POSTed data
    #
    # syntax of data URLs:
    # dataurl   := "data:" [ mediatype ] [ ";base64" ] "," data
    # mediatype := [ type "/" subtype ] *( ";" parameter )
    # data      := *urlchar
    # parameter := attribute "=" value
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    try:
        [type, data] = url.split(',', 1)
    except ValueError:
        raise IOError, ('data error', 'bad data URL')
    if not type:
        type = 'text/plain;charset=US-ASCII'
    semi = type.rfind(';')
    if semi >= 0 and '=' not in type[semi:]:
        encoding = type[semi+1:]
        type = type[:semi]
    else:
        encoding = ''
    msg = []
    msg.append('Date: %s'% time.strftime('%a, %d %b %Y %H:%M:%S GMT',
                                        time.gmtime(time.time())))
    msg.append('Content-type: %s' % type)
    if encoding == 'base64':
        data = base64.decodestring(data)
    else:
        data = urllib.unquote(data)
    msg.append('Content-Length: %d' % len(data))
    msg.append('')
    msg.append(data)
    msg = '\n'.join(msg)
    f = StringIO(msg)
    headers = mimetools.Message(f, 0)
    #f.fileno = None     # needed for addinfourl
    return urllib.addinfourl(f, headers, url)

urllib.URLopener.open_data = open_data

# Methods to be patched into urllib.addbase

def ab___init__(self, fp):
    self.fp = fp
    self._amt_read = 0
    if hasattr(self.fp, "readlines"): self.readlines = self.fp.readlines
    if hasattr(self.fp, "fileno"):
        self.fileno = self.fp.fileno
    else:
        self.fileno = lambda: None
    if hasattr(self.fp, "__iter__"):
        self.__iter__ = self.fp.__iter__
        if hasattr(self.fp, "next"):
            self.next = self.fp.next

def ab_read(self, *a, **k):
    v = self.fp.read(*a, **k)
    self._amt_read += len(v)
    return v
def ab_readline(self, *a, **k):
    v = self.fp.readline(*a, **k)
    self._amt_read += len(v)
    return v

def ab_tell(self):
    return self._amt_read

def ab___repr__(self):
    return '<%s at %r whose fp = %r>' % (self.__class__.__name__,
                                         id(self), self.fp)

def ab_close(self):
    self._amt_read = 0
    self.read = None
    self.readline = None
    self.readlines = None
    self.fileno = None
    if self.fp: self.fp.close()
    self.fp = None

for meth in '__init__ read readline tell __repr__ close'.split():
    setattr(urllib.addbase, meth, globals()['ab_' + meth])

#
#urllib.addbase = addbase

if os.name == 'nt':
    class OneProxy(dict):
        @property
        def proxyServer(self):
            return self._proxyServer
        def __missing__(self, key):
            val = '%s://%s' % (key, self.proxyServer)
            self.__setitem__(key, val)
            return val


    def getproxies_registry():
        """Return a dictionary of scheme -> proxy server URL mappings.

        Win32 uses the registry to store proxies.

        """
        proxies = {}
        try:
            import _winreg
        except ImportError:
            # Std module, so should be around - but you never know!
            return proxies
        try:
            internetSettings = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Internet Settings')
            proxyEnable = _winreg.QueryValueEx(internetSettings,
                                               'ProxyEnable')[0]
            if proxyEnable:
                # Returned as Unicode but problems if not converted to ASCII
                proxyServer = str(_winreg.QueryValueEx(internetSettings,
                                                       'ProxyServer')[0])
                if '=' in proxyServer:
                    # Per-protocol settings
                    for p in proxyServer.split(';'):
                        protocol, address = p.split('=', 1)
                        # See if address has a type:// prefix
                        import re
                        if not re.match('^([^/:]+)://', address):
                            address = '%s://%s' % (protocol, address)
                        proxies[protocol] = address
                else:
                    # Use one setting for all protocols
                    if proxyServer[:5] == 'http:':
                        proxies['http'] = proxyServer
                    else:
                        proxies = OneProxy()
                        proxies._proxyServer = proxyServer

                        # these 2 lines put the keys/values
                        proxies['https']
                        proxies['http']
                        proxies['ftp']

            internetSettings.Close()
        except (WindowsError, ValueError, TypeError):
            # Either registry key not found etc, or the value in an
            # unexpected format.
            # proxies already set up to be empty so nothing to do
            pass
        return proxies

    urllib.OneProxy = OneProxy
    urllib.getproxies_registry = getproxies_registry

######################################
import urllib2
######################################


class ProxyHandler(urllib2.BaseHandler):
    # Proxies must be in front
    handler_order = 100

    def __init__(self, proxies=None):
        self._proxies = proxies

    def _get_proxies(self):
        import urllib
        return self._proxies or urllib.getproxies()

    def _set_proxies(self, val):
        self._proxies = val

    proxies = property(_get_proxies, _set_proxies)

    def http_open(self, req):
        return self.proxy_open(req, 'http')

    def https_open(self, req):
        return self.proxy_open(req, 'https')

    def ftp_open(self, req):
        return self.proxy_open(req, 'ftp')

    def proxy_open(self, req, type):
        orig_type = req.get_type()
        try:
            proxy = self.proxies[type]
        except KeyError:
            return None

        proxy_type, user, password, hostport = urllib2._parse_proxy(proxy)
        if proxy_type is None:
            proxy_type = orig_type
        if user and password:
            user_pass = '%s:%s' % (urllib2.unquote(user), urllib2.unquote(password))
            creds = base64.b64encode(user_pass).strip()
            req.add_header('Proxy-Authorization', 'Basic ' + creds)

        hostport = urllib2.unquote(hostport)
        req.set_proxy(hostport, proxy_type)
        if orig_type == proxy_type:
            # let other handlers take care of it
            return None
        else:
            # need to start over, because the other handlers don't
            # grok the proxy's URL type
            # e.g. if we have a constructor arg proxies like so:
            # {'http': 'ftp://proxy.example.com'}, we may end up turning
            # a request for http://acme.example.com/a into one for
            # ftp://proxy.example.com/a
            return self.parent.open(req)

urllib2.ProxyHandler = ProxyHandler

# FileHandler, the class to handle local file:// urls, attempts FTP if
# the url doesn't quite look like a file:// url (that is, if it doesn't
# have the right number of slashes).
#
# Defaulting to FTP when trying to open a localfile is not a good idea.
def _no_ftp_file_open(self, req):
    return self.open_local_file(req)

urllib2.FileHandler.file_open = _no_ftp_file_open

# Now, a new build_opener to replace urllib2's.
# The difference here is that you can specify opener_class by keyword
# and use an OpenerDirector subclass (or something). This is exactly copy/pasted
# from python 2.5.1 urllib2, with the exception of:
#  * the function takes **kwds and gets the opener class to instantiate from there
#  * default_classes are accessible from OUTSIDE of the function, in case they need to be modified.
#  * default classes are also modifiable via a keyword argument.

urllib2.default_opener_classes = map(
    lambda x: getattr(urllib2, x),
    ('UnknownHandler',
     'HTTPHandler',
     'HTTPDefaultErrorHandler',
     'HTTPRedirectHandler',
     'FTPHandler',
     'FileHandler',
     'HTTPErrorProcessor'
     ))

def build_opener(*handlers, **kwds):
    """Create an opener object from a list of handlers.

    The opener will use several default handlers, including support
    for HTTP and FTP.

    If any of the handlers passed as arguments are subclasses of the
    default handlers, the default handlers will not be used.
    """
    import types

    opener_class = kwds.pop('opener_class', urllib2.OpenerDirector)
    classes = kwds.pop('default_classes', urllib2.default_opener_classes)[:]

    if kwds:
        raise TypeError("Only opener_class and default_classes are accepted as keyword arguments for build_opener")

    def isclass(obj):
        return isinstance(obj, types.ClassType) or hasattr(obj, "__bases__")

    opener = opener_class()

    if hasattr(httplib, 'HTTPS'):
        classes.append(urllib2.HTTPSHandler)
    skip = []
    for klass in classes:
        for check in handlers:
            if isclass(check):
                if isclass(klass) and issubclass(check, klass):
                    skip.append(klass)
                elif not isclass(klass) and issubclass(check, type(klass)):
                    skip.append(klass)
            elif isinstance(check, type(klass)):
                skip.append(klass)
            elif isclass(klass) and isinstance(check, klass):
                skip.append(klass)

    for klass in skip:
        classes.remove(klass)

    for klass in classes:
        try:
            instance = klass()
        except (AttributeError, TypeError):
            instance = klass
        opener.add_handler(instance)

    for h in handlers:
        if isclass(h):
            h = h()
        opener.add_handler(h)
    return opener

urllib2.build_opener = build_opener

#
# asynchat monkeypatches
#
# the only thing that's changed from the standard library impl is to pass
# the exception object to handle_error
#

import socket
from asynchat import find_prefix_at_end
import sys

if sys.hexversion > 0x02060000:
    def handle_read (self):

        try:
            data = self.recv (self.ac_in_buffer_size)
        except socket.error, why:
            self.handle_error(why)
            return

        self.ac_in_buffer = self.ac_in_buffer + data

        # Continue to search for self.terminator in self.ac_in_buffer,
        # while calling self.collect_incoming_data.  The while loop
        # is necessary because we might read several data+terminator
        # combos with a single recv(4096).

        while self.ac_in_buffer:
            lb = len(self.ac_in_buffer)
            terminator = self.get_terminator()
            if not terminator:
                # no terminator, collect it all
                self.collect_incoming_data (self.ac_in_buffer)
                self.ac_in_buffer = ''
            elif isinstance(terminator, int) or isinstance(terminator, long):
                # numeric terminator
                n = terminator
                if lb < n:
                    self.collect_incoming_data (self.ac_in_buffer)
                    self.ac_in_buffer = ''
                    self.terminator = self.terminator - lb
                else:
                    self.collect_incoming_data (self.ac_in_buffer[:n])
                    self.ac_in_buffer = self.ac_in_buffer[n:]
                    self.terminator = 0
                    self.found_terminator()
            else:
                # 3 cases:
                # 1) end of buffer matches terminator exactly:
                #    collect data, transition
                # 2) end of buffer matches some prefix:
                #    collect data to the prefix
                # 3) end of buffer does not match any prefix:
                #    collect data
                terminator_len = len(terminator)
                index = self.ac_in_buffer.find(terminator)
                if index != -1:
                    # we found the terminator
                    if index > 0:
                        # don't bother reporting the empty string (source of subtle bugs)
                        self.collect_incoming_data (self.ac_in_buffer[:index])
                    self.ac_in_buffer = self.ac_in_buffer[index+terminator_len:]
                    # This does the Right Thing if the terminator is changed here.
                    self.found_terminator()
                else:
                    # check for a prefix of the terminator
                    index = find_prefix_at_end (self.ac_in_buffer, terminator)
                    if index:
                        if index != lb:
                            # we found a prefix, collect up to the prefix
                            self.collect_incoming_data (self.ac_in_buffer[:-index])
                            self.ac_in_buffer = self.ac_in_buffer[-index:]
                        break
                    else:
                        # no prefix, collect it all
                        self.collect_incoming_data (self.ac_in_buffer)
                        self.ac_in_buffer = ''

    from sys import py3kwarning
    from warnings import filterwarnings, catch_warnings

    def initiate_send(self):
        while self.producer_fifo and self.connected:
            first = self.producer_fifo.popleft()
            # handle empty string/buffer or None entry
            if not first:
                if first is None:
                    self.handle_close()
                    return

            # handle classic producer behavior
            obs = self.ac_out_buffer_size
            try:
                with catch_warnings():
                    if py3kwarning:
                        filterwarnings("ignore", ".*buffer", DeprecationWarning)
                    data = buffer(first, 0, obs)
            except TypeError:
                data = first.more()
                if data is not None:
                    self.producer_fifo.appendleft(first)

                if data:
                    self.producer_fifo.appendleft(data)
                continue

            # send the data
            try:
                num_sent = self.send(data)
            except socket.error, why:
                self.handle_error(why)
                self.producer_fifo.appendleft(first)
                return

            if num_sent:
                if num_sent < len(data) or obs < len(first):
                    self.producer_fifo.appendleft(first[num_sent:])
            # we tried to send some actual data
            return
else: #sys.hexversion > 0x02060000

    def handle_read (self):

        try:
            data = self.recv (self.ac_in_buffer_size)
        except socket.error, why:
            self.handle_error(why)
            return

        self.ac_in_buffer = self.ac_in_buffer + data

        # Continue to search for self.terminator in self.ac_in_buffer,
        # while calling self.collect_incoming_data.  The while loop
        # is necessary because we might read several data+terminator
        # combos with a single recv(1024).

        while self.ac_in_buffer:
            lb = len(self.ac_in_buffer)
            terminator = self.get_terminator()
            if not terminator:
                # no terminator, collect it all
                self.collect_incoming_data (self.ac_in_buffer)
                self.ac_in_buffer = ''
            elif isinstance(terminator, int) or isinstance(terminator, long):
                # numeric terminator
                n = terminator
                if lb < n:
                    self.collect_incoming_data (self.ac_in_buffer)
                    self.ac_in_buffer = ''
                    self.terminator = self.terminator - lb
                else:
                    self.collect_incoming_data (self.ac_in_buffer[:n])
                    self.ac_in_buffer = self.ac_in_buffer[n:]
                    self.terminator = 0
                    self.found_terminator()
            else:
                # 3 cases:
                # 1) end of buffer matches terminator exactly:
                #    collect data, transition
                # 2) end of buffer matches some prefix:
                #    collect data to the prefix
                # 3) end of buffer does not match any prefix:
                #    collect data
                terminator_len = len(terminator)
                index = self.ac_in_buffer.find(terminator)
                if index != -1:
                    # we found the terminator
                    if index > 0:
                        # don't bother reporting the empty string (source of subtle bugs)
                        self.collect_incoming_data (self.ac_in_buffer[:index])
                    self.ac_in_buffer = self.ac_in_buffer[index+terminator_len:]
                    # This does the Right Thing if the terminator is changed here.
                    self.found_terminator()
                else:
                    # check for a prefix of the terminator
                    index = find_prefix_at_end (self.ac_in_buffer, terminator)
                    if index:
                        if index != lb:
                            # we found a prefix, collect up to the prefix
                            self.collect_incoming_data (self.ac_in_buffer[:-index])
                            self.ac_in_buffer = self.ac_in_buffer[-index:]
                        break
                    else:
                        # no prefix, collect it all
                        self.collect_incoming_data (self.ac_in_buffer)
                        self.ac_in_buffer = ''

    def initiate_send (self):
        obs = self.ac_out_buffer_size
        # try to refill the buffer
        if (len (self.ac_out_buffer) < obs):
            self.refill_buffer()

        if self.ac_out_buffer and self.connected:
            # try to send the buffer
            try:
                num_sent = self.send (self.ac_out_buffer[:obs])
                if num_sent:
                    self.ac_out_buffer = self.ac_out_buffer[num_sent:]

            except socket.error, why:
                self.handle_error(why)
                return


import asynchat
asynchat.async_chat.handle_read = handle_read
asynchat.async_chat.initiate_send = initiate_send
del handle_read, initiate_send

def dispatcher_getattr(self, attr):
    if attr == 'socket':
        return object.__getattribute__(self, 'socket')
    return getattr(self.socket, attr)

import asyncore
asyncore.dispatcher.__getattr__ = dispatcher_getattr
del dispatcher_getattr

def make_request(cls, full_url, data=None, *a, **k):
    '''
    Convenience constructor, you can provide a (possibly full) URL (and data, optionally)
    or another request.
    '''
    # construct a urllib2.Request object, set appropriate headers for connection, and return it
    if not isinstance(full_url, cls):
        default_host = k.pop('default_host', None)
        ssl = k.pop('ssl', False)

        proto = 'http%s' % ('s' if ssl else '')

        if default_host and not (full_url.startswith(proto) or full_url.startswith(default_host)):
            proto_host = ('%s://%s' % (proto, default_host.rstrip('/')))
            full_url = proto_host + '/' + full_url.lstrip('/')
        if not full_url.startswith(proto):
            full_url = ('%s://%s' % (proto, full_url))

        req = cls(full_url, *a, **k)
    else:
        req = full_url

    if data is not None:
        if not isinstance(data, str):
            data = urllib.urlencode(data)

        req.add_data(data)

    return req

urllib2.Request.make_request = classmethod(make_request)
