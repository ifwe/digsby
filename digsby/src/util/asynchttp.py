#!/usr/bin/env python
"""Asynchronous HTTP/1.1 client library

This module is an attempt to combine the best features of httplib with
the scalability of asynchat.

I have pasted as much code as I could from httplib (Python 2.0) because it
is a well written and widely used interface. This may be a mistake,
because the behavior of AsynchHTTPConnection os quite different from that of
httplib.HTTPConnection

contact:
Doug Fort <dougfort@downright.com>
Senior Meat Manager
Downright Software LLC
http://www.dougfort.com
"""
__author__="""
Downright Software LLC
http://www.downright.com
"""
__copyright__="""
Copyright (c) 2001 Downright Software LLC. All Rights Reserved.

Distributed and Licensed under the provisions of the Python Open Source License
Agreement which is included by reference. (See 'Front Matter' in the latest
Python documentation)

WARRANTIES
YOU UNDERSTAND AND AGREE THAT:

a. YOUR USE OF THE PACKAGE IS AT YOUR SOLE RISK.  THE PACKAGE IS PROVIDED ON
AN 'AS IS' AND 'AS AVAILABLE' BASIS.  DOWNRIGHT EXPRESSLY DISCLAIMS ALL
WARRANTIES OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING, BUT NOT LIMITED
TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
AND NON-INFRINGEMENT.

b. DOWNRIGHT MAKES NO WARRANTY THAT (1) THE PACKAGE WILL MEET YOUR
REQUIREMENTS, (2) THE PACKAGE WILL BE UNINTERRUPTED, TIMELY, SECURE, OR
ERROR-FREE, (3) THE RESULTS THAT MAY BE OBTAINED FROM THE USE OF THE PACKAGE
WILL BE ACCURATE OR RELIABLE, (4) THE OTHER MATERIAL PURCHASED OR OBTAINED BY
YOU THROUGH THE PACKAGE WILL MEET YOUR EXPECTATIONS,, AND (5) ANY ERRORS IN
THE PACKAGE WILL BE CORRECTED.

c. ANY MATERIALS DOWNLOADED OR OTHERWISE OBTAINED THROUGH THE USE OF THE
PACKAGE IS DONE AT YOUR OWN DISCRETION AND RISK AND THAT YOU WILL BE SOLELY
RESPONSIBLE FOR ANY DAMAGE TO YOUR COMPUTER SYSTEM OR LOSS OF DATA THAT
RESULTS FROM THE DOWNLOAD OF ANY SUCH MATERIAL.

d. NO ADVICE OR INFORMATION, WHETHER ORAL OR WRITTEN, OBTAINED BY YOU FROM
DOWNRIGHT OR THROUGH OR FROM THE PACKAGE SHALL CREATE ANY WARRANTY NOT
EXPRESSLY STATED IN THE TOS.

LIMITATION OF LIABILITY
YOU EXPRESSLY UNDERSTAND AND AGREE THAT DOWNRIGHT SHALL NOT BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL OR EXEMPLARY DAMAGES,
INCLUDING BUT NOT LIMITED TO, DAMAGES FOR LOSS OF PROFITS, GOODWILL, USE,
DATA OR OTHER INTANGIBLE LOSSES (EVEN IF DOWNRIGHT HAS BEEN ADVISED OF SUCH
DAMAGES), RESULTING FROM:
(1) THE USE OR THE INABILITY TO USE THE PACKAGE;
(2) THE COST OF PROCUREMENT OF SUBSTITUTE GOODS AND SERVICES RESULTING FROM
ANY GOODS, DATA, INFORMATION OR SERVICES PURCHASED OR OBTAINED OR MESSAGES
RECEIVED OR TRANSACTIONS ENTERED INTO THROUGH OR FROM THE PACKAGE;
(3) UNAUTHORIZED ACCESS TO OR ALTERATION OF YOUR TRANSMISSIONS OR DATA;
(4) STATEMENTS OF CONDUCT OF ANY THIRD PARTY ON THE PACKAGE; OR
(5) ANY OTHER MATTER RELATING TO THE PACKAGE.
"""
__version__="0.20"

import sys
import asynchat
import asyncore
import socket
import time
import string
import StringIO
import mimetools

HTTP_PORT = 80
HTTPS_PORT = 443

