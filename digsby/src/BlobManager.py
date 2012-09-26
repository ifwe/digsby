'''
BlobManager's purpose is to allow the profile to save blobs without requiring
a connection to the Digsby servers.  This is for cases such a temporary network
outage.  The manager requests updates from the server when the profile logs in
and then solves the synchronization of them once retrieved.  The resulting
behavior is that blobs are pushed to the server when possible, and overridden
with the server's copy if changes have been made there since the last
synchronization.
'''
from __future__ import with_statement
from util.callbacks import callsback
from util.primitives.funcs import Delegate

from logging import getLogger; log = getLogger('BlobManager')
from digsby.blobs import name_to_obj
from hashlib import md5
from util.primitives import Storage
import syck
import util
import struct
import traceback
import hooks
import prefs
print_exc = traceback.print_exc
info = log.info; warning = log.warning

import os, wx
from os.path import join as pathjoin, exists as pathexists
from struct import pack, unpack
from digsby.blobs import name_to_ns, ns_to_name, ns_to_obj
from util.observe import Observable

class BlobManager(Observable):
    CACHE_FOLDER = 'digsbyblobs'

    blob_names = list(name_to_ns.keys())

    def __init__(self, profile):
        Observable.__init__(self)
        self.profile = profile
        self.profile.add_observer(self.profile_state_changed, 'state')
        self.waiting_blobs = set(self.blob_names[:])
        self.from_cache = {}
        self.blobhashes = {}

    @callsback
    def server_retrieve(self, blobtype, tstamp, callback=None):
        '''
        attempts to get a blob from the server.
        not yet sure what to do if this fails.
        '''
        tstamp = str(int(tstamp))
        try:
            info('retrieving blob "%s"', blobtype)
            self.profile.connection.get_blob_raw(blobtype, tstamp, callback=callback)
        except Exception, e:
            raise

    def profile_state_changed(self, src, attr, old, new):
        '''
        notify target.
        used to initiate retrieval of blobs from the server
        when the profile goes online
        '''
        assert src == self.profile
        assert attr == 'state'
        from digsby import protocol as digsby_protocol

        if new == digsby_protocol.Statuses.SYNC_PREFS:
            self.profile.defaultprefs = prefs.defaultprefs()
            for blob in self.blob_names:
                b = self.blob_load_cache(blob)
                self.from_cache[blob] = b._data
                self.server_retrieve(blob, str(b.tstamp),
                                     success=self.retrieved_blob,
                                     error=self.blob_failed,
                                     timeout=lambda blob=blob: self.blob_timed_out(blob))

    @property
    def loading(self):
        'True when not all blobs have come back (initialized) from the server'
        return bool(self.waiting_blobs)

    def blob_timed_out(self, name):
        self.profile.blob_failed(name)

    def blob_failed(self, stanza):
        ns = stanza.get_query_ns()
        name = ns_to_name[ns]
        self.profile.blob_failed(name)

    def retrieved_blob(self, stanza):
        '''
        The answer from server_retrieve.
        Sends blob to the profile, either from the (in memory, pre-loaded) cache,
        or from the response from the server.  If the local copy was newer,
        this initiates a profile.save for the blob, after sending it to the profile.
        '''
        ns = stanza.get_query_ns()
        info('retrieved blob w/ ns:"%r"', ns)
        blob = ns_to_obj[ns](stanza.get_query())
        name = ns_to_name[ns]
        calls = Delegate()
        if blob.update_needed is True:
            assert blob._data is None
            info('%s: server-side older, sending our copy', name)
            calls.append(lambda: self.profile.save(name, force = True))
        if blob._data is None:
            info('%s: server-side matched cache', name)
            blob._data = self.from_cache.pop(name) #default?
        else:
            info('%s: server-side newer', name)
            self.blob_cache(blob)

        useful_data = blob.data
        old_loading = self.loading
        self.waiting_blobs.discard(name)
        self.profile.update_blob(name, useful_data)
        self.notify('loading', old_loading, self.loading)
        calls()

    def load_from_identity(self, identity = None):
        self.profile.defaultprefs = prefs.defaultprefs()
        for blob_name in self.blob_names:
            try:
                useful_data = identity.load_data(blob_name)
            except Exception:
                useful_data = None
            if useful_data is None:
                useful_data = name_to_obj[blob_name]('0', rawdata=None).data
            blob = name_to_obj[blob_name](data=useful_data)
            useful_data = blob.data
            del blob
            self.waiting_blobs.discard(blob_name)
            self.profile.update_blob(blob_name, useful_data)

    def local_load(self):
        self.profile.defaultprefs = prefs.defaultprefs()
        for name in self.blob_names:
            b = self.blob_load_cache(name)
            useful_data = b.data
            self.waiting_blobs.discard(name)
            self.profile.update_blob(name, useful_data)

    def get_cache_path(self):
        '''
        Net data that goes to and from the server is cached locally at the
        following location.
        '''
        un = self.profile.username
        import util.cacheable as cache

        cache_path = cache.get_cache_root(user = True) / self.CACHE_FOLDER

        # Make the cache directory if it doesn't exist.
        try:
            if not pathexists(cache_path):
                os.makedirs(cache_path)
        except Exception, e:
            log.critical('exception during makedirs: %r', e)

        return cache_path

    def blob_load_cache(self, elem_name):
        '''
        retrieves a 'cached' blob from load_cache.  Then stores the
        timestamp, the blob hash, and whether or not the blob's timestamp has
        been overridden (+=1) since it was last loaded (False here).
        '''
        blob = self.load_cache(elem_name)
        self.blobhashes[elem_name] = (blob.tstamp, self.calc_blob_hash(blob), False)
        return blob

    def load_cache(self, name):
        '''
        attempts to read a blob from the harddrive.
        Failure results in a blob whose _data is None with a timestamp of 0.
        '''
        cache_file = pathjoin(self.get_cache_path(), name)

        try:
            with open(cache_file, 'rb') as f:
                plen   = unpack('!H', f.read(2))[0]
                tstamp = str(int(f.read(plen)))
                data   = f.read()
        except IOError, e:
            log.critical('IO error while reading %r: %r', cache_file, e)
            tstamp = '0'
            data = None
        except Exception, e:
            traceback.print_exc()
            log.error("couldn't load %r: %r", cache_file, e)
            tstamp = '0'
            data = None

        log.info('loaded cache: %s...tstamp is %s', name, tstamp)
        try:
            b = name_to_obj[name](tstamp, rawdata=data)
            b.data
        except Exception, e:
            log.warning('trouble loading blob %s: returning blank blob. error was %r', name, e)
            b = name_to_obj[name]('0', rawdata=None)
            traceback.print_exc()
        return b

    @callsback
    def set_blob(self, elem_name, data, force = False, callback = None):
        '''
        Decide to send a blob to the server, or not.
        Run caching routine before doing so.
        response goes to self.set_blob_success
        '''
        try:
            hooks.notify('digsby.identity.save_data', elem_name, data)
        except Exception:
            callback.error()
        else:
            callback.success()
        finally:
            return
        blob = name_to_obj[elem_name](data=data)

        stored = self.blobhashes.get(elem_name, sentinel)
        if stored is not sentinel:
            stored1 = stored[1]
        else:
            stored1 = sentinel

        if stored1 == self.calc_blob_hash(blob) and not force:
            log.info('set_blob %s: no change', elem_name)
            return callback.success()

        #cache here
        sending_stamp = blob.tstamp
        try:
            int(sending_stamp)
        except Exception, e:
            if stored is not sentinel:
                blob.tstamp = stored[0]
            else:
                blob.tstamp = 0
        self.blob_cache(blob, ts_override=True)
        blob.tstamp = sending_stamp
        del sending_stamp
        # send blob out to network.

        try:
            iq = blob.make_push(self.profile.connection)

            log.info('%s: changed, sending stanza %r', elem_name, iq)
            self.profile.connection.send_cb(iq, success = lambda s: self.set_blob_success(s, blob._data, callback = callback),
                             error   = callback.error,
                             timeout = callback.timeout)
        except Exception, e:
            log.critical('failed sending %s to server:', elem_name)
            print_exc()
            callback.error()

    def blob_set(self, stanza):
        '''
        respond to blob pushes from the server.
        cache it to disk, and send it to the profile.
        '''
        ns = stanza.get_query_ns()
        info('blob set %s', ns)
        blob = ns_to_obj[ns](stanza.get_query())
        self.blob_cache(blob)
        self.incoming_blob(blob)

    def incoming_blob(self, blob):
        '''
        send a blob push to the profile.
        This function only extracts the data and name from the jabber object
        and sends it to the profile in the format it is expecting.
        '''
        useful_data = blob.data
        name = ns_to_name[blob.xml_element_namespace]
        self.profile.update_blob(name, useful_data)

    @callsback
    def set_blob_success(self, stanza, data, callback = None):
        '''
        upon a successful send to the server,
        re-cache the data with the new timestamp.
        '''
        ns   = stanza.get_query_ns()
        name = ns_to_name[ns]

        #get timestamp and reset on harddrive here.

        blob = ns_to_obj[ns](stanza.get_query())
        blob._data = data

        self.blob_cache(blob)
        callback.success()

    def _save_cache(self, blob, ts_override=False):
        '''
        write a blob to the hard drive.  If bool(ts_override) is True,
        will increase the timestamp written by 1, if this has not already been
        recorded as having happened at index 2 ([2]) of the entry in
        self.blobhashes
        '''
        name = type(blob).__name__.lower()
        if ts_override:
            stored = self.blobhashes.get('name', sentinel)
            if stored is sentinel or not stored[2]:
                blob.tstamp = str(int(blob.tstamp)+1)
        tstamp = blob.tstamp
        data = blob._data
        cache_path = self.get_cache_path()

        info('caching: %s', name)
        with open(pathjoin(cache_path, name), 'wb') as f:
            f.write(pack('!H', len(str(tstamp))) + str(tstamp)) # pstring of timestamp

            f.write(data)           # gzip(pickled(data))
        return name

    def blob_cache(self, ablob, ts_override=False):
        '''
        decide whether or not to write a blob to disk, then do so (or not).
        '''
        digest = self.calc_blob_hash(ablob)
        name = ns_to_name[ablob.xml_element_namespace]
        stored = self.blobhashes.get('name', sentinel)
        if stored is not sentinel:
            stored = stored[1]
        if stored != digest:
            try:
                cachedname = self._save_cache(ablob, ts_override=ts_override)
                if name != cachedname:
                    raise AssertionError
            except Exception:
                traceback.print_exc()
                info('failed to cache blob %s with digest %s, tstamp %s', name, digest, ablob.tstamp)
            else:
                self.blobhashes[name] = (ablob.tstamp, digest, ts_override)
                info('cached blob %s with digest %s, tstamp %s', name, digest, ablob.tstamp)
        else:
            info('digests matched, did not cache %s', name)

    def calc_blob_hash(self, blob):
        '''
        md5 blob._data, None if _data was None
        '''
        return md5(blob._data).hexdigest() if blob._data is not None else None

