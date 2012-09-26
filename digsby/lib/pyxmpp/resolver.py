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

"""DNS resolever with SRV record support.

Normative reference:
  - `RFC 1035 <http://www.ietf.org/rfc/rfc1035.txt>`__
  - `RFC 2782 <http://www.ietf.org/rfc/rfc2782.txt>`__
"""

__revision__="$Id: resolver.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import re
import socket
import dns.resolver
import dns.name
import dns.exception
import random
from encodings import idna

service_aliases={"xmpp-server": ("jabber-server","jabber")}
ip_re=re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

def shuffle_srv(records):
    """Randomly reorder SRV records using their weights.

    :Parameters:
        - `records`: SRV records to shuffle.
    :Types:
        - `records`: sequence of `dns.rdtypes.IN.SRV`

    :return: reordered records.
    :returntype: `list` of `dns.rdtypes.IN.SRV`"""
    if not records:
        return []
    ret=[]
    while len(records)>1:
        weight_sum=0
        for rr in records:
            weight_sum+=rr.weight+0.1
        thres=random.random()*weight_sum
        weight_sum=0
        for rr in records:
            weight_sum+=rr.weight+0.1
            if thres<weight_sum:
                records.remove(rr)
                ret.append(rr)
                break
    ret.append(records[0])
    return ret

def reorder_srv(records):
    """Reorder SRV records using their priorities and weights.

    :Parameters:
        - `records`: SRV records to shuffle.
    :Types:
        - `records`: `list` of `dns.rdtypes.IN.SRV`

    :return: reordered records.
    :returntype: `list` of `dns.rdtypes.IN.SRV`"""
    records=list(records)
    records.sort()
    ret=[]
    tmp=[]
    for rr in records:
        if not tmp or rr.priority==tmp[0].priority:
            tmp.append(rr)
            continue
        ret+=shuffle_srv(tmp)
    if tmp:
        ret+=shuffle_srv(tmp)
    return ret

def resolve_srv(domain,service,proto="tcp"):
    """Resolve service domain to server name and port number using SRV records.

    A built-in service alias table will be used to lookup also some obsolete
    record names.

    :Parameters:
        - `domain`: domain name.
        - `service`: service name.
        - `proto`: protocol name.
    :Types:
        - `domain`: `unicode` or `str`
        - `service`: `unicode` or `str`
        - `proto`: `str`

    :return: host names and port numbers for the service or None.
    :returntype: `list` of (`str`,`int`)"""
    names_to_try=[u"_%s._%s.%s" % (service,proto,domain)]
    if service_aliases.has_key(service):
        for a in service_aliases[service]:
            names_to_try.append(u"_%s._%s.%s" % (a,proto,domain))
    for name in names_to_try:
        name=idna.ToASCII(name)
        try:
            r=dns.resolver.query(name, 'SRV')
        except dns.exception.DNSException:
            continue
        if not r:
            continue
        return [(rr.target.to_text(),rr.port) for rr in reorder_srv(r)]
    return None

def getaddrinfo(host,port,family=0,socktype=socket.SOCK_STREAM,proto=0,allow_cname=True):
    """Resolve host and port into addrinfo struct.

    Does the same thing as socket.getaddrinfo, but using `pyxmpp.resolver`. This
    makes it possible to reuse data (A records from the additional section of
    DNS reply) returned with SRV records lookup done using this module.

    :Parameters:
        - `host`: service domain name.
        - `port`: service port number or name.
        - `family`: address family.
        - `socktype`: socket type.
        - `proto`: protocol number or name.
        - `allow_cname`: when False CNAME responses are not allowed.
    :Types:
        - `host`: `unicode` or `str`
        - `port`: `int` or `str`
        - `family`: `int`
        - `socktype`: `int`
        - `proto`: `int` or `str`
        - `allow_cname`: `bool`

    :return: list of (family, socktype, proto, canonname, sockaddr).
    :returntype: `list` of (`int`, `int`, `int`, `str`, (`str`, `int`))"""
    ret=[]
    if proto==0:
        proto=socket.getprotobyname("tcp")
    elif type(proto)!=int:
        proto=socket.getprotobyname(proto)
    if type(port)!=int:
        port=socket.getservbyname(port,proto)
    if family not in (0,socket.AF_INET):
        raise NotImplementedError,"Protocol family other than AF_INET not supported, yet"
    if ip_re.match(host):
        return [(socket.AF_INET,socktype,proto,host,(host,port))]
    host=idna.ToASCII(host)
    try:
        r=dns.resolver.query(host, 'A')
    except dns.exception.DNSException:
        r=dns.resolver.query(host+".", 'A')
    if not allow_cname and r.rrset.name!=dns.name.from_text(host):
        raise ValueError,"Unexpected CNAME record found for %s" % (host,)
    if r:
        for rr in r:
            ret.append((socket.AF_INET,socktype,proto,r.rrset.name,(rr.to_text(),port)))
    return ret

# vi: sts=4 et sw=4
