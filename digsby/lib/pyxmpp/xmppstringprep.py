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
# pylint treats "import stringprep" like depreciated "import string"
# pylint: disable-msg=W0402

"""Nodeprep and resourceprep stringprep profiles.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: xmppstringprep.py,v 1.16 2004/10/07 22:28:04 jajcus Exp $"
__docformat__="restructuredtext en"

import stringprep
import unicodedata
from pyxmpp.exceptions import StringprepError

class LookupFunction:
    """Class for looking up RFC 3454 tables using function.

    :Ivariables:
        - `lookup`: the lookup function."""
    def __init__(self,function):
        """Initialize `LookupFunction` object.

        :Parameters:
            - `function`: function taking character code as input and returning
              `bool` value or the mapped for `code`."""
        self.lookup=function

class LookupTable:
    """Class for looking up RFC 3454 tables using a dictionary and/or list of ranges."""
    def __init__(self,singles,ranges):
        """Initialize `LookupTable` object.

        :Parameters:
            - `singles`: dictionary mapping Unicode characters into other Unicode characters.
            - `ranges`: list of ``((start,end),value)`` tuples mapping codes in range (start,end)
              to the value."""
        self.singles=singles
        self.ranges=ranges

    def lookup(self,c):
        """Do Unicode character lookup.

        :Parameters:
            - `c`: Unicode character to look up.

        :return: the mapped value."""
        if self.singles.has_key(c):
            return self.singles[c]
        c=ord(c)
        for (start,end),value in self.ranges:
            if c<start:
                return None
            if c<=end:
                return value
        return None

A_1=LookupFunction(stringprep.in_table_a1)

def b1_mapping(uc):
    """Do RFC 3454 B.1 table mapping.

    :Parameters:
        - `uc`: Unicode character to map.

    :returns: u"" if there is `uc` code in the table, `None` otherwise."""
    if stringprep.in_table_b1(uc):
        return u""
    else:
        return None

B_1=LookupFunction(b1_mapping)
B_2=LookupFunction(stringprep.map_table_b2)
B_3=LookupFunction(stringprep.map_table_b3)
C_1_1=LookupFunction(stringprep.in_table_c11)
C_1_2=LookupFunction(stringprep.in_table_c12)
C_2_1=LookupFunction(stringprep.in_table_c21)
C_2_2=LookupFunction(stringprep.in_table_c22)
C_3=LookupFunction(stringprep.in_table_c3)
C_4=LookupFunction(stringprep.in_table_c4)
C_5=LookupFunction(stringprep.in_table_c5)
C_6=LookupFunction(stringprep.in_table_c6)
C_7=LookupFunction(stringprep.in_table_c7)
C_8=LookupFunction(stringprep.in_table_c8)
C_9=LookupFunction(stringprep.in_table_c9)
D_1=LookupFunction(stringprep.in_table_d1)
D_2=LookupFunction(stringprep.in_table_d2)

def nfkc(data):
    """Do NFKC normalization of Unicode data.

    :Parameters:
        - `data`: list of Unicode characters or Unicode string.

    :return: normalized Unicode string."""
    if type(data) is list:
        data=u"".join(data)
    return unicodedata.normalize("NFKC",data)

class Profile:
    """Base class for stringprep profiles."""
    cache_items=[]
    def __init__(self,unassigned,mapping,normalization,prohibited,bidi=1):
        """Initialize Profile object.

        :Parameters:
            - `unassigned`: the lookup table with unassigned codes
            - `mapping`: the lookup table with character mappings
            - `normalization`: the normalization function
            - `prohibited`: the lookup table with prohibited characters
            - `bidi`: if True then bidirectional checks should be done
        """
        self.unassigned=unassigned
        self.mapping=mapping
        self.normalization=normalization
        self.prohibited=prohibited
        self.bidi=bidi
        self.cache={}

    def prepare(self,data):
        """Complete string preparation procedure for 'stored' strings.
        (includes checks for unassigned codes)

        :Parameters:
            - `data`: Unicode string to prepare.

        :return: prepared string

        :raise StringprepError: if the preparation fails
        """
        r=self.cache.get(data)
        if r is not None:
            return r
        s=self.map(data)
        if self.normalization:
            s=self.normalization(s)
        s=self.prohibit(s)
        s=self.check_unassigned(s)
        if self.bidi:
            s=self.check_bidi(s)
        if type(s) is list:
            s=u"".string.join()
        if len(self.cache_items)>=stringprep_cache_size:
            remove=self.cache_items[:-stringprep_cache_size/2]
            for profile,key in remove:
                try:
                    del profile.cache[key]
                except KeyError:
                    pass
            self.cache_items[:]=self.cache_items[-stringprep_cache_size/2:]
        self.cache_items.append((self,data))
        self.cache[data]=s
        return s

    def prepare_query(self,s):
        """Complete string preparation procedure for 'query' strings.
        (without checks for unassigned codes)

        :Parameters:
            - `s`: Unicode string to prepare.

        :return: prepared string

        :raise StringprepError: if the preparation fails
        """

        s=self.map(s)
        if self.normalization:
            s=self.normalization(s)
        s=self.prohibit(s)
        if self.bidi:
            s=self.check_bidi(s)
        if type(s) is list:
            s=u"".string.join(s)
        return s

    def map(self,s):
        """Mapping part of string preparation."""
        r=[]
        for c in s:
            rc=None
            for t in self.mapping:
                rc=t.lookup(c)
                if rc is not None:
                    break
            if rc is not None:
                r.append(rc)
            else:
                r.append(c)
        return r

    def prohibit(self,s):
        """Checks for prohibited characters."""
        for c in s:
            for t in self.prohibited:
                if t.lookup(c):
                    raise StringprepError,"Prohibited character: %r" % (c,)
        return s

    def check_unassigned(self,s):
        """Checks for unassigned character codes."""
        for c in s:
            for t in self.unassigned:
                if t.lookup(c):
                    raise StringprepError,"Unassigned character: %r" % (c,)
        return s

    def check_bidi(self,s):
        """Checks if sting is valid for bidirectional printing."""
        has_l=0
        has_ral=0
        for c in s:
            if D_1.lookup(c):
                has_ral=1
            elif D_2.lookup(c):
                has_l=1
        if has_l and has_ral:
            raise StringprepError,"Both RandALCat and LCat characters present"
        if has_l and (D_1.lookup(s[0]) is None or D_1.lookup(s[-1]) is None):
            raise StringprepError,"The first and the last character must be RandALCat"
        return s

nodeprep=Profile(
    unassigned=(A_1,),
    mapping=(B_1,B_2),
    normalization=nfkc,
    prohibited=(C_1_1,C_1_2,C_2_1,C_2_2,C_3,C_4,C_5,C_6,C_7,C_8,C_9,
            LookupTable({u'"':True,u'&':True,u"'":True,u"/":True,
                    u":":True,u"<":True,u">":True,u"@":True},()) ),
    bidi=1)

resourceprep=Profile(
    unassigned=(A_1,),
    mapping=(B_1,),
    normalization=nfkc,
    prohibited=(C_1_2,C_2_1,C_2_2,C_3,C_4,C_5,C_6,C_7,C_8,C_9),
    bidi=1)

stringprep_cache_size=1000
def set_stringprep_cache_size(size):
    """Modify stringprep cache size.

    :Parameters:
        - `size`: new cache size"""
    global stringprep_cache_size
    stringprep_cache_size=size
    if len(Profile.cache_items)>size:
        remove=Profile.cache_items[:-size]
        for profile,key in remove:
            try:
                del profile.cache[key]
            except KeyError:
                pass
        Profile.cache_items=Profile.cache_items[-size:]

# vi: sts=4 et sw=4
