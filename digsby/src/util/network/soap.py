import ZSI
import ZSI.schema as schema
import ZSI.fault as fault
import ZSI.auth as auth
import ZSI.client as ZSIClient
import ZSI.wstools.Namespaces as WSNS

import logging
import urlparse

import common.asynchttp as asynchttp
import util.callbacks as callbacks

import traceback
log = logging.getLogger("util.soap")

SOAP_TYPES = ('text/xml',
              'application/soap+xml',
              )

MinTime = '0001-01-01T00:00:00.0000000-08:00'

class Binding(ZSIClient.Binding):

    def __init__(self, url, transport = None, **k):
        super(Binding, self).__init__(url, transport = transport, **k)

    def __getattr__(self, attr):
        if attr == "_getAttributeNames":
            return False
        else:
            return ZSIClient.Binding.__getattr__(self, attr)


    def get_default_headers(self):
        return {'Content-Type' : 'application/soap+xml; charset="utf-8"',
                }

    @callbacks.callsback
    def RPC(self, url, opname, obj, callback = None, **kw):
        '''Send a request, return the reply.  See Send() and Recieve()
        docstrings for details.
        '''
        self.Send(url, opname, obj,
                  # Might be a fault, or it could be an HTTP error
                  error = lambda response: self.Receive(response, callback = callback, **kw),
                  success = lambda response: self.Receive(response, callback = callback, **kw),
                  **kw)

    @callbacks.callsback
    def Send(self, url, opname, obj, nsdict={}, soapaction=None, wsaction=None,
             endPointReference=None, soapheaders=(), callback = None, **kw):
        '''Send a message.  If url is None, use the value from the
        constructor (else error). obj is the object (data) to send.
        Data may be described with a requesttypecode keyword, the default
        is the class's typecode (if there is one), else Any.

        Try to serialize as a Struct, if this is not possible serialize an Array.  If
        data is a sequence of built-in python data types, it will be serialized as an
        Array, unless requesttypecode is specified.

        arguments:
            url --
            opname -- struct wrapper
            obj -- python instance

        key word arguments:
            nsdict --
            soapaction --
            wsaction -- WS-Address Action, goes in SOAP Header.
            endPointReference --  set by calling party, must be an
                EndPointReference type instance.
            soapheaders -- list of pyobj, typically w/typecode attribute.
                serialized in the SOAP:Header.
            requesttypecode --

        '''
        url = url or self.url
        endPointReference = endPointReference or self.endPointReference

        # Serialize the object.
        d = {}
        d.update(self.nsdict)
        d.update(nsdict)

        SWC = kw.get('writerclass', self.writerclass or ZSI.SoapWriter)
        sw = SWC(nsdict=d, header=True, outputclass=self.writerclass,
                 encodingStyle=kw.get('encodingStyle'),)

        requesttypecode = kw.get('requesttypecode')
        if kw.has_key('_args'): #NamedParamBinding
            tc = requesttypecode or ZSI.TC.Any(pname=opname, aslist=False)
            sw.serialize(kw['_args'], tc)
        elif not requesttypecode:
            tc = getattr(obj, 'typecode', None) or ZSI.TC.Any(pname=opname, aslist=False)
            try:
                if type(obj) in ZSI._seqtypes:
                    obj = dict(map(lambda i: (i.typecode.pname,i), obj))
            except AttributeError:
                # can't do anything but serialize this in a SOAP:Array
                tc = ZSI.TC.Any(pname=opname, aslist=True)
            else:
                tc = ZSI.TC.Any(pname=opname, aslist=False)

            sw.serialize(obj, tc)
        else:
            sw.serialize(obj, requesttypecode)

        for i in soapheaders:
            sw.serialize_header(i)

        #
        # Determine the SOAP auth element.  SOAP:Header element
        if self.auth_style & auth.AUTH.zsibasic:
            sw.serialize_header(ZSIClient._AuthHeader(self.auth_user, self.auth_pass),
                ZSIClient._AuthHeader.typecode)

        #
        # Serialize WS-Address
        if self.wsAddressURI is not None:
            if self.soapaction and wsaction.strip('\'"') != self.soapaction:
                raise WSActionException, 'soapAction(%s) and WS-Action(%s) must match'\
                    %(self.soapaction,wsaction)

            self.address = Address(url, self.wsAddressURI)
            self.address.setRequest(endPointReference, wsaction)
            self.address.serialize(sw)

        #
        # WS-Security Signature Handler
        if self.sig_handler is not None:
            self.sig_handler.sign(sw)

        scheme,netloc,path,nil,nil,nil = urlparse.urlparse(url)

        soapdata = str(sw)
        headers = self.get_default_headers()

        sa = soapaction or self.soapaction
        if sa:
            headers['SOAPAction'] = sa
