#! /usr/bin/env python
#
"""
"""
# Original code Copyright (C) 2006 Tomer Filliba
# Modifications Copyright (C) 2012 GC3, University of Zurich
#
# Original source code was took from
#   http://code.activestate.com/recipes/496741-object-proxying/
#
# This software is released under PSF license.
#
# PSF LICENSE AGREEMENT FOR PYTHON 2.7.3
#
# This LICENSE AGREEMENT is between the Python Software Foundation
# ("PSF"), and the Individual or Organization ("Licensee") accessing
# and otherwise using Python 2.7.3 software in source or binary form
# and its associated documentation.
#
# Subject to the terms and conditions of this License Agreement, PSF
# hereby grants Licensee a nonexclusive, royalty-free, world-wide
# license to reproduce, analyze, test, perform and/or display
# publicly, prepare derivative works, distribute, and otherwise use
# Python 2.7.3 alone or in any derivative version, provided, however,
# that PSF's License Agreement and PSF's notice of copyright, i.e.,
# "Copyright (c) 2001-2012 Python Software Foundation; All Rights
# Reserved" are retained in Python 2.7.3 alone or in any derivative
# version prepared by Licensee.
#
# In the event Licensee prepares a derivative work that is based on or
# incorporates Python 2.7.3 or any part thereof, and wants to make the
# derivative work available to others as provided herein, then
# Licensee hereby agrees to include in any such work a brief summary
# of the changes made to Python 2.7.3.
#
# PSF is making Python 2.7.3 available to Licensee on an "AS IS"
# basis. PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
# IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
# DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR
# FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON 2.7.3
# WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.
#
# PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
# 2.7.3 FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS
# AS A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON
# 2.7.3, OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY
# THEREOF.
#
# This License Agreement will automatically terminate upon a material
# breach of its terms and conditions.
#
# Nothing in this License Agreement shall be deemed to create any
# relationship of agency, partnership, or joint venture between PSF
# and Licensee. This License Agreement does not grant permission to
# use PSF trademarks or trade name in a trademark sense to endorse or
# promote products or services of Licensee, or any third party.
#
# By copying, installing or otherwise using Python 2.7.3, Licensee
# agrees to be bound by the terms and conditions of this License
# Agreement.


__docformat__ = 'reStructuredText'
__version__ = '$Revision$'


class ACProxy(object):
    __slots__ = ["_obj", "__weakref__"]
    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)
    
    #
    # proxying (special cases)
    #
    def __getattribute__(self, name):
        return getattr(object.__getattribute__(self, "_obj"), name)
    def __delattr__(self, name):
        delattr(object.__getattribute__(self, "_obj"), name)
    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_obj"), name, value)
    
    def __nonzero__(self):
        return bool(object.__getattribute__(self, "_obj"))
    def __str__(self):
        return str(object.__getattribute__(self, "_obj"))
    def __repr__(self):
        return repr(object.__getattribute__(self, "_obj"))
    
    #
    # factories
    #
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__', 
        '__contains__', '__delitem__', '__delslice__', '__div__', '__divmod__', 
        '__eq__', '__float__', '__floordiv__', '__ge__', '__getitem__', 
        '__getslice__', '__gt__', '__hash__', '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__', '__imod__', 
        '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__', 
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__', 
        '__long__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__', 
        '__neg__', '__oct__', '__or__', '__pos__', '__pow__', '__radd__', 
        '__rand__', '__rdiv__', '__rdivmod__', '__reduce__', '__reduce_ex__', 
        '__repr__', '__reversed__', '__rfloordiv__', '__rlshift__', '__rmod__', 
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', 
        '__rtruediv__', '__rxor__', '__setitem__', '__setslice__', '__sub__', 
        '__truediv__', '__xor__', 'next',
    ]
    
    @classmethod
    def _create_class_proxy(cls, theclass):
        """creates a proxy for the given class"""
        
        def make_method(name):
            def method(self, *args, **kw):
                return getattr(object.__getattribute__(self, "_obj"), name)(*args, **kw)
            return method
        
        namespace = {}
        for name in cls._special_names:
            if hasattr(theclass, name):
                namespace[name] = make_method(name)
        return type("%s(%s)" % (cls.__name__, theclass.__name__), (cls,), namespace)
    
    def __new__(cls, obj, *args, **kwargs):
        """
        Create a proxy instance referencing `obj`.

        The triple `(obj, *args, **kwargs)` is passed to this class'
        __init__, so deriving classes can define an __init__ method of
        their own.

        .. note::

          `_class_proxy_cache` is unique per deriving class (each
          deriving class must hold its own cache).
        """
        try:
            cache = cls.__dict__["_class_proxy_cache"]
        except KeyError:
            cls._class_proxy_cache = cache = {}
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls._create_class_proxy(obj.__class__)
        instance = object.__new__(theclass)
        theclass.__init__(instance, obj, *args, **kwargs)
        return instance


## main: run tests

if "__main__" == __name__:
    import nose
    nose.runmodule()
