#!/usr/bin/python
#__LICENSE_GOES_HERE__

import Queue
import array
from collections import deque
import socket
import sys
import weakref
import threading
from new import instancemethod
import glob
import logging
import logging.handlers
import time

class StatLogger:
  def __init__(self):
    self.log = open("pyskypekit.stats", "w")
  def CreateObj(self, modid, oid):
    self.log.write('CreateObj(%f,%d,%d)\n' % (time.time(), modid, oid))
  def ReachObj(self, modid, oid, hit, reached_from):
    self.log.write('ReachObj(%f,%d,%d,%s,"%s")\n' % (time.time(), modid, oid, hit, reached_from))
  def ReachProp(self, modid, oid, propid, hit, reached_from):
    self.log.write('ReachProp(%f,%d,%d,%d,%s,"%s")\n' % (time.time(), modid, oid, propid, hit, reached_from))
  def XcallBegin(self, mid, method, rid, oid):
    self.log.write('XcallBegin(%f,%d,%d,%d,%d)\n' % (time.time(), mid, method, rid, oid))
  def XcallEnd(self, rid):
    self.log.write('XcallEnd(%f,%d)\n' % (time.time(), rid))
  def Event(self, mid, method, oid, dispatched):
    self.log.write('DispatchEvent(%f,%d,%d,%d)\n' % (time.time(), mid, method, oid))
stat_logger = None #StatLogger()

LOG_FILENAME = 'pyskypekit.out'

''' Protocol error.
'''
class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class ConnectionClosed(Error):
    def __init__(self):
        Error.__init__(self, "Connection closed")

class ResponseError(Error):
    def __init__(self):
        Error.__init__(self, "response error (either invalid in parameters for the call or call isn't allowed or call failed")


class InvalidObjectIdError(Error):
    def __init__(self):
        Error.__init__(self, "object id is 0")

module_id2classes = { }

class ScopedLock(object):
  def __init__(self, mutex):
    self.mutex = mutex
    self.mutex.acquire();
  def __del__(self):
    self.mutex.release();

class Cached(object):
  '''Base class for all cached objects.

  Every object is identified by an Id specified as first parameter of the constructor.
  Trying to create two objects with same Id yields the same object. Uses weak references
  to allow the objects to be deleted normally.

  @warning: C{__init__()} is always called, don't use it to prevent initializing an already
  initialized object. Use C{_Init()} instead, it is called only once.
  '''
  _lock_  = threading.Lock()
  _cache_ = weakref.WeakValueDictionary()
  def __new__(cls, Id, *args, **kwargs):
    if Id == 0: return False # invalid id, still return something not to shift parameters
    sl = ScopedLock(cls._lock_)
    h = cls, Id
    hit = True
    o = None
    try:
      o = cls._cache_[h]
    except KeyError:
      #stat_logger.CreateObj(cls.module_id, Id)
      o = object.__new__(cls)
      h = cls, Id
      cls._cache_[h] = o
      if hasattr(o, '_Init'):
        o._Init(Id, *args, **kwargs)
    return o
  @staticmethod
  def exists(cls, Id, src):
    if Id == 0: return None # invalid id
    sl = ScopedLock(cls._lock_)
    h = cls, Id
    try:
      return cls._cache_[h]
    except KeyError:
      return None
  def __copy__(self):
      return self

class Object(Cached):
  rwlock = threading.Lock()
  def _Init(self, object_id, transport):
    self.transport = transport
    self.object_id = object_id
    self.properties= {}
    if transport.logger: transport.logger.info('INSTANTIATING mod=%d oid=%d' % (self.module_id,object_id))
  ''' Retrieve given property id.
  '''
  def _Property(self, header, prop_id, cached):
    hit = cached #True
    val = 0
    try:
      self.rwlock.acquire()
      if hit: val = self.properties[prop_id]
      self.rwlock.release()
    except KeyError:
      self.rwlock.release()
      hit=False
    if not hit:
      val = self.transport.Get(GetRequest(header, self.object_id))
    #stat_logger.ReachProp(self.module_id, self.object_id, prop_id, hit, 'Get')
    return val
  def _propkey(self, propname, t):
    for p,l in self.propid2label.items():
      # don't set the property value, as it shall be notified by a property change event
      if l == propname:
        if p in self.properties: del self.properties[p] # clean it...
        return p*4+t
    return None
  def multiget(self, header):
    self.transport.Get(GetRequest(header, self.object_id))
