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

"""Utility functions for the pyxmpp package."""

__revision__="$Id: utils.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import sys

if sys.hexversion<0x02030000:
    raise ImportError,"Python 2.3 or newer is required"

import time
import datetime

def to_utf8(s):
    """
    Convevert `s` to UTF-8 if it is Unicode, leave unchanged
    if it is string or None and convert to string overwise
    """
    if s is None:
        return None
    elif type(s) is unicode:
        return s.encode("utf-8")
    elif type(s) is str:
        return s
    else:
        return unicode(s).encode("utf-8")

def from_utf8(s):
    """
    Convert `s` to Unicode or leave unchanged if it is None.

    Regular strings are assumed to be UTF-8 encoded
    """
    if s is None:
        return None
    elif type(s) is unicode:
        return s
    elif type(s) is str:
        return unicode(s,"utf-8")
    else:
        return unicode(s)

minute=datetime.timedelta(minutes=1)
nulldelta=datetime.timedelta()

def datetime_utc_to_local(utc):
    """
    An ugly hack to convert naive `datetime.datetime` object containing
    UTC time to a naive `datetime.datetime` object with local time.
    It seems standard Python 2.3 library doesn't provide any better way to
    do that.
    """
    ts=time.time()
    cur=datetime.datetime.fromtimestamp(ts)
    cur_utc=datetime.datetime.utcfromtimestamp(ts)

    offset=cur-cur_utc
    t=utc

    d=datetime.timedelta(hours=2)
    while d>minute:
        local=t+offset
        tm=local.timetuple()
        tm=tm[0:8]+(0,)
        ts=time.mktime(tm)
        u=datetime.datetime.utcfromtimestamp(ts)
        diff=u-utc
        if diff<minute and diff>-minute:
            break
        if diff>nulldelta:
            offset-=d
        else:
            offset+=d
        d/=2
    return local

def datetime_local_to_utc(local):
    """
    Simple function to convert naive `datetime.datetime` object containing
    local time to a naive `datetime.datetime` object with UTC time.
    """
    ts=time.mktime(local.timetuple())
    return datetime.datetime.utcfromtimestamp(ts)

# vi: sts=4 et sw=4
