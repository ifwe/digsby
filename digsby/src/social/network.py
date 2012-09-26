import hooks
import logging
from rpc.jsonrpc import Dsuccess, Derror
log = logging.getLogger('social.network')

from util import try_this, Storage
from common import AccountBase, profile, UpdateMixin, FromNetMixin, pref

class SocialNetwork(UpdateMixin, AccountBase, FromNetMixin):
    filters = {}
    header_funcs = []
    timer = Null

    def __init__(self, enabled = True,  **options):
        AccountBase.__init__(self, **options)
        UpdateMixin.__init__(self, **options)
        FromNetMixin.__init__(self, **options)

        self.enabled = enabled
        self._dirty_error = True # The next error is new

    @property
    def dirty(self):
        return self._dirty

    @property
    def display_name(self):
        return try_this(lambda: getattr(self, pref('social.display_attr')), self.username)

    def _decryptedpw(self):
        return profile.plain_pw(self.password)

    def update_info(self, **info):
        force = info.pop('force', None)
        self._dirty_error = True
        for k, v in info.iteritems():
            setattr(self, k, v)
        self.notify()

#        if self.OFFLINE and self.enabled:
#            self.update_now()

        # Tell the server.
        profile.update_account(self, force = force)

    def get_options(self):
        try:
            get_opts = super(SocialNetwork, self).get_options
        except AttributeError:
            opts = {}
        else:
            opts = get_opts()
        #updatefreq is not user settable, so we don't need to store it
        opts.pop('updatefreq', None)
        return opts

    @property
    def icon(self):
        from gui import skin
        from util import try_this
        return try_this(lambda: skin.get('serviceicons.%s' % self.protocol), None)

    def error_link(self):
        reason = self.Reasons

        if self.protocol_info().get('needs_password', True):
            bplinkref = (_('Edit Account'), lambda *a: profile.account_manager.edit(self, True))
        else:
            bplinkref =(_('Retry'), lambda *a: self.Connect())


        linkref = {
            reason.BAD_PASSWORD     : bplinkref,
            reason.CONN_FAIL        : (_('Retry'),     lambda *a: self.Connect()),
            reason.OTHER_USER       : (_('Reconnect'), lambda *a: self.update_now()),
            reason.CONN_LOST        : (_('Retry'),     lambda *a: self.update_now()),
            reason.WILL_RECONNECT   : (_('Retry'),     lambda *a: self.update_now()),
            reason.NONE             : None,
        }
        if self.offline_reason in linkref:
            return linkref[self.offline_reason]
        else:
            log.debug('Couldn\'t find offline reason %r in linkref dictionary. Returning None for error_link',
                      self.offline_reason)
            return None

    @property
    def service(self):
        raise NotImplementedError

    @property
    def protocol(self):
        raise NotImplementedError

    def Connect(self, *a, **k):
        raise NotImplementedError
#        self.change_state(self.Statuses.ONLINE)

    def Disconnect(self, *a, **k):
        raise NotImplementedError
#        self.change_state(self.Statuses.OFFLINE)
#    disconnect = Disconnect
    def disconnect(self, *a, **k):
        raise NotImplementedError

    def observe_count(self,callback):
        return NotImplemented
        #self.add_gui_observer(callback, 'count')

    def observe_state(self, callback):
        return NotImplemented
        #self.add_gui_observer(callback, 'enabled')

    def unobserve_count(self,callback):
        return NotImplemented
        #self.remove_gui_observer(callback, 'count')

    def unobserve_state(self,callback):
        return NotImplemented
        #self.remove_gui_observer(callback)


import weakref
weak_socialfeeds = weakref.WeakValueDictionary()

def on_dirty(ctx):
    try:
        feed = weak_socialfeeds[ctx]
    except KeyError:
        log.warning('SocialFeed marked dirty but not in weak dictionary: %r', ctx)
    else:
        feed.set_dirty()

hooks.register('social.feed.mark_dirty', on_dirty)

class SocialFeed(object):
    '''
    allows plugins to use social.feed.* hooks to inject things into social feeds
    '''

    def __init__(self, id_, feed_context, get_feed_items, render_items, set_dirty=None):
        assert hasattr(render_items, '__call__')
        assert hasattr(get_feed_items, '__call__')

        self.id = id_  # globally unique, i.e. account_id + name + subtype.  Must be hashable
        self.context = feed_context # for use by whatever is creating the SocialFeed
        self.get_feed_items = get_feed_items
        self.render_items = render_items


        self.iterators = {}

        hooks.notify('social.feed.created', self.id)

        self.set_dirty_cb = set_dirty

        weak_socialfeeds[self.id] = self

    def set_dirty(self):
        if self.set_dirty_cb is not None:
            self.set_dirty_cb()
        else:
            log.warning('%r dirty hook called, but has no callback', self)

    def get_iterator(self):
        iterator_info = Storage(id=self.id,
                                context=self.context,
                                iterator=self.get_feed_items())

        # allow plugins to wrap/transform the generator
        return hooks.reduce('social.feed.iterator', iterator_info).iterator

    def new_ids(self, ids):
        hooks.notify('social.feed.updated', self.id, ids)

    def jscall_initialize_feed(self, webview, _id):
        self.iterators.pop(webview, None)

    def jscall_next_item(self, webview, id):
        try:
            it = self.iterators[webview]
        except KeyError:
            it = self.iterators[webview] = self.get_iterator()

        try:
            item = it.next()
        except StopIteration:
            Derror(id, webview)
        else:
            Dsuccess(id, webview, html=self.render_items([item], self.context))