#        if self.auth_style & auth.AUTH.httpbasic:
#            headers['Authorization'] = 'Basic ' + _b64_encode(self.auth_user + ':' + self.auth_pass).replace("\012", "")
#        elif self.auth_style == auth.AUTH.httpdigest and 'Authorization' not in headers and 'Expect' not in headers:
#            pass

        log.debug_s("soap data: %r", soapdata)
        req = asynchttp.HTTPRequest.make_request(self.url,
                                                 data = soapdata,
                                                 headers = headers,
                                                 method = 'POST',
                                                 adjust_headers = False)

        self.ps = self.data = None

        transport = self.transport or asynchttp

        transport.httpopen(req,
                           success = lambda req, resp: self.handle_response(req, resp, callback = callback),
                           error = lambda req, resp: self.handle_error(req, resp, callback=callback))

    @callbacks.callsback
    def handle_response(self, request, response, callback = None):
        callback.success(response)

    @callbacks.callsback
    def handle_error(self, request, response, callback = None):
        callback.error(response)


    def ReceiveRaw(self, response):
        '''Read a server reply, unconverted to any format and return it.
        '''

        # TODO: handle possible HTTP errors and stuff here.
        response.body.seek(0)
        response.content = response.body.read()
        response.body.seek(0)
        log.info("SOAP response: %r", response.content)
        return response.content

    def IsSOAP(self, response):
        mimetype = response.headers.get_content_type()
        return mimetype in SOAP_TYPES

    def ReceiveSOAP(self, response, readerclass=None, **kw):
        '''Get back a SOAP message.
        '''

        self.ReceiveRaw(response)

        if self.ps: return self.ps
        if not self.IsSOAP(response):
            raise TypeError(
                'Response is "%s", not in %r' % (response.headers.get_content_type(), SOAP_TYPES))
        if len(response.content) == 0:
            raise TypeError('Received empty response')

        self.ps = ZSI.ParsedSoap(response.content,
                             readerclass=readerclass or self.readerclass,
                             encodingStyle=kw.get('encodingStyle'))

        if self.sig_handler is not None:
            self.sig_handler.verify(self.ps)

        return self.ps

    def IsAFault(self, response):
        '''Get a SOAP message, see if it has a fault.
        '''
        self.ReceiveSOAP(response)
        return self.ps.IsAFault()

    def ReceiveFault(self, response, **kw):
        '''Parse incoming message as a fault. Raise TypeError if no
        fault found.
        '''
        self.ReceiveSOAP(response, **kw)
        if not self.ps.IsAFault():
            raise TypeError("Expected SOAP Fault not found")

        return fault.FaultFromFaultMessage(self.ps)

    @callbacks.callsback
    def Receive(self, response, callback = None, **kw):
        '''Parse message, create Python object.

        KeyWord data:
            faults   -- list of WSDL operation.fault typecodes
            wsaction -- If using WS-Address, must specify Action value we expect to
                receive.
        '''
#        fault = None
#        try:
#            fault = self.ReceiveFault(response, **kw)
#        except TypeError:
#            pass
#        else:
#            return callback.error(FaultException(msg))
        self.ReceiveSOAP(response, **kw)
        pname = self.ps.body_root.namespaceURI, self.ps.body_root.localName
        el_type = schema.GTD(*pname)
        if el_type is not None:
            tc = el_type(pname)
        else:
            tc = schema.GED(*pname)

        reply = self.ps.Parse(tc)

        if self.ps.body_root.localName == 'Fault':
            return callback.error(reply)

        reply_tc = getattr(reply, 'typecode', None)
        if reply_tc is None:
            log.warning("Unable to parse reply with tc=%r (got %r). Returning empty tc instance.", tc, reply)
            reply = tc

        headers_to_parse = []
        for hdr in self.ps.header_elements:
            hdr_pname = (hdr.namespaceURI, hdr.localName)
            hdr_type = schema.GTD(*hdr_pname)
            if hdr_type is not None:
                hdr_tc = hdr_type(hdr_pname)
            else:
                hdr_tc = schema.GED(*hdr_pname)

            headers_to_parse.append(hdr_tc)

        headers = self.ps.ParseHeaderElements(headers_to_parse)
        reply.soapheaders = headers

        if self.address is not None:
            self.address.checkResponse(self.ps, kw.get('wsaction'))
        callback.success(reply)

    def __repr__(self):
        return "<%s instance %s>" % (self.__class__.__name__, ZSI._get_idstr(self))


