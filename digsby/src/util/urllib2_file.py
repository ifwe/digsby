#!/usr/bin/env python
####
# Version: 0.2.0
#  - UTF-8 filenames are now allowed (Eli Golovinsky)<br/>
#  - File object is no more mandatory, Object only needs to have seek() read() attributes (Eli Golovinsky)<br/>
#
# Version: 0.1.0
#  - upload is now done with chunks (Adam Ambrose)
#
# Version: older
# THANKS TO:
# bug fix: kosh @T aesaeion.com
# HTTPS support : Ryan Grow <ryangrow @T yahoo.com>
# Copyright (C) 2004,2005,2006 Fabien SEISEN
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# you can contact me at: <fabien@seisen.org>
# http://fabien.seisen.org/python/
#
# Also modified by Adam Ambrose (aambrose @T pacbell.net) to write data in
# chunks (hardcoded to CHUNK_SIZE for now), so the entire contents of the file
# don't need to be kept in memory.

"""
enable to upload files using multipart/form-data

idea from:
upload files in python:
 http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306

timeoutsocket.py: overriding Python socket API:
 http://www.timo-tasi.org/python/timeoutsocket.py
 http://mail.python.org/pipermail/python-announce-list/2001-December/001095.html

import urllib2_files
import urllib2
u = urllib2.urlopen('http://site.com/path' [, data])

data can be a mapping object or a sequence of two-elements tuples
(like in original urllib2.urlopen())
varname still need to be a string and
value can be string of a file object
eg:
  ((varname, value),
   (varname2, value),
  )
  or
  { name:  value,
    name2: value2
  }

"""

from urllib2 import URLError
from urllib import splittype
from urllib import splithost
from httplib import NotConnected
from urllib import addinfourl

import os
import socket
import sys
import stat
import mimetypes
import mimetools
import httplib
import urllib
import urllib2

CHUNK_SIZE = 65536

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

# if sock is None, juste return the estimate size
def send_data(v_vars, v_files, boundary, sendfunc=None):
    l = 0
    for (k, v) in v_vars:
        buffer=''
        buffer += '--%s\r\n' % boundary
        buffer += 'Content-Disposition: form-data; name="%s"\r\n' % k
        buffer += '\r\n'
        buffer += v + '\r\n'
        if sendfunc:
            sendfunc(buffer)
        l += len(buffer)
    for (k, v) in v_files:
        fd = v
        if hasattr(fd, 'len'):
            file_size = fd.len
        else:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
        if isinstance(k, tuple):
            k, name = k
        else:
            name = fd.name.split('/')[-1]
        if isinstance(name, unicode):
            name = name.encode('UTF-8')
        buffer=''
        buffer += '--%s\r\n' % boundary
        buffer += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' \
                  % (k, name)
        buffer += 'Content-Type: %s\r\n' % get_content_type(name)
        buffer += 'Content-Length: %s\r\n' % file_size
        buffer += '\r\n'

        l += len(buffer)
        if sendfunc:
            sendfunc(buffer)
            if hasattr(fd, 'seek'):
                fd.seek(0)
            while True:
                chunk = fd.read(CHUNK_SIZE)
                if not chunk: break
                sendfunc(chunk)

        l += file_size
    buffer='\r\n'
    buffer += '--%s--\r\n' % boundary
    buffer += '\r\n'
    if sendfunc:
        sendfunc(buffer)
    l += len(buffer)
    return l

def do_request_(self, request):
    host = request.get_host()
    if not host:
        raise URLError('no host given')

    data = request.get_data()
    v_files=[]
    v_vars=[]
    if request.has_data() and not isinstance(data, str):  #POST
        if hasattr(data, 'items'):
            data = data.items()
        else:
            try:
                if len(data) and not isinstance(data[0], tuple):
                    raise TypeError
            except TypeError:
                _ty, _va, tb = sys.exc_info()
                try:
                    raise TypeError, "not a valid non-string sequence or mapping object: %r" % type(data), tb
                finally:
                    del tb
        for (k, v) in data:
            if hasattr(v, 'read'):
                v_files.append((k, v))
            else:
                v_vars.append( (k, v) )
        boundary = mimetools.choose_boundary()
        request.boundary = boundary
        request.v_files  = v_files
        request.v_vars   = v_vars
    # no file ? convert to string
    if len(v_vars) > 0 and len(v_files) == 0:
        request.data = data = urllib.urlencode(v_vars)
        v_files[:]=[]
        v_vars[:]=[]

    if request.has_data():
        if not 'Content-type' in request.headers:
            if len(v_files) > 0:
                l = send_data(v_vars, v_files, boundary)
                request.add_unredirected_header('Content-Type',
                            'multipart/form-data; boundary=%s' % boundary)
                request.add_unredirected_header('Content-length', str(l))
            else:
                request.add_unredirected_header('Content-type',
                            'application/x-www-form-urlencoded')
                if not 'Content-length' in request.headers:
                    request.add_unredirected_header('Content-length', '%d' % len(data))

    _scheme, sel = splittype(request.get_selector())
    sel_host, _sel_path = splithost(sel)
    if not request.has_header('Host'):
        request.add_unredirected_header('Host', sel_host or host)
    for name, value in self.parent.addheaders:
        name = name.capitalize()
        if not request.has_header(name):
            request.add_unredirected_header(name, value)

    return request