''' Connection class that implements Skype IPC.
'''
class SkypeKit:
  decoders={}

  class EventDispatcher(threading.Thread):
    def __init__(self, connection):
      self.connection = connection
      threading.Thread.__init__(self)
      self.setName('event thread')
    def run(self):
      try:
        self.connection.EventThread()
      except:
        self.connection.Stop()
        raise

  class ResponseListener(threading.Thread):
    def __init__(self, connection):
      self.connection = connection
      threading.Thread.__init__(self)
      self.setName('responser listener thread')
    def run(self):
      try:
        self.connection.Start()
      except:
        self.connection.Stop()
        raise

  def __init__(self, has_event_thread = True, host = '127.0.0.1', port = 8963, logging_level = logging.NOTSET, logging_file = LOG_FILENAME, noncacheable = 'z', logtransport=False):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)
    sock.settimeout(30.5)
    self.pending_requests = {}
    self.pending_gets = deque()
    self.pending_lock = threading.Lock()
    self.encoding_lock = threading.Lock()
    self.decoded = threading.Event()
    self.event_queue = Queue.Queue()
    self.inlog  = False
    self.outlog = False
    if logtransport:
      try:
        self.inlog  = open(logtransport+'_log_in.1', 'wb')
      except IOError:
        self.inlog  = False
      try:
        self.outlog = open(logtransport+'_log_out.1', 'wb')
      except IOError:
        self.outlog = False
    self.logger = False
    if logging_level != logging.NOTSET:
      self.logger = logging.getLogger('SkypeKitLogger')
      self.logger.setLevel(logging_level)
      handler = logging.handlers.RotatingFileHandler(logging_file, maxBytes=2**29, backupCount=5)
      self.logger.addHandler(handler)
    self.stopped = False
    self.socket = sock
    retry = 3
    while retry > 0:
      try:
        sock.connect((host, port))
        retry = -1
      except:
        retry = retry - 1
        if retry == 0:
          raise
        time.sleep(5)
    self.read_buffer = ''
    sock.sendall('z')
    if has_event_thread:
      self.event_dispatcher = SkypeKit.EventDispatcher(self)
      self.event_dispatcher.start()
    self.listener = SkypeKit.ResponseListener(self)
    self.listener.start()

  def setRoot(self, root): self.root = root

  def __del__(self):
    if self.socket != None:
      self.socket.close()
    if self.inlog: self.inlog.close()
    if self.outlog: self.outlog.close()

  def ReadByte(self, num_bytes_to_read = 1, timeout = True):
    def isprint(c):
      if ord(c) >= 32 and ord(c) <= 127: return c
      return ' '
    result = self.read_buffer
    while not self.stopped and len(result) < num_bytes_to_read:
      try:
        read = self.socket.recv(4096)
        if not read:
          self.Stop()
          raise ConnectionClosed
        result += read
        if self.inlog:
          try:
            self.inlog.write(read)
          except IOError:
            self.inlog.close()
            self.inlog = False
      except socket.timeout:
        pass # retry always: if connection is closed we will see it at next read
      except:
        self.Stop()
        raise
    if self.stopped: return None
    self.read_buffer = result[num_bytes_to_read:]
    result = result[:num_bytes_to_read]
    if self.logger:
      if len(result) == 1:
        self.logger.debug('reading %s %3d %2x' % (isprint(result), ord(result), ord(result)))
      else:
        self.logger.debug('reading %3d bytes ' % (len(result)))
    return result

  def EventThread(self):
    while True:
      e = self.event_queue.get()
      if self.stopped: return
      e.dispatch()

  def DispatchEvent(self):
    while not self.event_queue.empty():
      e = self.event_queue.get()
      if self.stopped: return
      e.dispatch()

  def Xcall(self, request):
    ev  = threading.Event()
    self.encoding_lock.acquire()
    self.pending_lock.acquire()
    self.pending_requests[request.rid] = ev
    self.pending_lock.release()
    if self.logger: self.logger.info('CALLING mod=%d mid=%d rid=%d' % (request.module_id, request.method_id, request.rid))
    #stat_logger.XcallBegin(request.module_id, request.method_id, request.rid, request.oid)
    rq = request.Send()
    self.socket.sendall(rq)
    if self.outlog:
      try:
        self.outlog.write(rq)
      except IOError:
        self.outlog.close()
        self.outlog = False
    self.encoding_lock.release()
    ev.wait() # no need to clear: one shot
    if self.stopped: raise ConnectionClosed()
    response = self.decode_parms()
    #stat_logger.XcallEnd(request.rid)
    return response

  def multiget(self, header, objects):
    if len(objects) > 0: self.Get(MultiGetRequest(header, objects))

  def Get(self, request):
    ev  = threading.Event()
    self.encoding_lock.acquire()
    self.pending_lock.acquire()
    self.pending_gets.append(ev)
    self.pending_lock.release()
    rq = request.Send()
    self.socket.sendall(rq)
    if self.outlog:
      try:
        self.outlog.write(rq)
      except IOError:
        self.outlog.close()
        self.outlog = False
    self.encoding_lock.release()  # wait until response is here
    ev.wait()
    if self.stopped: raise ConnectionClosed()
    # process the response with patching the instances...
    response  = None
    mresponse = {}
    continue_sign = ','
    count = 0
    while continue_sign == ',':
      modid = self.decode_varuint() # modid
      while continue_sign == ',':
        oid = self.decode_varuint() # oid
        o = module_id2classes[modid](oid,self)
        if not o in mresponse: mresponse[o] = {}
        kind = self.ReadByte()
        while kind != ']':
          propid = self.decode_varuint() # propid
          if kind != 'N':
            response = self.decoders[kind](self)
            mresponse[o][propid] = response
            o.rwlock.acquire()
            o.properties[propid] = response
            o.rwlock.release()
            count = count + 1
          kind = self.ReadByte() # ] finish the list
        if kind != ']': raise ResponseError()
        continue_sign = self.ReadByte()
      if continue_sign != ']': raise ResponseError()
      continue_sign = self.ReadByte()
    if continue_sign != ']': raise ResponseError()
    if self.ReadByte() != 'z': raise ResponseError()
    self.decoded.set()
    if count > 1: response = mresponse
    return response

  def GetResponse(self):
    self.pending_lock.acquire()
    self.pending_gets.popleft().set()
    self.pending_lock.release()
  decoders['g'] = GetResponse

  def decode_varuint(self):
    shift  = 0
    result = 0
    while 1:
      value  = ord(self.ReadByte()) & 0xff
      result = result | ((value & 0x7f) << shift)
      shift  = shift + 7
      if not (value & 0x80): break
    return result
  decoders['u'] = decode_varuint
  decoders['O'] = decode_varuint
  decoders['e'] = decode_varuint

  def decode_varint(self):
    value = self.decode_varuint()
    if not value & 0x1:
      return value >> 1
    return (value >> 1) ^ (~0)
  decoders['i'] = decode_varint

  def decode_true(self):
    return True
  decoders['T'] = decode_true

  def decode_false(self):
    return False
  decoders['F'] = decode_false

  def decode_list(self):
    l = []
    while True:
      b = self.ReadByte()
      if b == ']': return l
      m   = self.decoders[b]
      if m: l.append(m(self))
  decoders['['] = decode_list

  def decode_binary(self):
    length = self.decode_varuint()
    v = ''
    if length>0:
      v = self.ReadByte(length)
    return v

  def decode_string(self):
    s = self.decode_binary()
    return s.decode('utf-8')
  decoders['f'] = decode_string
  decoders['B'] = decode_binary
  decoders['S'] = decode_string
  decoders['X'] = decode_string

  class Parms(dict):
    def get(self, index, defval = None):
      try:
        return self[index]
      except:
        if defval == None: defval = 0
        return defval

  def decode_parms(self):
    parms = self.Parms()
    m = True
    while m != None:
      b = self.ReadByte()
      if self.stopped or b == 'z': break
      if b != 'N':
        m   = self.decoders[b]
        tag = self.decode_varuint()
        if m: parms[tag] = m(self)
      else:
        #print "response error ", self.ReadByte() # shall be z
        self.decoded.set()
        raise ResponseError
    self.decoded.set()
    return parms

  class Event(object):
    def __init__(self, transport):
      self.module_id = transport.decode_varuint()
      self.target    = transport.root
      self.event_id  = transport.decode_varuint()
      self.transport = transport
      self.parms     = transport.decode_parms()
    def dispatch(self):
      target = self.target
      if self.module_id != 0:
        target = Cached.exists(module_id2classes[self.module_id],self.parms[0], 'Event')
        if target == None:
          if self.transport.logger: self.transport.logger.debug('IGNORE EVENT mod=%d ev=%d oid=%d' % (self.module_id,self.event_id,self.parms[0]))
          return
      #else:
      #  stat_logger.ReachObj(0, 0, True, 'Event')
      if self.transport.logger: self.transport.logger.info('DISPATCH EVENT mod=%d ev=%d oid=%d' % (self.module_id,self.event_id,target.object_id))
      getattr(target,target.event_handlers[self.event_id])(self.parms)

  def decode_event(self):
    # push the event in the event queue
    self.event_queue.put(SkypeKit.Event(self))
  decoders['E'] = decode_event

  class PropertyChange(object):
    def __init__(self, transport):
      self.logger = transport.logger
      self.transport = transport
      self.modid  = transport.decode_varuint()
      self.oid    = transport.decode_varuint() # obj id
      kind        = transport.ReadByte()       # prop kind
      self.propid = transport.decode_varuint() # prop id
      if kind != 'N': self.val = transport.decoders[kind](transport)
      transport.ReadByte(4) # ]]]z
      transport.decoded.set()
    def dispatch(self):
      o = Cached.exists(module_id2classes[self.modid],self.oid, 'PropertyChangeEvent')
      if o == None:
        if self.logger: self.logger.debug('IGNORE CHANGE PROPERTY mod=%d oid=%d prop=%d' % (self.modid, self.oid, self.propid))
        return
      try:
        propname = o.propid2label[self.propid]
      except KeyError:
        return
      o.rwlock.acquire()
      o.properties[self.propid] = self.val
      o.rwlock.release()
      if self.logger: self.logger.info('CHANGED PROPERTY mod=%d oid=%d prop=%s' % (self.modid, self.oid, propname))
      #stat_logger.ReachProp(self.modid, self.oid, self.propid, self.propid in o.properties, 'PropertyChangeEvent')
      print o,'.OnPropertyChange(',propname,'): ',repr(self.val)
      o.OnPropertyChange(propname)

  def decode_property_change(self):
    # push the event in the event queue
    self.event_queue.put(SkypeKit.PropertyChange(self))
  decoders['C'] = decode_property_change

  def XCallResponse(self):
    rid = self.decode_varuint()
    self.pending_lock.acquire()
    ev = self.pending_requests[rid]
    del self.pending_requests[rid]
    self.pending_lock.release()
    ev.set()
  decoders['r'] = XCallResponse

  def Start(self):
    while not self.stopped:
      if self.ReadByte(1,False) == 'Z':
        if self.stopped: return
        cmd = self.ReadByte()
        if self.stopped: return
        if self.logger: self.logger.debug('Processing %c' % cmd)
        m = self.decoders[cmd]
        if m:
          m(self)
          self.decoded.wait()
          self.decoded.clear() # shall be done immediatly after set?
        if self.logger: self.logger.debug('Done processing %c' % cmd)

  def Stop(self):
    if not self.stopped:
      self.stopped = True
      if self.logger: self.logger.info('stopping...')
      self.decoded.set() # ensure that Listener thread resumes
      self.event_queue.put({}) # ensure that event thread resumes
      for e in self.pending_gets: e.set()
      for k in self.pending_requests: self.pending_requests[k].set()
      if self.socket:
        self.socket.close()
        self.socket = None