class BindingSOAP(object):
    BindingClass = Binding
    nsdict = dict(#ps   = MSNS.PPCRL.BASE,
                  #psf  = MSNS.PPCRL.FAULT,
                  wsse = WSNS.OASIS.WSSE,
                  wsp  = WSNS.WSP.POLICY,  # should this be WSP200212 ?
                  wsu  = WSNS.OASIS.UTILITY,
                  wsa  = WSNS.WSA.ADDRESS, # should this be WSA200403 ?
                  wssc = WSNS.BEA.SECCONV,
                  wst  = WSNS.WSTRUST.BASE,# should this be WSTRUST200404 ?
                  )
    def __init__(self, url, **kw):
        kw.setdefault("readerclass", None)
        kw.setdefault("writerclass", None)
        # no resource properties
        bindingClass = kw.get('BindingClass', self.BindingClass)
        nsdict = kw.setdefault('nsdict', {})
        nsdict.update(self.nsdict)
        self.transport = kw.get('transport', None)
        self.binding = bindingClass(url=url, **kw)
        if self.transport is None:
            raise Exception
        if self.binding.transport is None:
            raise Exception
        # no ws-addressing

class soapcall(object):
    def __init__(self,
                 soap_module = None,
                 service_name = None,
                 name = None,
                 getHeaders = None,
                 getLocator = None,
                 getPort = None,
                 getMessage = None,
                 handleHeaders = None,
                 handleResponse = None):

        self.soap_module = soap_module
        self.service_name = service_name
        self.name = name
        self.message_setup = None

        self._getLocator = getLocator
        self._getPort = getPort
        self._getMessage = getMessage
        self._getHeaders = getHeaders
        self._handleHeaders = handleHeaders
        self._handleResponse = handleResponse

    def __get__(self, obj, objtype):
        @callbacks.callsback
        def call(**k):

            soap_module = self.soap_module or obj.Soap
            self.service_name = self.service_name or getattr(obj, 'AppName', None)
            getLocator = self._getLocator or getattr(obj, 'Locator', getattr(soap_module, '%sLocator' % self.service_name))
            locator = getLocator()
            getPort = self._getPort or getattr(obj, 'getPort', None) or getattr(locator, 'get%sPort' % self.name)

            transport = getattr(obj, 'Transport', None)

            port = getPort(url = k.get('PortUrl', None), soapName = self.name, locator = locator, transport = transport, **k)
            phn = getattr(obj, 'PreferredHostName', None)
            if phn is not None:
                parsed_url = urlparse.urlparse(port.binding.url)._asdict()
                parsed_url['netloc'] = phn
                new_url = urlparse.urlunparse(urlparse.ParseResult(**parsed_url))
                log.debug("using PreferredHostName url %r instead of default %r", new_url, port.binding.url)
                port.binding.url = new_url

            callback = k.pop('callback')
            getHeaders = self._getHeaders or getattr(obj, '%sHeaders' % self.name, getattr(obj, 'serviceHeaders', lambda *a, **k: ()))
            headers = getHeaders(**k) or ()

            getMessage = self._getMessage or getattr(soap_module, '%sMessage' % self.name)
            message = getMessage()
            e = None
            try:
                do_request = self.message_setup(self=obj, msg=message, **k)
            except Exception, e:
                do_request = False

            if do_request is False:
                _v = 'BadRequest', message, k, e
                if e:
                    traceback.print_exc()
                return callback.error(Exception(*_v))

            def success(resp):
                handleHeaders = getattr(obj, self._handleHeaders or 'handle%sHeaders' % self.name, getattr(obj, 'handleHeaders', None))
                handleResponse = getattr(obj, self._handleResponse or '%sSuccess' % self.name, None)

                if handleHeaders is not None:
                    handleHeaders(client = k.get('client'), headers = resp.soapheaders)

                if handleResponse is not None:
                    resp = handleResponse(response = resp, **k)

                callback.success(resp)

            try:
                getattr(port, self.name)(request = message, soapheaders = headers,
                                         success = success, error = callback.error,
                                         **k)
            except Exception, e:
                traceback.print_exc()
                callback.error(e)

            return do_request

        def CheckAndCall(**k):
            obj.CheckAuth(k.get('client'),
                          success = lambda:call(**k),
                          error = getattr(k.get('callback'), 'error', lambda *a: None))

        return CheckAndCall

    def __call__(self, message_setup):
        if self.name is None:
            self.name = message_setup.func_name
        self.message_setup = message_setup
        return self

