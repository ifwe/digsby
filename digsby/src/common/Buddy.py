"""

ooo eee ooo I look just like Buddy Holly

"""
from __future__ import with_statement
from threading import RLock
from util.callbacks import callsback
from traceback import print_exc
from util.threads import threaded
from util.primitives.error_handling import traceguard
from util.primitives.funcs import do, readonly
from util.primitives.mapping import Storage
from util.primitives.synchronization import lock
from digsby_chatlogs.interfaces import IAliasProvider
import traceback

import os.path, wx, cPickle, stat
from os.path import isfile, join as pathjoin, exists as pathexists
from cStringIO import StringIO

from util import Timer
import stdpaths
from path import path
from util.observe import Observable, ObservableProperty as oproperty
from common.actions import ObservableActionMeta, action
from common import profile
from PIL import Image
from time import time

from gui.toolbox import calllimit

from logging import getLogger; log = getLogger('Buddy'); info = log.info

from common.buddyicon import _rate_limited_icon_get

class FileTransferException(Exception):
    pass

ICON_HASH_FILE = 'iconhashes.dat'
#
# loading
#
def load_hashes():
    '''
    Loads icon hashes from
    '''

    assert 'hashes' not in globals()     # make sure only called once
    global hashes
    global cache_path

    hashes = {}

    # save icon hashes on exit
    wx.GetApp().PreShutdown.append(write_hashes)

    cache_path = pathjoin(stdpaths.userlocaldata, 'cache')

    if not pathexists(cache_path):
        os.makedirs(cache_path)

    elif pathexists(cache_path):
        hash_filename = pathjoin(cache_path, ICON_HASH_FILE)

        if not pathexists(hash_filename):
            log.info('no icon hash file %r found', hash_filename)
        else:
            try:
                with file(hash_filename, 'rb') as f:
                    hashes = cPickle.load(f)
                    return
            except Exception:
                log.critical('error loading icon hashes from %r', hash_filename)
                print_exc()


#
# saving
#
hash_lock = RLock()

def buddy_icon_key(buddy):
    return buddy.service


@calllimit(5)
def write_hashes():
    'Called on program exit. (Should probably be periodically instead.)'

    if not 'hashes' in globals(): load_hashes()
    global hashes

    log.info('writing icon hashes')

    with hash_lock:
        try:
            with file(pathjoin(cache_path, 'iconhashes.dat'), 'wb') as f:
                cPickle.dump(hashes, f)
        except Exception:
            log.critical('error writing icon hashes')
            print_exc()

def icon_path_for(buddy):
    "Returns a path for the buddy's cached icon."
    if not 'cache_path' in globals(): load_hashes()
    bname = buddy.name
    if isinstance(bname, bytes):
        bname = bname.decode('fuzzy utf8').encode('filesys')
    elif isinstance(bname, unicode):
        bname = bname.encode('filesys')

    return pathjoin(cache_path, buddy_icon_key(buddy), '%s_ICON.dat' % bname).decode('filesys')

def get_disk_icon_hash(buddy):
    'Returns the icon hash on disk for a buddy, if any exists.'

    if not 'hashes' in globals(): load_hashes()
    global hashes

    protoname = buddy_icon_key(buddy)

    try:
        protohashes = hashes[protoname]
    except KeyError:
        return None
    else:
        return protohashes.get(buddy.name, None)

def get_cached_icon(buddy):
    '''

    @param buddy:

    @return bitmap, hash
            None, None (invalid) or string, string (valid)
    '''

    if not 'hashes' in globals(): load_hashes()
    global hashes

    icon_path = icon_path_for(buddy)
    if not isfile(icon_path):
        return None, None

    try:
        icon_file = open(icon_path, 'rb')
        data = icon_file.read()
    except Exception:
        print_exc()
        return None, None

    icon_file.close()

    if not buddy.name in hashes.setdefault(buddy_icon_key(buddy), {}):
        return None, None
    else:
        hash = hashes[buddy_icon_key(buddy)][buddy.name]

    if len(data) == 0:
        return "empty", hash

    try:
        img = Image.open(StringIO(data))
    except Exception:
        log.critical('%s was not an icon, removing it', icon_path)
        try: os.remove(icon_path)
        except Exception: log.critical('could not remove nonimage icon %s',  icon_path)

        return None, None

    img.path = unicode(icon_path) + unicode(time())
    return img, hash

