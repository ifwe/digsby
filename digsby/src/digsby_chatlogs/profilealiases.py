from digsby_chatlogs.interfaces import IAliasProvider
from peak.util.addons import AddOn
import util.primitives.mapping as mapping
import util.cacheable as cacheable
from util.command_queue import cmdqueue, SerialCommandQueue
from util.primitives.error_handling import traceguard
from util.cacheable import DiskCache
import traceback
import sqlite3
import warnings
import protocols

import logging
log = logging.getLogger('profilealiases')

WHERE_DOUBLE = 'WHERE name=? AND service=?'
WHERE_TRIPLE = WHERE_DOUBLE + ' AND protocol=?'

class ProfileAliasProviderBase(AddOn):
    def __init__(self, subject):
        self.profile = subject
        super(ProfileAliasProviderBase, self).__init__(subject)

    def get_alias(self, name, service, protocol=None):
        mcs = self.profile.blist.metacontacts.forbuddy(mapping.Storage(name = name.lower(), service=service.lower()))
        ret = None
        if len(mcs) == 1: #how to choose if there is more than one metacontact? sorted()[0]?
            ret = list(mcs)[0].alias
        if not ret:
            ret = self.profile.get_contact_info(name.lower() + '_' + service.lower(), 'alias')
        ret = ret or self.find_alias(name, service, protocol)
        return ret

class MemoryProfileAliasProvider(ProfileAliasProviderBase):
    protocols.advise(instancesProvide=(IAliasProvider,))

    @classmethod
    def key_transform(cls, name, service, protocol):
        return (name.lower(), service.lower(), protocol)

    def __init__(self, subject, d=None):
        self.store = dict() if d is None else d
        super(MemoryProfileAliasProvider, self).__init__(subject)

    def set_alias(self, name, service, protocol, alias):
        self.store[self.key_transform(name, service, protocol)] = alias

    def find_alias(self, name, service, protocol):
        return self.store.get(self.key_transform(name, service, protocol))

def alias_cache_validator(obj):
    ret = {}
    if isinstance(obj, dict):
        try:
            for ((name, service, protocol), alias) in obj.iteritems():
                if name != alias:
                    ret[(name, service, protocol)] = alias
        except Exception:
            traceback.print_exc()
    return ret

class YamlProfileAliasProvider(MemoryProfileAliasProvider):
    def __init__(self, subject):
        self.cache = DiskCache('alias_cache_v1.yaml', format='yaml', compression = 'gzip', validator=alias_cache_validator)
        self.store = self.cache.safe_load(dict)
        super(YamlProfileAliasProvider, self).__init__(subject, self.store)

    def set_alias(self, name, service, protocol, alias):
        if alias is None or alias == name:
            return
        if super(YamlProfileAliasProvider, self).find_alias(name, service, protocol) != alias:
            super(YamlProfileAliasProvider, self).set_alias(name, service, protocol, alias)
            self.cache.save(self.store)

class DBProfileAliasProvider(MemoryProfileAliasProvider):

    def __init__(self, subject):
        self.initing = False
        self.cmdq = SerialCommandQueue([self.connect_db, self.integrity_check], [self.shutdown_db])
        super(DBProfileAliasProvider, self).__init__(subject)
        self.corrupted = False
        self.load_db()

    @cmdqueue()
    def load_db(self):
        if self.corrupted or not self.integrity_check():
            log.critical('database was corrupted, short-circuiting load')
            return
        try:
            self.db.execute('CREATE TABLE IF NOT EXISTS profile_aliases (name text, service text, protocol text, alias text, PRIMARY KEY(name, service, protocol))').close()
        except Exception:
            traceback.print_exc()
        else:
            with traceguard:
                self.db.execute('DELETE FROM profile_aliases where name == alias').close()
            with traceguard:
                self.db.execute('VACUUM').close()
            with traceguard:
                self.db.commit()
            r = None
            try:
                r = self.db.execute('SELECT name, service, protocol, alias FROM profile_aliases')
                for (name, service, protocol, alias) in r:
                    self.store[self.key_transform(name, service, protocol)] = alias
            except Exception:
                traceback.print_exc()
            finally:
                if r is not None:
                    r.close()

    def integrity_check(self, tries=0):
        if tries > 5:
            log.critical('database cannot be fixed, flagging as corrupted')
            self.corrupted = True
            return False
        try:
            r = self.db.execute('PRAGMA integrity_check;')
            r = list(r)
            if r != [(u'ok',)]:
                self.on_corrupt_db()
                return self.integrity_check(tries = tries+1)
        except Exception:
            self.on_corrupt_db()
            return self.integrity_check(tries = tries+1)
        else:
            return True

    def db_file(self):
        return cacheable.get_cache_root(user=True) / 'alias_cache_v1.db'

    def on_corrupt_db(self):
        self.shutdown_db()
        with traceguard:
            self.db_file().remove()
        try:
            self.connect_db()
        except Exception:
            log.critical('database could not be connected, flagging as corrupted')
            self.corrupted = True

    def connect_db(self):
        if self.corrupted:
            return
        self.db = sqlite3.connect(self.db_file())

    def shutdown_db(self):
        with traceguard:
            self.db.commit()
        with traceguard:
            self.db.close()
        try:
            del self.db
        except AttributeError:
            pass

    def need_set(self, name, service, protocol, alias):
        if self.corrupted:
            return False
        #validate other values?
        if alias is not None and not isinstance(alias, unicode):
            if protocol not in ('aim', 'icq', 'msim', 'fbchat', 'msn'): #this may not be desirable, but oscar usually has bytes here.
                warnings.warn('%r, %r, %r has non-unicode alias: %r' % (name, service, protocol, alias))
            try:
                alias = alias.decode('fuzzy utf-8')
            except Exception:
                traceback.print_exc()
                return False
        name, service, protocol = self.key_transform(name, service, protocol)
        if super(DBProfileAliasProvider, self).find_alias(name, service, protocol) != alias:
            return True

    def set_alias(self, name, service, protocol, alias):
        if self.need_set(name, service, protocol, alias):
            self._set_alias(name, service, protocol, alias)

    @cmdqueue()
    def _set_alias(self, name, service, protocol, alias):
        if self.need_set(name, service, protocol, alias):
            if not alias or name == alias:
                with traceguard:
                    self.db.execute('DELETE FROM profile_aliases ' + WHERE_TRIPLE, (name, service, protocol)).close()
            else:
                with traceguard:
                    self.db.execute('INSERT OR REPLACE INTO profile_aliases VALUES (?,?,?,?)', (name, service, protocol, alias)).close()
            super(DBProfileAliasProvider, self).set_alias(name, service, protocol, alias)

    def find_alias(self, name, service, protocol):
        name, service, protocol = self.key_transform(name, service, protocol)
        try:
            return self.store[(name, service, protocol)]
        except KeyError:
            db = None
            with traceguard:
                db = sqlite3.connect(self.db_file())
                for query, args in [
                                    ('SELECT alias FROM profile_aliases ' + WHERE_TRIPLE, (name, service, protocol)),
                                    ('SELECT alias FROM profile_aliases ' + WHERE_DOUBLE, (name, service))
                                    ]:
                    r = db.execute(query, args)
                    try:
                        for row in r:
                            alias = row[0]
                            if alias:
                                super(DBProfileAliasProvider, self).set_alias(name, service, protocol, alias)
                                return alias
                    finally:
                        r.close()
            if db is not None:
                db.close()
        alias = None #we didn't find one.  cache that knowledge.
        super(DBProfileAliasProvider, self).set_alias(name, service, protocol, alias)

ProfileAliasProvider = DBProfileAliasProvider