import common

class AsyncHTTPResponse:
    """
    This class attempts to mimic HTTPResponse from httplib.
    The major difference is that it is NOT DYNAMIC:
    All the reading has already been done
    """
    def __init__(self, fp, debuglevel=0):
        """
        This constructor builds everything in the response
        object except the body.  It expects a file object
        containing the header text returnded by the server
        """
        self.fp = fp
        self.debuglevel = debuglevel
        self.msg = None
        self._replyline = ''

        self.status = None
        self.reason = None
        self.version = None

    def _process_response(self):
        # we're expecting something like 'HTTP/1.1 200 OK'
        self._replyline = self.fp.readline()
        if self.debuglevel > 0:
            print "reply: %s" % (self._replyline)

        replylist = string.split(self._replyline, None, 2)

        if len(replylist) == 3:
            version, status, reason = replylist
        elif len(replylist) == 2:
            version, status = replylist
            reason = ""
        else:
            raise BadStatusLine(self._replyline, name=str(self))

        if version[:5] != 'HTTP/':
            raise BadStatusLine(self._replyline, name=str(self))

        try:
            self.code = self.status = int(status)
        except:
            raise BadStatusLine(self._replyline, name=str(self))

        self.reason = string.strip(reason)

        if version == 'HTTP/1.0':
            self.version = 10
        elif version.startswith('HTTP/1.'):
            self.version = 11    # use HTTP/1.1 code for HTTP/1.x where x>=1
        else:
            raise UnknownProtocol(self._replyline, name=str(self))

        self.msg = mimetools.Message(self.fp, 0)
        if self.debuglevel > 0:
            for hdr in self.msg.headers:
                print "header: %s" %  (string.strip(hdr))

        self.error = (self.code//100) != 2

        self.body = None

    def __str__(self):
        return "AsyncHTTPResponse %r" % (self._replyline)

    def getheader(self, name, default=None):
        if self.msg is None:
            raise ResponseNotReady(name=str(self))
        return self.msg.getheader(name, default)

    def getbody(self):
        if self.body is None:
            raise ResponseNotReady(name=str(self))
        return self.body

    def read(self, howmuch=-1):
        return self.fp.read(howmuch)

    def info(self):
        return self.msg

_CHUNK_REQUEST_SIZE = 8192

_STATE_IDLE = "asynchttp._STATE_IDLE"
_STATE_CONNECTING = "asynchttp._STATE_CONNECTING"
_STATE_ACTIVE = "asynchttp._STATE_ACTIVE"
_STATE_ACCEPTING_HEADERS = "asynchttp._STATE_ACCEPTING_HEADERS"
_STATE_REQUESTING_BODY = "asynchttp._STATE_REQUESTING_BODY"
_STATE_CHUNK_START = "asynchttp._STATE_CHUNK_START"
_STATE_CHUNK_BODY = "asynchttp._STATE_CHUNK_BODY"
_STATE_CHUNK_RESIDUE = "asynchttp._STATE_CHUNK_RESIDUE"

class AsyncHTTPConnection(common.socket):

    _http_vsn = 11
    _http_vsn_str = 'HTTP/1.1'

    response_class = AsyncHTTPResponse
    default_port = HTTP_PORT
    auto_open = 1
    debuglevel = 0

    def __init__(self, host=None, port=None):
        # overload asynchat.found_terminator with the function
        # appropriate for each state
        self._TERMINATOR_MAP = {
            _STATE_IDLE : self._no_action,
            _STATE_CONNECTING :  self._no_action,
            _STATE_ACTIVE:  self._no_action,
            _STATE_ACCEPTING_HEADERS:  self._header_data,
            _STATE_REQUESTING_BODY : self._body_data,
            _STATE_CHUNK_START : self._chunk_start_data,
            _STATE_CHUNK_BODY : self._chunk_body_data,
            _STATE_CHUNK_RESIDUE : self._chunk_residue_data
            }
        self.__state = None
        self.__set_state(_STATE_IDLE)

        # we accumulate headers in a dictionary so the
        # caller can write over the headers we supply
        # (or their own headers if  they want)
        self._headerdict = {}
        self._requestfp = None
        self._responsefp = StringIO.StringIO()
        self._chunkfp = None

        self.response = self.response_class(
            self._responsefp,
            self.debuglevel
            )

        self._set_hostport(host, port)
        self._willclose = 0

        import primitives.funcs as funcs
        self._on_connect = funcs.Delegate()
        common.socket.__init__(self, False)

    def _set_hostport(self, host, port):
        if host and port is None:
            i = string.find(host, ':')
            if i >= 0:
                port = int(host[i+1:])
                host = host[:i]
            else:
                port = self.default_port

        self.host = host
        self.port = port

    def set_debuglevel(self, level):
        self.debuglevel = level

    def connect(self):
        """
        Connect to the host and port specified in __init__.
        Add ourselves to thhe asyncore polling group
        """
        self.__set_state(_STATE_CONNECTING)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.debuglevel > 0:
            print "connecting: (%s, %s)" % (self.host, self.port)

        import util.net as net, socks
        pi = net.GetProxyInfo()
        use_proxy = True
        host, port = self.host, self.port
        if pi.get('proxytype', 0) == socks.PROXY_TYPE_HTTP:
            # Don't use ProxySockets, let urllib2 handle proxy info
            use_proxy = False

        common.socket.connect(self, (host, port), use_proxy = use_proxy, error = self.handle_error)

    def close(self):
        """
        Close the connection to the HTTP server.
        And remove ourselves from the asyncore polling group
        """
        if self.debuglevel > 0:
            print "asynchttp.close() (%s, %s)" % (self.host, self.port)

        self.connected = 0

        if self.socket:
            common.socket.close(self)

        self._set_hostport(None, None)

    def send_entity(self, str):
        """
        Send `str' to the server.
        Actually, we  just append str to the block of text to  be sent
        to the server when getresponse is called.

        Note:  the name was changed from httplib's 'HTTPConnection.send()'
        because it conflicts with asynchat
        """
        if self.debuglevel > 0:
            print "send_entity %r" % str

        self._requestfp.write(str)

    def putrequest(self, method, url):
        """Send a request to the server.

        `method' specifies an HTTP request method, e.g. 'GET'.
        `url' specifies the object being requested, e.g. '/index.html'.

        This function actually only starts accumulating the request:
        nothing gets sent to the server until getresponse() is called.
        """
        if self.debuglevel > 0:
            print "putrequest %s %s" % (method, url)

        if not self.__state is _STATE_ACTIVE:
            raise RequestNotReady(
                "Invalid putrequest() %s" % (self.__state),
                name=str(self)
                )

        self._requestfp = StringIO.StringIO()

        if not url:
            url = '/'
        self._requestfp.write(
            '%s %s %s\r\n' % (method, url, self._http_vsn_str)
            )

        if self._http_vsn == 11:
            # Issue some standard headers for better HTTP/1.1 compliance

            # this header is issued *only* for HTTP/1.1 connections. more
            # specifically, this means it is only issued when the client uses
            # the new HTTPConnection() class. backwards-compat clients will
            # be using HTTP/1.0 and those clients may be issuing this header
            # themselves. we should NOT issue it twice; some web servers (such
            # as Apache) barf when they see two Host: headers
            self.putheader('Host', self.host)

            # note: we are assuming that clients will not attempt to set these
            #       headers since *this* library must deal with the
            #       consequences. this also means that when the supporting
            #       libraries are updated to recognize other forms, then this
            #       code should be changed (removed or updated).

            # we only want a Content-Encoding of "identity" since we don't
            # support encodings such as x-gzip or x-deflate.
            self.putheader('Accept-Encoding', 'identity')

            # we can accept "chunked" Transfer-Encodings, but no others
            # NOTE: no TE header implies *only* "chunked"
            #self.putheader('TE', 'chunked')

            # if TE is supplied in the header, then it must appear in a
            # Connection header.
            #self.putheader('Connection', 'TE')

    def putheader(self, header, value):
        """
        Send a request header line to the server.

        For example: h.putheader('Accept', 'text/html')
        We don't actually send the header here, we stick it
        in a dictionary, to be sent when getresponse() is
        called.  If you call putheader() with a duplicate
        key, it will wipe out the existing entry.
        """
        if self.debuglevel > 0:
            print "putheader %s: %s" % (header, value)

        self._headerdict[header] = value

    def endheaders(self):
        """
        Indicate that the last header line has been sent to the server.
        Actually, we just copy the header dictionary into the request
        stream to be sent when getresponse() is called.
        """

        if not self.__state is _STATE_ACTIVE:
            self._on_connect += self.endheaders
            return

        if self.debuglevel > 0:
            print "endheaders"

        for header, value in self._headerdict.items():
            self._requestfp.write(
                '%s: %s\r\n' % (header, value)
                )
        # store a blank line to indicate end of headers
        self._requestfp.write('\r\n')

    def request(self, method, url, body=None, headers={}):
        """
        Send a complete request to the server.
        """
        if self.debuglevel > 0:
            print "request"

        if not self.__state is _STATE_ACTIVE:
            self._on_connect += lambda: self.request(method, url, body, headers)
            return

        self._send_request(method, url, body, headers)

    def _send_request(self, method, url, body, headers):
        if self.debuglevel > 0:
            print "_send_request"

        self.putrequest(method, url)

        if body:
            self.putheader('Content-Length', str(len(body)))

        for hdr, value in headers.items():
            self.putheader(hdr, value)

        self.endheaders()

        if body:
            self.send_entity(body)

    def getresponse(self):
        """
        Get the response from the server.
        This  actually starts the process of sending the request
        to the server.  The response will be delivered in handle_response
        """
        if not self.__state is _STATE_ACTIVE:
            self._on_connect += self.getresponse
            return self.response

        self.__set_state(_STATE_ACCEPTING_HEADERS)

        self.push(self._requestfp.getvalue())

        self._requestfp = None

        # exit this state on a blank line
        self.set_terminator("\r\n\r\n")

        return self.response

    def handle_connect(self):
        """
        Notification from asyncore that we are connected
        """
        self.__set_state(_STATE_ACTIVE)
        if self.debuglevel > 0:
            print "connected: (%s, %s)" % (self.host, self.port)

        self._on_connect.call_and_clear()

    def handle_close(self):
        """
        Notification from asyncore that the server has closed
        its end of the connection.
        If auto_open is TRUE, we will attempt to reopen the
        connection.
        """
        if self.debuglevel > 0:
            print "closed by server: (%s, %s) %s" % (
                self.host, self.port, self.__state
                )

        common.socket.handle_close(self)
        self.close()
        # 2001-03-14 djf If the server closed the connection while we're
        # requesting body data, it  may just be trying to tell us that
        # we're done
        if self.__state in [
            _STATE_REQUESTING_BODY,
            _STATE_CHUNK_BODY,
            _STATE_CHUNK_RESIDUE
            ]:
            self.found_terminator()
            return

        # if auto_open, attempt to reopen the connection
#        if self.auto_open and self.host:
#            self.connect()

    def handle_error(self, why=None):
        """
        Overload asyncore's exception handling
        """
        self.__set_state(_STATE_IDLE)
        common.socket.handle_error(self, why)

    def collect_incoming_data(self, data):
        """
        asynchat calls this with data as it comes in
        """
        if not self._responsefp:
            raise UnexpectedData(
                "%s '%s' '%s' '%s'" % (
                self.__state,
                data,
                self.get_terminator(),
                self.ac_in_buffer
                ), name=str(self))

        self._responsefp.write(data)

    def _no_action(self):
        """
        overload asynchat.found_terminator
        This function will only be called when someone is badly confused
        """
        raise UnexpectedTerminator(
            "%s '%s'" % (self.__state, self.get_terminator()),
            name=str(self)
            )

    def _header_data(self):
        """
        overload asynchat.found_terminator for
        _STATE_ACCEPTING_HEADERS
        We assume that we have hit the blank line terminator after the
        HTTP response headers.
        """
        self._responsefp.seek(0)
        self.response._process_response()
        self._willclose = string.lower(
            self.response.getheader("connection", "")
            ) == "close"

        transferencoding = string.lower(
            self.response.getheader("transfer-encoding", "")
            )

        # set up for getting the body
        self._responsefp = StringIO.StringIO()

        if transferencoding:
            if transferencoding == "chunked":
                self._chunkfp = StringIO.StringIO()
                self.set_terminator("\r\n")
                self.__set_state(_STATE_CHUNK_START)
                return

            raise UnknownTransferEncoding(
                self.response.getheader("transfer-encoding", ""),
                name=str(self)
                )

        contentlengthstr = self.response.getheader(
            "content-length", None
            )
        if contentlengthstr:
            contentlength = int(contentlengthstr)
        else:
            contentlength = None

        self.set_terminator(contentlength)
        self.__set_state(_STATE_REQUESTING_BODY)

    def _body_data(self):
        """
        overload asynchat.found_terminator for
        _STATE_REQUESTING_BODY
        We assume that we have the full body text
        """
        self.response.body = self._responsefp.getvalue()
        self._responsefp = None

        if self._willclose:
            self.close()

        self.__set_state(_STATE_ACTIVE)

        # hand off the response object to the child class
        self.handle_response()

    def _get_chunk_size(self):
        """
        Assume that chunkbuffer contains some text, begining with
        a line containing the chunk size in hex.
        """
        # 2001-03-26 djf -- kludge alert! We shouldn't have to lstrip
        # here, but sometimes we get extra whitespace
        splitlist = self._chunkbuffer.lstrip().split("\r\n",1)
        if len(splitlist) == 1:
            chunkline, self._chunkbuffer = splitlist[0], ''
        else:
            chunkline, self._chunkbuffer = splitlist

        i = string.find(chunkline, ';')
        if i >= 0:
            chunkline = chunkline[:i]    # strip chunk-extensions

        try:
            chunksize = string.atoi(chunkline, 16)
        except:
            raise InvalidChunk(
                "Can't compute chunk size from '%s' '%s'" % (
                chunkline, self._chunkbuffer
                ))

        if self.debuglevel > 0:
            print "chunksize = '%d" % (chunksize)

        return chunksize

    def _chunk_start_data(self):
        """
        overload asynchat.found_terminator for
        _STATE_CHUNKED_START
        Assumes we got a hit on terminator '\r\n'
        """
        self._chunkbuffer = self._responsefp.getvalue()
        self._chunksize = self._get_chunk_size()
        if self._chunksize == 0:
            if self.debuglevel > 0:
                print "0 size Chunk: ending chunk processing"
            self.response.body = self._chunkfp.getvalue()
            self._chunkfp = None
            self.set_terminator("\r\n\r\n")
            self._responsefp = StringIO.StringIO()
            self.__set_state(_STATE_CHUNK_RESIDUE)
            return

        self.set_terminator(self._chunksize+2)
        self._responsefp = StringIO.StringIO()
        self.__set_state(_STATE_CHUNK_BODY)

    def _chunk_body_data(self):
        """
        overload asynchat.found_terminator for
        _STATE_CHUNK_BODY
        """
        self._chunkbuffer += self._responsefp.getvalue()

        while self._chunkbuffer:
            chunk_plus_crlf_size = self._chunksize+2
            if len(self._chunkbuffer) > chunk_plus_crlf_size:
                chunkbody = self._chunkbuffer[:chunk_plus_crlf_size]
                self._chunkbuffer = self._chunkbuffer[chunk_plus_crlf_size:]
                self._chunkbuffer = self._chunkbuffer.lstrip()
            else:
                chunkbody = self._chunkbuffer
                self._chunkbuffer = ''

            self._chunkfp.write(chunkbody)

            if not self._chunkbuffer:
                break

            #if we have some text left over, we hope it's another chunk,
            # but if it doesn't contain a newline, it is insufficient
            if self._chunkbuffer.find("\r\n") < 0:
                self._responsefp = StringIO.StringIO()
                self.set_terminator("\r\n")
                self.__set_state(_STATE_CHUNK_START)
                return

            self._chunksize = self._get_chunk_size()
            if self._chunksize == 0:
                if self.debuglevel > 0:
                    print "0 size Chunk: ending chunk processing"
                self.response.body = self._chunkfp.getvalue()
                self._chunkfp = None

                # if there's still something in the buffer,
                # assume it's  the chunk residue (probably just
                # '\r\n'
                if self._chunkbuffer:
                    self._chunkbuffer = "" # discard the residue
                    self.__set_state(_STATE_ACTIVE)

                    if self._willclose:
                        self.close()

                    # hand off the response object to the child class
                    self.handle_response()
                    return

                # we've handled the whole chunk, but the server could
                # send entity headers. It should  at least send
                # a final '\r\n'
                self.set_terminator("\r\n\r\n")
                self._responsefp = StringIO.StringIO()
                self.__set_state(_STATE_CHUNK_RESIDUE)
                return

            # We have a nonzero chunksize, if we have less than
            # the specified number of bytes in the buffer, we need
            # to  read some more
            chunk_plus_crlf_size = self._chunksize+2
            bufsize = len(self._chunkbuffer)
            if bufsize < chunk_plus_crlf_size:
                self.set_terminator(chunk_plus_crlf_size - bufsize)
                self._responsefp = StringIO.StringIO()
                self.__set_state(_STATE_CHUNK_BODY)
                return

            # if we made it this far, we should have a chunk size and
            # at least enough in the buffer to satisfy it. So we loop
            # back to the top of the while.

        # we don't have any text left over, but we haven't hit a
        # zero chunk. See if the server will give us another line
        self._responsefp = StringIO.StringIO()
        self.set_terminator("\r\n")
        self.__set_state(_STATE_CHUNK_START)

    def _chunk_residue_data(self):
        """
        overload asynchat.found_terminator for
        _STATE_CHUNK_RESIDUE
        """
        residue = string.strip(self._responsefp.getvalue())
        if self.debuglevel > 0 and residue:
            print "chunk residue '%s'" % (residue)

        self._responsefp = None

        if self._willclose:
            self.close()

        self.__set_state(_STATE_ACTIVE)

        # hand off the response object to the child class
        self.handle_response()

    def handle_response(self):
        """
        This is an abstract function, the  user MUST overload it
        """
        raise HandleResponse(
            "Call to AsyncHTTPConnection.handle_response", name=str(self)
            )

    def __set_state(self, next_state):
        """
        Change state be setting _found_terminator
        """
        if self.debuglevel > 0:
            print "%s to %s" % (self.__state, next_state)
        self.__state = next_state
        self.found_terminator = self._TERMINATOR_MAP[self.__state]

class AsyncHTTPException(Exception):
    def __init__(self, message="", name=""):
        self._message = message
        self._name = name

    def __str__(self):
        return "%s %s" % (self._name, self._message)

class NotConnected(AsyncHTTPException):
    pass

class UnknownProtocol(AsyncHTTPException):
    pass

class UnknownTransferEncoding(AsyncHTTPException):
    pass

class BadStatusLine(AsyncHTTPException):
    pass

class ImproperConnectionState(AsyncHTTPException):
    pass

class RequestNotReady(ImproperConnectionState):
    pass

class ResponseNotReady(ImproperConnectionState):
    pass

class HandleResponse(ImproperConnectionState):
    pass

class UnexpectedData(AsyncHTTPException):
    pass

class UnexpectedTerminator(AsyncHTTPException):
    pass

class InvalidChunk(AsyncHTTPException):
    pass

class __test_AsyncHTTPConnection(AsyncHTTPConnection):
    def __init__(self, host, port, url):
        AsyncHTTPConnection.__init__(
            self, host, port
            )
        self._url = url

    def handle_response(self):
        self.close()

    def handle_connect(self):
        print "__test_AsyncHTTPConnection.handle_connect"
        AsyncHTTPConnection.handle_connect(self)
        self.putrequest("GET", self._url)
        self.endheaders()
        self.getresponse()

if __name__ == "__main__":
    """
    Code for commandline testing
    """
    if len(sys.argv) < 4:
        print "Usage:  asynchttp.py <host> <port> <request>"
        print "\t\tUsing www.google.com 80 '/'"
        sys.argv[1:] = ['www.google.com', '80', '/']

    tester = __test_AsyncHTTPConnection(
        sys.argv[1],
        int(sys.argv[2]),
        sys.argv[3]
        )
    tester.set_debuglevel(1)
    tester.connect()

    asyncore.loop()

    if not hasattr(tester, "response"):
        print "No rsponse"
        sys.exit(-1)

    print "results %s %d %s" % (
        tester.response.version,
        tester.response.status,
        tester.response.reason
        )

    print "headers:"
    for hdr in tester.response.msg.headers:
        print "%s" %  (string.strip(hdr))

    if tester.response.status == 200:
        print "body:"
        print tester.response.body
