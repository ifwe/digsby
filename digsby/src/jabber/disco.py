from __future__ import with_statement
from contextlib import contextmanager

import pyxmpp.jabber.disco as disco_
import time
from pyxmpp.all import JID
from logging import getLogger
from threading import RLock
log = getLogger('jabber.disco')
from itertools import ifilter
from datetime import timedelta

def items_start(func):
    def wrapper(self, *arg, **kwargs):
        self._items_outstanding = True
        func(self, *arg, **kwargs)
    return wrapper

def items_end(func):
    def wrapper(self, *arg, **kwargs):
        func(self, *arg, **kwargs)
        self._items_outstanding = False
        self.check()
    return wrapper

def info_start(func):
    def wrapper(self, *arg, **kwargs):
        self._info_outstanding = True
        func(self, *arg, **kwargs)
    return wrapper

def info_end(func):
    def wrapper(self, *arg, **kwargs):
        func(self, *arg, **kwargs)
        self._info_outstanding = False
        self.check()
    return wrapper

class DiscoInfoStorage(object):
    __slots__ = """
                address
                identities
                features
                """.split()
    def __init__(self, address, identities, features):
        self.address    = address
        self.identities = identities
        self.features   = features

class DiscoIdentStorage(object):
    __slots__ = """
                name
                category
                type
                """.split()
    def __init__(self, ident):
        self.name     = ident.get_name(),
        self.category = ident.get_category(),
        self.type     = ident.get_type()

class Disco(object):
    def __init__(self, cache, jid, show=True, finished_handler=None):
        self.cache   = cache
        self.pending = 0
        self.lock    = RLock()
        self.infos   = {}
        self.hierarchy = {}
        self.jid = JID(jid)
        self.show = show
        self.finished_handler = finished_handler

        self.start = time.clock()

        self.get((self.jid, None))

    def fetch_info(self, address):
        log.info('fetching %s info', address)
        self.cache.request_object(disco_.DiscoInfo, address, state='old',
                                  object_handler=self.info_response,
                                  error_handler=self.info_err,
                                  timeout_handler=self.info_time,
                                  timeout = timedelta(seconds=5))

    def fetch_items(self, address):
        log.info('fetching %s items', address)
        self.cache.request_object(disco_.DiscoItems, address, state='old',
                             object_handler=self.items_response,
                             error_handler=self.items_err,
                             timeout_handler=self.items_time,
                             timeout = timedelta(seconds=5))

    def get(self, addr):
        with self.add():
            self.fetch_info(addr)
            self.fetch_items(addr)

    def info_response(self, address, value, state):
        with self.sub():
            log.info('info response')
            try:
                idents = [DiscoIdentStorage(i.get_name(),
                                            i.get_category(),
                                            i.get_type())
                          for i in value.identities]
                self.infos[address] = DiscoInfoStorage(address,
                                                       idents,
                                                       value.features)
            except Exception, e:
                log.info('%r', e)
                raise e

    def info_err(self, address, error_data):
        with self.sub():
            log.info('info error')
            self.infos[address] = str(error_data)

    def info_time(self, address):
        with self.sub():
            log.info('info timeout')
            self.hierarchy[address] = None

    def items_response(self, address, value, state):
        with self.sub():
            log.info('items response')
            itms = value.get_items()
            if itms:
                its   = {}
                print its
                for item in itms:
#                    print 'setting %r: %r' % ((item.jid, item.node), (item.name, item.action))
                    its.__setitem__((item.jid, item.node), (item.name, item.action))
    #            [ ]
                self.hierarchy[address] = its
                for addy in its:
                    self.get(addy)

    def items_err(self, address, error_data):
        with self.sub():
            log.info('items error')
            self.hierarchy[address] = None

    def items_time(self, address):
        with self.sub():
            log.info('items timeout')
            self.hierarchy[address] = None

    @contextmanager
    def sub(self):
        with self.lock:
            try:
                yield self
            finally:
                self.pending -= 1
                log.info('subtracting 1, self.pending is now %d', self.pending)
                if not self.pending:
                    self.end = time.clock()
                    if self.show:
                        import wx
                        wx.CallAfter(DiscoViewer, (self.jid, None), self.hierarchy, self.infos, expand=True, title=None)
                    if self.finished_handler:
                        self.finished_handler(self)

    @contextmanager
    def add(self):
        with self.lock:
            try:
                self.pending += 2
                log.info('adding 2,      self.pending is now %d', self.pending)
                yield self
            finally:
                pass

    def find_feature(self, feature):
        return list(self.find_feature_iter(feature))

    def find_feature_iter(self, feature):
        return ifilter(lambda i: feature in i.features
                       if hasattr(i, 'features') else None,
                       self.infos.itervalues())

import wx
import util

class DiscoViewer(wx.Frame):
    def __init__(self, key, item_dict, info_dict, expand=False, title=None):
        wx.Frame.__init__(self, parent=None, id = -1, title = title if title else "DiscoViewer")
        util.persist_window_pos(self, close_method=self.on_close)
        self.content = wx.BoxSizer(wx.VERTICAL)
        self.expand = expand

        self.item_dict = item_dict
        self.info_dict = info_dict

        #generate new tree control
        tree_id = wx.NewId()
        self.tree = wx.TreeCtrl(self, tree_id)
        self.content.Add(self.tree,1,wx.GROW)

        self.rootId = self.tree.AddRoot('Root')
        if key: self(key)

        self.SetSizer(self.content)
        self.Show(True)

    def __call__(self, key, parent_id=None):
        parent_id = parent_id or self.rootId
        info     = self.info_dict[key]
        children = self.item_dict[key] if key in self.item_dict else {}

        idents = info.identities
        name = ""
        for ident in idents:
            if name: name += ' / '
            name += ident.name

        child_id = self.tree.AppendItem(parent_id, name)
        for c in children:
            id = self(c,child_id)
            if self.expand: self.tree.Expand(id)
        if self.expand:
            self.tree.Expand(child_id)
            self.tree.Expand(self.rootId)
        return child_id

    def on_close(self, e):
        self.Destroy()

