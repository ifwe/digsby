'''
asynchttp

This module is meant to be used in place of urllib2.urlopen. It supports most widely used features
of urllib2, and has a new features of its own (besides asynchronicity). It operates with the asyncore
thread machinery, which is a bit coupled with the overall app code. For that reason, this module is a
part of common, and not util.

### Making requests

Success callback receives the request object that was provided or created and the response.
>>> success_handler = lambda request, response: None

Error callback should* receive the attempted request object as well as the exception that occurred.
* (see 'Issues', below)
>>> error_handler = lambda req, e = None: None

The simplest way of performing a request is with asynchttp.httpopen, passing the URL and callback functions.
asynchttp.httpopen is an alias to the `open` method of a global HttpMaster instance.
>>> asynchttp.httpopen('http://www.example.com', success = success_handler, error = error_handler)

For more complicated requests, you can provide more options. All recieved arguments (except callback)
are passed directly to the request_cls factory callable owned by the HttpMaster instance being used.
The default request_cls is asynchttp.HTTPRequest (from httptypes.py) which supports the following arguments:

 - url: string
     the full URL of the resource being requested
 - data: string (None)
     content that will be submitted as the request body. its len() is used to determine Content-Length.
 - headers: mapping type or iterable of 2-tuples ({})
     If this value is ordered, order will be retained when sending.
       Headers that are generated automatically (e.g. Content-Length) will NOT be generated if they are
       provided in this argument.
 - origin_req_host: string (None)
     original host the request originated for. Used when a request is proxied, usually not
       needed unless overriding functionality
 - unverifiable: bool (False)
      value is True if the user had no option to approve the request. This is not used directly by
        asynchttp, but is provided to maintain compatibility with urllib2.urlopen
 - method: string ('GET' or 'POST')
     the HTTP method. usually one of GET, POST, PUT, DELETE. If not provided, GET is used when
       'data' is None and POST otherwise.
 - follow_redirects: bool (True)
     controls behavior if server responds with a redirect. Default: True.
 - on_redirect: callable (None)
     if provided, this function is called with the request object if a redirect status code is
       received. The function should return a Request object to be used (it can be the same one
       it was called with) or veto the redirect entirely by returning None.
 - accumulate_body: bool (True)
     Controls whether the response object will accumulate the body of the response or not. This is
       generally the most useful way to use this module. However, it's also possible to bind to the
       Request's on_chunk method and accumulate the received data yourself; for example, a large file
       download. A working use case of this can be found in the twitter plugin.
 - adjust_headers: bool (True)
     When True, causes header keys to be Title-Cased, which is usually the norm in the HTTP protocol.
       Occasionally, one finds a finicky HTTP server that doesn't like this and so you might want to
       set it to false.

You can also create a request object yourself and pass it to HttpMaster.open. If the first argument
is not a string, it's treated as a request object. This can be helpful if you need to use a subclass
of HTTPRequest.
>>> req = asynchttp.HTTPRequest('http://www.example.com', *foo, **bar)
>>> asynchttp.httpopen(req, success = success_handler, error = error_handler)
###

### Handling connections
Connection handling is performed by HttpMaster instances. As mentioned there is a global instance
provided for convenience, but part of its functionality is to throttle connections to a given server.
An HttpMaster will deliberately NOT open multiple connections to the same server. For this reason, it's
expected that a given protocol type (e.g. FacebookAPI) will have its own HttpMaster instance. Having your
own HttpMaster instance (or subclass instance) also allows you to customize request_cls and persister_cls
(default HttpPersister) factory functions.

When an HttpMaster processes a request, it first finds or creates a persister_cls (which manages an
AsyncHttpConnection or subclass instance) for the destination host. Once a connection is established,
the request is sent and a response is read.

HttpMaster also suppors BASIC HTTP auth. You can add credentials with the add_password method. It accepts
arguments (realm, uri, username, password). For more info, see HTTPPasswordMgr in the python documentation.

Also worth noting is a CookieJarHTTPMaster class that supports cookies for all of its connections.

All connections can be closed forcefully (as quickly as asyncore event processing will allow) with the close_all
method. No guarantees can be made about any event handlers being called after this method; in fact the intention
is that no more events will be emitted.
###

### Serving
This is a newer feature of asynchttp that is not widely used nor is it extensively developed. It's intended
to be used for one-off incoming requests to a certain path (or regex pattern) that are handled by a callback.

For a working example, see common.oauth_util.
###

### Issues
 - Error callbacks are not always called with two arguments (request, error). Sometimes they're called with
     just one (error).
###
'''

from httptypes import HTTPRequest
from requester import HttpMaster, httpopen
