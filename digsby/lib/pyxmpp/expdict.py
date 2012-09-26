#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

"""Dictionary with item expiration."""

__revision__="$Id: expdict.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import time
import threading

__all__ = ['ExpiringDictionary']

sentinel = object()

class ExpiringDictionary(dict):
    """An extension to standard Python dictionary objects which implements item
    expiration.

    Each item in ExpiringDictionary has its expiration time assigned, after
    which the item is removed from the mapping.

    :Ivariables:
        - `_timeouts`: a dictionary with timeout values and timeout callback for
          stored objects.
        - `_default_timeout`: the default timeout value (in seconds from now).
        - `_lock`: access synchronization lock.
    :Types:
        - `_timeouts`: `dict`
        - `_default_timeout`: `int`
        - `_lock`: `threading.RLock`"""

    __slots__=['_timeouts','_default_timeout','_lock']

    def __init__(self,default_timeout=300):
        """Initialize an `ExpiringDictionary` object.

        :Parameters:
            - `default_timeout`: default timeout value for stored objects.
        :Types:
            - `default_timeout`: `int`"""
        dict.__init__(self)
        self._timeouts={}
        self._default_timeout=default_timeout
        self._lock=threading.RLock()

    def __delitem__(self,key):
        self._lock.acquire()
        try:
            del self._timeouts[key]
            return dict.__delitem__(self,key)
        finally:
            self._lock.release()

    def __getitem__(self,key):
        self._lock.acquire()
        try:
            self._expire_item(key)
            return dict.__getitem__(self,key)
        finally:
            self._lock.release()

    def pop(self,key,default=sentinel):
        self._lock.acquire()
        try:
            self._expire_item(key)
            del self._timeouts[key]
            if default is not sentinel:
                return dict.pop(self,key,default)
            else:
                return dict.pop(self,key)
        finally:
            self._lock.release()

    def __setitem__(self,key,value):
        return self.set_item(key,value)

    def set_item(self,key,value,timeout=None,timeout_callback=None):
        """Set item of the dictionary.

        :Parameters:
            - `key`: the key.
            - `value`: the object to store.
            - `timeout`: timeout value for the object (in seconds from now).
            - `timeout_callback`: function to be called when the item expires.
              The callback should accept none, one (the key) or two (the key
              and the value) arguments.
        :Types:
            - `key`: any hashable value
            - `value`: any python object
            - `timeout`: `int`
            - `timeout_callback`: callable"""
        self._lock.acquire()
        try:
            if not timeout:
                timeout=self._default_timeout
            self._timeouts[key]=(time.time()+timeout,timeout_callback)
            return dict.__setitem__(self,key,value)
        finally:
            self._lock.release()

    def expire(self):
        """Do the expiration of dictionary items.

        Remove items that expired by now from the dictionary."""
        self._lock.acquire()
        try:
            for k in self._timeouts.keys():
                self._expire_item(k)
        finally:
            self._lock.release()

    def _expire_item(self,key):
        """Do the expiration of a dictionary item.

        Remove the item if it has expired by now.

        :Parameters:
            - `key`: key to the object.
        :Types:
            - `key`: any hashable value"""
        (timeout,callback)=self._timeouts[key]
        if timeout<=time.time():
            item = dict.pop(self, key)
            del self._timeouts[key]
            if callback:
                try:
                    callback(key,item)
                except TypeError:
                    try:
                        callback(key)
                    except TypeError:
                        callback()

# vi: sts=4 et sw=4