urllib2.AbstractHTTPHandler.do_request_ = do_request_
old_open = urllib2.AbstractHTTPHandler.do_open

def do_open(self, http_class, req):
    req = do_request_(self, req)
    host = req.get_host()
    if not host:
        raise URLError('no host given')

    h = http_class(host) # will parse host:port
    h.set_debuglevel(self._debuglevel)

    headers = dict(req.headers)
    headers.update(req.unredirected_hdrs)
    headers["Connection"] = "close"
    headers = dict(
        (name.title(), val) for name, val in headers.items())

    if req.has_data() and not isinstance(req.data, str):
        reqdata = req
    else:
        reqdata = req.data

    try:
        h.request(req.get_method(), req.get_selector(), reqdata, headers)
        r = h.getresponse()
    except socket.error, err: # XXX what error?
        raise URLError(err)

    r.recv = r.read
    fp = socket._fileobject(r, close=True)

    resp = addinfourl(fp, r.msg, req.get_full_url())
    resp.code = r.status
    resp.msg = r.reason
    return resp

urllib2.AbstractHTTPHandler.do_open = do_open

def _send_request(self, method, url, body, headers):
    # honour explicitly requested Host: and Accept-Encoding headers
    header_names = dict.fromkeys([k.lower() for k in headers])
    skips = {}
    if 'host' in header_names:
        skips['skip_host'] = 1
    if 'accept-encoding' in header_names:
        skips['skip_accept_encoding'] = 1

    self.putrequest(method, url, **skips)

    if isinstance(body, str):
        if body and ('content-length' not in header_names):
            self.putheader('Content-Length', str(len(body)))
    for hdr, value in headers.iteritems():
        self.putheader(hdr, value)
    self.endheaders()

    if body:
        self.send(body)

httplib.HTTPConnection._send_request = _send_request

def send(self, str):
    """Send `str' to the server."""
    if self.sock is None:
        if self.auto_open:
            self.connect()
        else:
            raise NotConnected()

    # send the data to the server. if we get a broken pipe, then close
    # the socket. we want to reconnect when somebody tries to send again.
    #
    # NOTE: we DO propagate the error, though, because we cannot simply
    #       ignore the error... the caller will know if they can retry.
    if self.debuglevel > 0:
        print "send:", repr(str)
    try:
        if hasattr(str, 'boundary'):
            boundary = str.boundary
            v_files  = str.v_files
            v_vars   = str.v_vars
            send_data(v_vars, v_files, boundary, self.sock.sendall)
        else:
            self.sock.sendall(str)
    except socket.error, v:
        if v[0] == 32:      # Broken pipe
            self.close()
        raise


httplib.HTTPConnection.send = send