def save_cached_icon(buddy, imgdata, imghash):
    global hashes

    full_path = icon_path_for(buddy)

    dir, file = os.path.split(full_path)
    if not pathexists(dir):
        try:
            os.makedirs(dir)
        except Exception:
            traceback.print_exc()

    # Write the icon to disk.
    try:
        with open(full_path, 'wb') as f:
            f.write(imgdata)
    except Exception:
        traceback.print_exc()
    else:
        assert imghash

        with hash_lock:
            hashes.setdefault(buddy_icon_key(buddy),{})[buddy.name] = imghash

def get_bname(b):
    try:
        return b.name
    except AttributeError:
        assert isinstance(b, basestring), "can't get a bname from %r" % b
        return str(b)

# todo: online is not a legal status!!!
available_fix = {'online': 'available',
                 'normal': 'available'}

def get_status_orb(contact):
    st = contact.status.lower()
    st = available_fix.get(st, st)

    if st == 'unknown':
        pass
    elif contact.mobile:
        st = 'mobile'
    elif not contact.online:
        st = 'offline'
    elif st == 'idle' or contact.idle:
        st = 'idle'
    elif contact.away:
        st = 'away'

    return st

def get_log_size(buddy):
    return get_log_size_tup(buddy.name, buddy.service)

def get_log_size_tup(name, service):
    return profile.logger.logsize_for_nameservice(name, service)

class LogSizeDict(dict):
    def __init__(self):
        dict.__init__(self)
        self.needed = dict()
        self.triggered = False

    @lock
    def __missing__(self, key, initialize=True):
        if initialize:
            self.needed[key] = []
        self.__setitem__(key, 0)
        if not self.triggered:
            self.triggered = True
            self.trigger()
        return 0

    def trigger(self):
        Timer(.1, self.do_disk_access, success=self.update).start()

    @threaded
    def do_disk_access(self):
        with self._lock:
            needed = self.needed
            self.needed = dict()
        retval = dict()
        for key in needed:
            retval[key] = get_log_size_tup(*key)

        log.info("getting %d log sizes: %r", len(needed), needed)
        return retval, needed

    def update(self, d):
        with self._lock:
            newvals, retrieved = d
            for key in newvals:
                self.needed.pop(key, None)
            if not self.needed:
                self.triggered = False
            else:
                self.trigger()
        try:
            retval = dict.update(self, newvals)
        except Exception:
            raise
        else:
            for val in retrieved.values():
                for buddy in val:
                    with traceguard:
                        buddy.notify('log_size')
            return retval
        finally:
            profile.blist.rebuild()

    @lock
    def notify_get(self, key, buddy):
        if key in self.needed:
            assert key in self
            self.needed[key].append(buddy)
            return self[key]
        if key not in self:
            self.needed[key] = [buddy]
            return self.__missing__(key, initialize=False)
        else:
            return self[key]

    @lock
    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    @lock
    def __setitem__(self, key, value):
        return dict.__setitem__(self, key, value)



