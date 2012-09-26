#
# (C) Copyright 2006 Jacek Konieczny <jajcus@jajcus.net>
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

"""Interface API, minimal implementation.

This is minimal Zope Interfaces API implementation, as required by PyXMPP, not add another dependencies.

If zope.interface package is available it will be used instead of this one. Never import this module directly."""

__revision__="$Id: utils.py 647 2006-08-26 18:27:39Z jajcus $"
__docformat__="restructuredtext en"

import sys
from types import FunctionType

def classImplements(cls, *interfaces):
    if not isinstance(cls, classobj):
        raise TypeError, "%r is not a class"
    for interface in interfaces:
        if not isinstance(interface, InterfaceClass):
            raise TypeError, "Only interfaces may be implemented"
    cls.__implemented__ = tuple(interfaces)

def implements(*interfaces):
    for interface in interfaces:
        if not isinstance(interface, InterfaceClass):
            raise TypeError, "Only interfaces may be implemented"

    frame = sys._getframe(1)
    locals = frame.f_locals

    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError, "implements() may only be used in a class definition"

    if "__implemented__" in locals:
        raise TypeError, "implements() may be used only once"

    locals["__implemented__"] = tuple(interfaces)

def _whole_tree(cls):
    yield cls
    for base in cls.__bases__:
        for b in _whole_tree(base):
            yield b

def implementedBy(cls):
    try:
        for interface in cls.__implemented__:
            for c in _whole_tree(interface):
                yield c
    except AttributeError:
        pass
    for base in cls.__bases__:
        for interface in implementedBy(base):
            yield interface

def providedBy(ob):
    try:
        for interface in ob.__provides__:
            yield interface
    except AttributeError:
        try:
            for interface in implementedBy(ob.__class__):
                yield interface
        except AttributeError:
            return

class InterfaceClass(object):
    def __init__(self, name, bases = (), attrs = None, __doc__ = None, __module__ = None):
        if __module__ is None:
            if (attrs is not None and ('__module__' in attrs) and isinstance(attrs['__module__'], str)):
                __module__ = attrs['__module__']
                del attrs['__module__']
            else:
                __module__ = sys._getframe(1).f_globals['__name__']
        if __doc__ is not None:
            self.__doc__ = __doc__
        if attrs is not None and "__doc__" in attrs:
            del attrs["__doc__"]
        self.__module__ = __module__
        for base in bases:
            if not isinstance(base, InterfaceClass):
                raise TypeError, 'Interface bases must be Interfaces'
        if attrs is not None:
            for aname, attr in attrs.items():
                if not isinstance(attr, Attribute) and type(attr) is not FunctionType:
                    raise TypeError, 'Interface attributes must be Attributes o functions (%r found in %s)' % (attr, aname)
        self.__bases__ = bases
        self.__attrs = attrs
        self.__name__ = name
        self.__identifier__ = "%s.%s" % (self.__module__, self.__name__)
        
    def providedBy(self, ob):
        """Is the interface implemented by an object"""
        if self in providedBy(ob):
            return True
        return False

    def implementedBy(self, cls):
        """Do instances of the given class implement the interface?"""
        return self in implementedBy(cls)

    def __repr__(self):
        name = self.__name__
        module = self.__module__
        if module and module != "__main__":
            name = "%s.%s" % (module, name)
        return "<%s %s>" % (self.__class__.__name__, name)

class Attribute(object):
    def __init__(self, doc):
        self.__doc__ = doc

Interface = InterfaceClass("Interface", __module__ = "pyxmpp.inteface_micro_impl")

# vi: sts=4 et sw=4