class Request:
  def __init__(self):
    self.tokens = array.array('B')
    #self.tokens.append(ord('Z'))
  def Send(self):
    tok = self.tokens
    tok.append(ord('z'))
    self.tokens = None
    return tok
  encoders = { }

  def encode_varint(self, number):
    if number >= 0: number = number << 1
    else: number = (number << 1) ^ (~0)
    self.encode_varuint(number)
  encoders['i'] = encode_varint

  def encode_varuint(self, number):
    tok = self.tokens
    while 1:
      towrite = number & 0x7f
      number = number >> 7
      if number == 0:
        tok.append(towrite)
        break
      tok.append(0x80|towrite)
  encoders['u'] = encode_varuint
  encoders['e'] = encode_varuint
  encoders['o'] = encode_varuint

  def encode_objectid(self, val):
    self.encode_varuint(val.object_id)
  encoders['O'] = encode_objectid

  def encode_string(self, val):
    tok = self.tokens
    if isinstance(val, unicode):
      val=val.encode('utf-8')
    length = len(val)
    self.encode_varuint(length)
    if length>0:
      tok.fromstring(val)
  encoders['S'] = encode_string
  encoders['X'] = encode_string
  encoders['f'] = encode_string
  encoders['B'] = encode_string

  def AddParm(self, kind, tag, val):
    tok = self.tokens
    if isinstance(val, list):
      tok.append(ord('['))
      self.encode_varuint(tag)
      encoder = self.encoders[kind]
      for v in val:
        if kind != 'b':
          tok.append(ord(kind))
          encoder(self, v)
        else:
          if v: tok.append(ord('T'))
          else: tok.append(ord('F'))
      tok.append(ord(']'))
    elif kind != 'b':
      tok.append(ord(kind))
      if tag == 0: self.oid = val.object_id
      self.encode_varuint(tag)
      self.encoders[kind](self, val)
    else:
      if val: tok.append(ord('T'))
      else:   tok.append(ord('F'))
      self.encode_varuint(tag)
    return self

class XCallRequest(Request):
  __request_id = 0
  def __init__(self, header, module_id, method_id):
    Request.__init__(self)
    self.tokens.fromstring(header)
    self.module_id = module_id
    self.method_id = method_id
    self.oid       = 0
    tok = self.tokens
    #tok.append(ord('R'))
    self.rid = XCallRequest.__request_id
    XCallRequest.__request_id = XCallRequest.__request_id + 1 # mutexed?
    #self.encode_varuint(module_id)
    #self.encode_varuint(method_id)
    self.encode_varuint(self.rid)

class GetRequest(Request):
  def __init__(self, header, object_id):
    Request.__init__(self)
    tok = self.tokens
    tok.fromstring(header)
    self.encode_varuint(object_id)
    tok.fromstring(']]z')
  def Send(self):
    tok = self.tokens
    self.tokens = None
    return tok

class MultiGetRequest(Request):
  def __init__(self, header, objects):
    Request.__init__(self)
    tok = self.tokens
    tok.fromstring(header)
    pref = ''
    for o in objects:
      tok.fromstring(pref)
      self.encode_varuint(o.object_id)
      pref = ','
    tok.fromstring(']]z')
  def Send(self):
    tok = self.tokens
    self.tokens = None
    return tok