from util import lock

class DiscoNode(object):
    #in general, functions in this class are only sub-routines
    def __init__(self, cache, jid, node=None, name=None):
        self.lock    = RLock()
        self.cache = cache
        #jid of this item
        self.jid = JID(jid)
        #node part of address
        self.node = node
        #Item description
        self.name = name
        #a list of namespaces
        self.features = []
        #a list of DiscoIdentStorage with category(req), type(req), and name(opt)
        self.identities = []
        #a list of "child" DiscoNode
        self.items = []
        self.info_error_data    = False
        self.items_error_data   = False
        self._info_outstanding  = False
        self._items_outstanding = False
        self._children_outstanding = 0

    @property
    def address(self):
        '''
        Service Discovery address (jid, node)
        '''
        return (self.jid, self.node)

    @lock
    @info_start
    def fetch_info(self, state='old'):
        '''
        fetches the disco#info response for this address
        @param state: lowest acceptable cache state for the response
        '''

        log.info('fetching info for %r', self)
        self.cache.request_object(disco_.DiscoInfo, self.address, state=state,
                                  object_handler=self.__info_response,
                                  error_handler=self.__info_error,
                                  timeout_handler=self.__info_timeout,
                                  timeout = timedelta(seconds=self.timeout_duration))

    @lock
    @info_end
    def __info_response(self, address, value, _state):
        log.info('info response for %r', self)
        try:
            self.idents = [DiscoIdentStorage(i) for i in value.identities]
            self.features = value.features
        except Exception, e:
            log.info(repr(e))
            raise

    @lock
    @info_end
    def __info_error(self, address, error_data="TimeOut"):
        log.warning('info error for %r', self) if error_data != "TimeOut" \
            else log.warning('info timout for %r', self)
        self.idents     = []
        self.features   = []
        self.info_error_data = error_data

    __info_timeout = __info_error

    @lock
    @items_start
    def fetch_items(self, state='old'):
        '''
        fetches the disco#items response for this address
        @param state: lowest acceptable cache state for the response
        '''
        log.info('fetching items for %r', self)
        self.cache.request_object(disco_.DiscoItems, self.address, state=state,
                             object_handler=self.__items_response,
                             error_handler=self.__items_error,
                             timeout_handler=self.__items_timeout,
                             timeout = timedelta(seconds=self.timeout_duration))

    @lock
    @items_end
    def __items_response(self, address, value, state):
        log.info('items response for %r', self)
        del self.items[:]
        len_ = len([self.items.append(DiscoNode(self.cache, item.jid, item.node, item.name))
                    for item in value.get_items()])
        if self.depth_to_check:
            self._children_outstanding += len_
            [item.fetch(callback=self.__child_done, depth=self.depth_to_check-1,
                        state=self.fetching_state, info = self.fetching_info,
                        items=self.fetching_items, timeout_duration = self.timeout_duration)
                        for item in self.items]

    @lock
    def __child_done(self, child):
        self._children_outstanding -= 1
        self.check()

    @lock
    @items_end
    def __items_error(self, address, error_data="TimeOut"):
        log.warning('items error for %r', self) if error_data != "TimeOut" \
            else log.warning('items timout for %r', self)
        del self.items[:]
        self.items_error_data = error_data

    __items_timeout = __items_error

    @lock
    def fetch(self, callback=None, depth=0, state='old', info=True, items=True, timeout_duration=5):
        '''
        fetches information about this and "child" DiscoNodes

        @param callback: function to call when this fetch is complete,
                         takes one argument, will be this DiscoNode object
        @param depth:    depth to fetch information:
                         items depth is depth-1
        @param state:    lowest acceptable cache state for the response(s)
        @param info:     boolean: get #info ?
        @param items:    boolean: get #items ? if False, depth can only be 0
        '''

        assert depth >= 0
        if not items: assert depth == 0
        self.fetching_info = info
        self.fetching_items = items
        self.depth_to_check = depth
        self.callback = callback
        self.fetching_state = state
        self.timeout_duration = timeout_duration
        if info:  self.fetch_info(state)
        if items and depth-1>=0: self.fetch_items(state)

    @lock
    def check(self):
        '''
        check if conditions are right to call the callback
        '''
        if self._info_outstanding \
        or self._items_outstanding \
        or self._children_outstanding > 0:
            return

        #magic callback here
        if self.callback is not None:
            self.callback(self)

    def find_feature(self, feature, depth=0):
        '''
        Searches the tree for a certain namespace,
        returns a list of matching nodes

        @param feature: namespace to find
        @param depth:   depth to search (depth 0 = only this node)
        '''

        assert depth >= 0
        l = []
        if feature in self.features:
            l.append(self)
        if depth > 0:
            for child in self.items:
                l.extend(child.find_feature(feature, depth-1))
        return l

    def __repr__(self):
        return "<DiscoNode %(name)s: %(address)r>" % dict(name=self.name,
                                                          address=self.address)