class Buddy(Observable):
    __metaclass__ = ObservableActionMeta
    _icon_requests = 0
    _get_image_min_once = False

    def __init__(self, name, protocol):
        Observable.__init__(self)
        self.add_observer(self.store_remote_alias, 'remote_alias')
        self.name = name
        self.protocol = protocol
        self._notify_dirty = True

        self.entering = self.leaving = False

        # all Buddy slots default to None!
        do(setattr(self, s, None) for s in [
        'icon_bitmap'])

        self.icon_hash = self.get_icon_hash()
        self._getting_image = False
        self._cached_hash   = None
        self.icon_disabled  = False

        # register with the BuddyWatcher
        try:
            register = profile.account_manager.buddywatcher.register
        except AttributeError:
            log.debug('No buddy watcher to register with')
            return
        else:
            register(self)

    @property
    def supports_group_chat(self):
        return getattr(self.protocol, 'supports_group_chat', False)

    def store_remote_alias(self, obj, attr, old, new):
        if attr is None or attr == 'remote_alias':
            IAliasProvider(profile()).set_alias(self.name, self.service, protocol=self.protocol.service, alias=self.alias)

    def raise_proto_impl_err(self, prop=""):
        "Raise an error if a connection protocol is missing a property."
        raise NotImplementedError("%s has not implemented a required property %s" %
                                  (getattr(self, '__class__', str(self)), prop))

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)

    nice_name = readonly('name')

    @property
    def online(self): self.raise_proto_impl_err('online')
    @property
    def mobile(self): self.raise_proto_impl_err('mobile')
    @property
    def status_message(self): self.raise_proto_impl_err('status_message')
    @property
    def stripped_msg(self):
        return self.status_message or u''
    @property
    def idle(self): self.raise_proto_impl_err('idle')
    @property
    def away(self): self.raise_proto_impl_err('away')

    @property
    def blocked(self): self.raise_proto_impl_err('blocked')

    def _set_isbot(self, isbot):
        from common import caps
        if isbot:
            self.caps.add(caps.BOT)
        else:
            self.caps.discard(caps.BOT)

    @property
    def isbot(self):
        from common import caps
        return caps.BOT in self.caps

    bot = isbot

    @property
    def service(self):
        return self.protocol.name

    @property
    def serviceicon(self):
        from gui import skin
        return skin.get('serviceicons.%s' % self.service)

    @property
    def pending_auth(self):
        '''Subclasses can override this to indicate that the buddy is waiting
        for a user's authorization.'''
        return False

    @property
    def sms(self):
        return False

    def get_caps(self):
        "Returns this buddy's capabilities."
        from common import caps

        if self.sms:
            # SMS buddies only have the SMS capability.
            return set([caps.SMS])
        else:
            # otherwise fall back to the protocol
            buddy_caps = set(self.protocol.caps)

            # remove "files" if offline
            if not self.online:
                # What about invisible buddies?
                buddy_caps.discard(caps.FILES)
                buddy_caps.discard(caps.VIDEO)

            return buddy_caps

    caps = property(get_caps)

    def imwin_mode(self, mode):
        from gui.imwin import begin_conversation
        begin_conversation(self, mode = mode)

    @action(lambda self: 'IM' in self.caps)
    def chat(self):       self.imwin_mode('im')

    @action(lambda self: 'INFO' in self.caps)
    def buddy_info(self): self.imwin_mode('info')

    @action(lambda self: 'EMAIL' in self.caps)
    def send_email(self): self.imwin_mode('email')

    @action(lambda self: 'SMS' in self.caps)
    def send_sms(self):   self.imwin_mode('sms')

    def idstr(self):
        # If this changes, please change Contact.__hash__
        return '/'.join([self.protocol.name,
                         self.protocol.username,
                         self.name])

    @property
    def alias(self):
        a = profile.get_contact_info(self, 'alias')
        if a: return a

        a = getattr(self, 'local_alias', None)
        if a: return a

        a = getattr(self, 'remote_alias', None)
        if a: return a

        return self.name

    @property
    def local_alias(self):
        return profile.blist.get_contact_info(self, 'alias')

    @action(lambda self, *a: None if self.blocked else True)
    @callsback
    def block(self, set_blocked = True, callback = None):
        self.raise_proto_impl_err('block')

    def equals_chat_buddy(self, chat_buddy):
        return self == chat_buddy

    @action(lambda self, *a: True if self.blocked else None)
    @callsback
    def unblock(self, callback = None):
        self.raise_proto_impl_err('unblock')

    @action(lambda self, *a: self.online and 'FILES' in self.caps)
    def send_file(self, filepath = None):
        if filepath is None:
            from hub import Hub
            filepath = Hub.getInstance().get_file('Sending file to %s' % self.name)

        if filepath:
            finfo = fileinfo(filepath)
            if finfo.size:
                if self.online:
                    xfer = self.protocol.send_file(self, finfo)
                    profile.xfers.insert(0, xfer)
            else:
                from hub import Hub
                Hub.getInstance().on_error(FileTransferException('%s is an empty file' % finfo.name))

    def send_folder(self, dirpath = None):
        from hub import Hub
        if dirpath is None:
            dirpath = Hub.getInstance().get_dir('Choose a directory to send '
                                                'to %s.' % self.name)
        if dirpath:
            finfo = fileinfo(dirpath)
            if len(finfo.files) == 0:
                Hub.getInstance().on_error(ValueError('No files in that directory.'))
            elif finfo.size == 0:
                Hub.getInstance().on_error(ValueError('There are zero bytes in that directory.'))
            else:
                self.protocol.send_file(self, finfo)


    @action()
    def remove(self, protocol_obj):
        self.protocol.remove_buddy(protocol_obj)

    @property
    def icon_path(self):
        return path(icon_path_for(self))

    @property
    def num_online(self):
        return int(self.online)

    def notify(self, attr = None, *a, **k):
        # TODO: fix this when we have a better presence system
        self._notify_dirty = True
        profile.blist.buddy_changed(self, attr)

        return Observable.notify(self, attr, *a, **k)

    @property
    def cache_path(self):
        # cached attributes go in TEMPDIR + the following path
        proto = self.protocol
        return pathjoin(proto.name, self.name) + '.dat'

    @property
    def info_key(self):
        return self.name + '_' + self.service

    email_hint = property(lambda self: self.protocol.email_hint(self))

    @property
    def history(self):
        return profile.logger.history_for_safe(self.protocol, self)

    @property
    def icon(self):
        if self.icon_disabled:
            return None

        if self.icon_bitmap is None:
            # check the disk for a cached icon
            bitmap, hash = get_cached_icon(self)
            #if nothing got loaded, flag that we tried and failed with -1
            self.icon_bitmap = bitmap if bitmap is not None else -1
            self._cached_hash = hash   if bitmap is not None else -1

        nh = self.icon_hash #network hash (nh)
        #if we've loaded and it's good:
        if self.icon_bitmap is not None and self.icon_bitmap is not-1:
            #if we're not already getting the image
            #  and we have a hash
            #  and it's not the same as before:
            if not self._getting_image and nh is not None and nh != self._cached_hash:
                self._getting_image = True
                _rate_limited_icon_get(self)
        else:
        #if we don't have an image
            #if we have a new hash and we're not already getting it
            if (nh or self._get_image_min_once) and not self._getting_image:
                self._getting_image = True
                _rate_limited_icon_get(self)

        if self.icon_bitmap is not None and self.icon_bitmap is not -1:
            if isinstance(self.icon_bitmap, str) and self.icon_bitmap == "empty":
                return None
            else:
                return self.icon_bitmap
        else:
            return None

    def cache_icon(self, icon_data, icon_hash):
        self.icon_bitmap, self._cached_hash, self._getting_image = None, None, False
        save_cached_icon(self, icon_data, icon_hash)
        wx.CallAfter(write_hashes)

        # Notify the GUI
        self.notify('icon')

    def get_icon_hash(self):
        return get_disk_icon_hash(self)

    @property
    def log_size(self):
        return profile.log_sizes.notify_get((self.name, self.service), self)

    def increase_log_size(self, num_bytes):
        profile.log_sizes[(self.name, self.service)] += num_bytes
        self.notify('log_size')

    def __eq__(self, b):
        s = object()

        return getattr(b, 'name', s) == self.name \
            and getattr(b, 'protocol', ) is self.protocol

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.info_key)

    # used to store active notificiations
    status_notifies = {}

    def _set_status(self, status):
        status = {'online': 'available'}.get(status, status)
        self.setnotifyif('status', status)

    status_orb = oproperty(lambda self: get_status_orb(self), observe = 'status')

    @property
    def sightly_status(self):
        return self.status.title()

    @property
    def pretty_profile(self): return u''

    @property
    def buddy_icon(self):
        '''
        Returns a 32 pixel version of this buddy's icon (or the generic
        replacement icon for buddies without icons).
        '''

        from gui.buddylist.renderers import get_buddy_icon
        return get_buddy_icon(self, 32, False)

    def view_past_chats(self, fromacct = None):
        if fromacct is None:
            fromacct = self.protocol

        buddypath = profile.logger.pathfor(fromacct, self)

        from gui.pastbrowser import PastBrowser
        PastBrowser.MakeOrShowAndSelect(buddypath)


def fileinfo(filepath):
    'Collect information about a file or directory for sending it.'

    filestats = os.stat(filepath)

    # create a storage with meta information about the file.
    s = Storage(
        size    = os.path.getsize(filepath),
        modtime = filestats[stat.ST_MTIME],
        ctime   = filestats[stat.ST_CTIME],
        name    = os.path.split(filepath)[1],
        path    = path(filepath),
    )

    if os.path.isdir(filepath):
        # directories have all the above information, and
        # files, a list of path objects
        s.type = 'dir'

        s.size = s.numfiles = 0
        s.files = []
        s.path = path(filepath)

        for f in path(filepath).walkfiles():
            s.size  += f.size         # accumulate size,
            s.numfiles += 1           # and number,
            s.files.append(f)    # and a list of names

        info('sending folder with %d files (%d bytes)', s.numfiles, s.size)
    else:
        s.type = 'file'
        s.obj  = open(filepath, 'rb')
        s.numfiles = 1
        s.files = [path(filepath)]

    return s