# mainly a copy of HTTPHandler from urllib2
#class newHTTPHandler(urllib2.BaseHandler):
#    def http_open(self, req):
#        return self.do_open(httplib.HTTP, req)
#
#    def do_open(self, http_class, req):
#        data = req.get_data()
#        v_files=[]
#        v_vars=[]
#        # mapping object (dict)
#        if isinstance(data, unicode):
#            data = data.encode('UTF-8')
#        if req.has_data() and not isinstance(data, str):
#            if hasattr(data, 'items'):
#                data = data.items()
#            else:
#                try:
#                    if len(data) and not isinstance(data[0], tuple):
#                        raise TypeError
#                except TypeError:
#                    ty, va, tb = sys.exc_info()
#                    raise TypeError, "not a valid non-string sequence or mapping object", tb
#
#            for (k, v) in data:
#                if hasattr(v, 'read'):
#                    v_files.append((k, v))
#                else:
#                    v_vars.append( (k, v) )
#        # no file ? convert to string
#        if len(v_vars) > 0 and len(v_files) == 0:
#            data = urllib.urlencode(v_vars)
#            v_files=[]
#            v_vars=[]
#        host = req.get_host()
#        if not host:
#            raise urllib2.URLError('no host given')
#
#        h = http_class(host) # will parse host:port
#        if req.has_data():
#            print 'doing post'
#            h.putrequest('POST', req.get_selector())
#            if not 'Content-type' in req.headers:
#                if len(v_files) > 0:
#                    boundary = mimetools.choose_boundary()
#                    l = send_data(v_vars, v_files, boundary)
#                    h.putheader('Content-Type',
#                                'multipart/form-data; boundary=%s' % boundary)
#                    h.putheader('Content-length', str(l))
#                else:
#                    h.putheader('Content-type',
#                                'application/x-www-form-urlencoded')
#                    if not 'Content-length' in req.headers:
#                        h.putheader('Content-length', '%d' % len(data))
#        else:
#               print 'doing get ', req.get_selector()
#               h.putrequest('GET', req.get_selector())
#
#        scheme, sel = urllib.splittype(req.get_selector())
#        sel_host, sel_path = urllib.splithost(sel)
#        h.putheader('Host', sel_host or host)
#        for name, value in self.parent.addheaders:
#            name = name.capitalize()
#            if name not in req.headers:
#                h.putheader(name, value)
#        for k, v in req.headers.items():
#            h.putheader(k, v)
#        # httplib will attempt to connect() here.  be prepared
#        # to convert a socket error to a URLError.
#        try:
#            h.endheaders()
#        except socket.error, err:
#            raise urllib2.URLError(err)
#
#        if req.has_data():
#            if len(v_files) >0:
#                l = send_data(v_vars, v_files, boundary, h)
#            elif len(v_vars) > 0:
#                # if data is passed as dict ...
#                data = urllib.urlencode(v_vars)
#                h.send(data)
#            else:
#                # "normal" urllib2.urlopen()
#                h.send(data)
#
#        code, msg, hdrs = h.getreply()
#        fp = h.getfile()
#        if code == 200:
#            resp = urllib.addinfourl(fp, hdrs, req.get_full_url())
#            resp.code = code
#            resp.msg = msg
#            return resp
#        else:
#            return self.parent.error('http', req, fp, code, msg, hdrs)
#
#urllib2._old_HTTPHandler = urllib2.HTTPHandler
#urllib2.HTTPHandler = newHTTPHandler
#
#class newHTTPSHandler(newHTTPHandler):
#    def https_open(self, req):
#        return self.do_open(httplib.HTTPS, req)
#
#urllib2.HTTPSHandler = newHTTPSHandler
#
#if __name__ == '__main__':
#    import getopt
#    import urllib2
#    import urllib2_file
#    import string
#    import sys
#
#    def usage(progname):
#        print """
#SYNTAX: %s -u url -f file [-v]
#""" % progname
#
#    try:
#        opts, args = getopt.getopt(sys.argv[1:], 'hvu:f:')
#    except getopt.GetoptError, errmsg:
#        print "ERROR:", errmsg
#        sys.exit(1)
#
#    v_url = ''
#    v_verbose = 0
#    v_file = ''
#
#    for name, value in opts:
#        if name in ('-h',):
#            usage(sys.argv[0])
#            sys.exit(0)
#        elif name in ('-v',):
#            v_verbose += 1
#        elif name in ('-u',):
#            v_url = value
#        elif name in ('-f',):
#            v_file = value
#        else:
#            print "invalid argument:", name
#            sys.exit(2)
#
#    error = 0
#    if v_url == '':
#        print "need -u"
#        error += 1
#    if v_file == '':
#        print "need -f"
#        error += 1
#
#    if error > 0:
#        sys.exit(3)
#
#    fd = open(v_file, 'r')
#    data = {
#        'filename' : fd,
#        }
#    # u = urllib2.urlopen(v_url, data)
#    req = urllib2.Request(v_url, data, {})
#    try:
#        u = urllib2.urlopen(req)
#    except urllib2.HTTPError, errobj:
#        print "HTTPError:", errobj.code
#
#    else:
#        buf = u.read()
#        print "OK"
