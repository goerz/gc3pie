#! /usr/bin/env python
#
"""
"""
# Copyright (C) 2012, GC3, University of Zurich. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
__docformat__ = 'reStructuredText'
__version__ = '$Revision$'

import time

from gc3libs import log
from gc3libs.persistence.store import Persistable, Store
from gc3libs.persistence._ac_proxy import ACProxy
import gc3libs.exceptions


def create_proxy_class(cls, obj, extra):
    """
    This function will create a new `Proxy` object starting from the
    tuple (func, arguments) returned by `Proxy.__reduce_ex__()`.

    It is needed because otherwise pickle will never know how to
    re-create the `Proxy` instance, as it will only know about the
    proxied class.

    Arguments:

      `cls`: is the class name to use, one of `Proxy` or `BaseProxy`

      `obj`: is the proxied object

      `extra`: is a dictionary containing extra attribute of the
               `Proxy` class saved during the pickling process. Please
               note that this function will not update *any*
               attribute, but will only check for specific attributes.
    """
    # (re)construct object
    pxy = cls(obj)
    # set pickle persistent ID
    if 'persistent_id' in extra:
        pxy.persistent_id = extra['persistent_id']
    return pxy

class MemoryPool(object):
    """
    Store a set of Proxy objects but keep in memory only a fixed amount of them;
    others are re-loaded from the associated persistent storage upon access.

    It works with any `Proxy` object.

    This class is basically a FIFO where at each addition
    (:meth:`add`) all proxy objects but `self.maxobjects` are saved to
    the persistent storage and the referenced object is removed from
    memory.  The :meth:`refresh` method can also be invoked to force
    flushing objects to disk.

    You can customize the behavior by subclassing `MemoryPool` and
    overriding the two main methods: :meth:`cmp` and :meth:`keep`.
    """

    def __init__(self, storage=None, maxobjects=0, minobjects=None):
        """
        Create a `MemoryPool` instance, given the associated
        persistent store and maximum number of live objects to keep in
        memory.

        The `maxobjects` argument controls how many live objects are
        kept in memory.  If `maxobjects` is 0, then no object is ever
        flushed to persistent storage (i.e., this class becomes a
        no-op).

        The `minobjects` argument is used when a new refresh cycle is
        run, and controls the minimum number of live objects the
        MemoryPool will keep. When `maxobjects` limit is hit and a new
        refresh cycle is run, a certain number of objects will be
        flushed to persistent storage but no more than the current
        number of objects minus `minobjects`.

        Default value for `minobjects` is `maxobjects`/2.

        If `maxobjects` is not defined, the value of `minobjects` is
        meaningless because no refresh cycle is called.

        Example usage:

        1. Setup a `gc3libs.Store` instance to use as persistent storage::

            >>> import tempfile, os
            >>> from gc3libs.persistence import make_store
            >>> from gc3libs import Task
            >>> (f, tmp) = tempfile.mkstemp()
            >>> store = make_store("sqlite://%s" % tmp)

        2. Create a `MemoryPool` instance with this store and the maximum number
        of objects we want to save::

            >>> from gc3libs.persistence.proxy import memory_manager as mempool
            >>> mempool.set_storage(store)
            >>> mempool.maxobjects(10)
            10

           default value for `minobjects` is `maxobjects`/2:

            >>> mempool.minobjects()
            5

        3. Add 15 Proxy objects to the memory pool (we can add only
        `Proxy` objects)::

            >>> for i in range(15):
            ...     mempool.add(Proxy(Task(jobname=str(i))))

        4. The `refresh` method removes the 10 'older' objects, where
        'older' is computed by the time the objects were added to the
        `MemoryPool`::

            >>> mempool.refresh()
            >>> len([i for i in mempool if i.proxy_saved()])
            10
            >>> len([i for i in mempool if not i.proxy_saved()])
            5
            >>> mempool.flush()
            >>> os.remove(tmp)

        It is currently called each time `add` is called, but this may
        change in future.
          """

        self._storage = storage
        self._proxies = set()
        self._maxobjects = maxobjects
        self._minobjects = minobjects

    def maxobjects(self, num=None):
        """
        Getter/Setter for `maxobjects` attribute
        """
        if num is not None:
            self._maxobjects = num
        return self._maxobjects

    def minobjects(self, num=None):
        """
        Getter/Setter for `minobjects` attribute
        """
        if num is not None:
            self._minobjects = num
        if self._minobjects is None:
            return self._maxobjects/2
        else:
            return self._minobjects

    def set_storage(self, storage, overwrite=True):
        """
        Set the internal storage for `storage`.
        """
        if not self._storage or overwrite:
            self._storage = storage

    def get_storage(self):
        return self._storage

    def add(self, obj):
        """
        Add `proxy` object to the memory pool.
        """
        self._proxies.add(obj)
        obj.proxy_set_manager(self)
        if self.maxobjects() and len([obj for obj in self._proxies if not obj.proxy_saved()]) > self.maxobjects():
            self.refresh()

    def extend(self, objects):
        """
        Add sequence of objects that will be added to the pool.
        """
        for obj in objects:
            self.add(obj)

    def remove(self, obj):
        """
        Remove object from the memory pool
        """
        self._proxies.remove(obj)

    def flush(self):
        self._proxies = set()

    def refresh(self):
        """Refresh the list of proxies, forget "old" proxies if
        needed"""

        # If policy_function is defined, forget all objects we don't
        # want to remember anymore.
        living = len([i for i in self._proxies if not i.proxy_saved()])
        for obj in self._proxies:
            if not self.keep(obj):
                obj.proxy_forget()
                living -= 1

        if self.maxobjects():
            proxies = sorted(self._proxies, cmp=lambda x,y: self.cmp(x,y))
            while living > self.minobjects() and proxies:
                proxies.pop().proxy_forget()
                living -= 1

    def __iter__(self):
        return iter(self._proxies)

    @staticmethod
    def last_accessed(obj1, obj2):
        """Default comparison function used to sort proxies. It uses
        the `last_access` method of the objects to sort them.

        >>> p1 = Proxy("p1")
        >>> p2 = Proxy("p2")
        >>> p1.strip() == "p1"
        True
        >>> p2.strip() == "p2"
        True
        >>> MemoryPool.last_accessed(p1, p2)
        -1

        For the sake of our refresh function, any 'forgotten'
        object is considered *greater than* any non-forgotten object.
        """
        if cmp(obj2.proxy_saved(), obj1.proxy_saved()):
            return cmp(obj2.proxy_saved(), obj1.proxy_saved())
        return cmp(obj1.proxy_last_accessed(), obj2.proxy_last_accessed())

    def cmp(self, x, y):
        """This method is used to sort the list of Proxy
        objects in order to decide which proxies need to be forgotten.

        Default sorting method is based on the access time of any
        attribute of the proxied argument, in order to dump the
        'oldest' jobs.

        You can override this method by subclassing `MemoryPool`, but
        please remember that accessing attributes other than the ones
        stored on the Proxy itself may cause multiple `save` and
        `load` of the same object, thus degrading the overall
        performance.

        Moreover, since this function is called *after* the
        :meth:`keep` method, it is possible that an object already
        *forgotten* by the `keep` method is then loaded again because
        of the comparison.

        Therefore, it's probably safer not to mix `keep` and `cmp`
        methods in your implementation.
        """
        return MemoryPool.last_accessed(x, y)

    def keep(self, obj):
        """This method is used to decide if an object has to be
        forgotten or not.

        By default only least accessed objects are forgotten, thus
        this function returns always True.

        Please note that this method is called before the :meth:`cmp`
        method, and customizing both methods may not be safe. Please
        check the documentation for the :meth:`cmp` method too.
        """
        return True

    def getattr_called(self, proxy, name):
        """
        This method is called by a `proxy` everytime the
        __getattribute__ method of the proxy is called with argument
        `name`."""
        pass

    def proxy_loaded(self, proxy):
        """
        This method is called whenever an object is loaded from disk.
        """
        pass

# Global Memory Manager
memory_manager = MemoryPool()

class BaseProxy(ACProxy):
    """
    Base class for all `Proxy` objects.

    To create a BaseProxy object simply type:

    >>> p = BaseProxy(1)
    >>> type(p)
    <class 'gc3libs.persistence.proxy.BaseProxy(int)'>
    >>> isinstance(p, BaseProxy)
    True
    >>> isinstance(p, int)
    True

    The string representation of a proxy is the same as the proxied
    object's:

    >>> repr(p)
    '1'
    >>> str(p)
    '1'
    
    Adding a proxy to another object will work but will probably
    result in a non-proxy instance.
    
    >>> p+1
    2
    >>> type(p+1)
    <type 'int'>

    This class is designed in order to work well with `pickle` and
    with any of the `gc3libs.persistence.store`.
    """

    _reserved_names = ['_obj', '__reduce__', '__reduce_ex__', 'persistent_id', '_repr', '_str']
    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)
        object.__setattr__(self, "_str", str(obj))
        object.__setattr__(self, "_repr", repr(obj))

    #
    # proxying (special cases)
    #
    def __getattribute__(self, name):
        if name in BaseProxy._reserved_names:
            return object.__getattribute__(self, name)
        else:
            return getattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name, value):
        if name in Proxy._reserved_names:
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, "_obj"), name, value)

    def __str__(self):
        return self._str

    def __repr__(self):
        return self._repr


    @staticmethod
    def _make_method(name):
        def method(self, *args, **kw):
            return getattr(object.__getattribute__(self, "_obj"), name)(*args, **kw)
        return method

    @classmethod
    def _create_class_proxy(cls, theclass):
        """Create a proxy for the given class `theclass`."""
        namespace = {}
        for name in cls._special_names:
            if hasattr(theclass, name) and not hasattr(cls, name):
                namespace[name] = BaseProxy._make_method(name)
        return type("%s(%s)" % (cls.__name__, theclass.__name__), (cls,), namespace)

    def __reduce_ex__(self, proto):
        return ( create_proxy_class,
                 (BaseProxy,
                  object.__getattribute__(self, '_obj'),
                  object.__getattribute__(self, '__dict__') ),
                 )


class Proxy(BaseProxy):
    """
    Proxy an arbitrary object, reloading it from associated persistent
    storage if it's been deleted from memory.

    Example::

      >>> from gc3libs.persistence import make_store
      >>> import tempfile, os
      >>> (fd, tmpname) = tempfile.mkstemp()
      >>> from gc3libs import Task
      >>> p = Proxy(Task(jobname='NoTask'))
      >>> memory_manager.set_storage(make_store("sqlite://%s" % tmpname))
      >>> p # doctest: +ELLIPSIS
      <gc3libs.Task object at ...>
      >>> object.__getattribute__(p, "_obj") # doctest: +ELLIPSIS
      <gc3libs.Task object at ...>
      >>> p.jobname
      'NoTask'

    This `Proxy` class has the ability to 'forget' the associated
    object, i.e., remove the live copy from memory.  After that, any
    access to the objects' attributes will trigger a reload of the
    object from persistent storage.

    Example::

      >>> p.proxy_forget()
      >>> object.__getattribute__(p, "_obj") # doctest: +ELLIPSIS

    The object has been *forgotten*, and hopefully saved in the
    persistent storage. Accessing an attribute, however, transparently
    triggers object reload, so the running code sees no difference::

      >>> p.jobname
      'NoTask'

    If not store is defined, no object is saved to store and thus the
    reference to the object is never deleted.

      >>> memory_manager.set_storage(None)
      >>> p = Proxy(Task(jobname='NoTask2'))
      >>> p.proxy_forget()
      >>> object.__getattribute__(p, "_obj") # doctest: +ELLIPSIS
      <gc3libs.Task object at ...>
      >>> p.jobname
      'NoTask2'

    (Clean up temporary files used for testing.)
    ::

      >>> memory_manager.flush()
      >>> os.remove(tmpname)
    """

    _reserved_names = BaseProxy._reserved_names + [
        "_obj_id", "_manager", "_saved", "_last_access", "_post",
        "proxy_set_manager", "changed",
        "proxy_forget", "proxy_last_accessed", "proxy_saved", "proxy_load"]

    def __init__(self, obj, storage=None, manager=None, post_load=None):
        BaseProxy.__init__(self, obj)
        object.__setattr__(self, "_last_access", -1)
        object.__setattr__(self, "_saved", False)
        object.__setattr__(self, "_post", post_load)
        if not manager:
            manager = memory_manager
        object.__setattr__(self, "_manager", manager)
        manager.add(self)


    def __getattribute__(self, name):
        if name in Proxy._reserved_names:
            return object.__getattribute__(self, name)

        manager = object.__getattribute__(self, "_manager")
        if manager:
            manager.getattr_called(self, name)

        obj = object.__getattribute__(self, "_obj")

        if not obj:
            obj = self.proxy_load()
        object.__setattr__(self, "_last_access", time.time())
        return getattr(obj, name)

    def proxy_set_manager(self, manager):
        """
        Set the Memory Manager to `manager`. By default, the module's
        memory manager will be used.
        """
        old =  object.__getattribute__(self, '_manager')
        if old is manager:
            return
        if old and self in old:
            old.remove(self)
        object.__setattr__(self, '_manager', manager)

    def proxy_forget(self):
        """
        Save the object to the persistent storage and remove any
        reference to it.
        """
        obj = object.__getattribute__(self, '_obj')
        if not obj:
            return

        storage = self._manager.get_storage()
        if storage:
            try:
                p_id = storage.save(obj)
                object.__setattr__(self, "_obj", None)
                object.__setattr__(self, "_obj_id", p_id)
                object.__setattr__(self, "_saved", True)
                log.debug("Proxy: proxy_forget(): object %s saved to persistent store with persistent id %s." % (type(obj), p_id))
            except Exception, ex:
                log.error("Proxy: Error saving object to persistent storage: %s" % ex)
        else:
            log.warning("Proxy: `proxy_forget()` called but no persistent storage has been defined. Aborting *without* deleting proxied object")

    def proxy_load(self):
        """
        Load and returns the internal object.
        """
        log.debug("Proxy: called proxy_load()")
        obj = object.__getattribute__(self, "_obj")
        manager = object.__getattribute__(self, "_manager")
        storage = manager.get_storage()
        if not obj:
            assert isinstance(storage, Store)

            obj_id = object.__getattribute__(self, "_obj_id")
            assert storage and obj_id
            obj = storage.load(obj_id)
            object.__setattr__(self, "_obj", obj)
            object.__setattr__(self, "_saved", False)
            log.debug("Proxy: proxy_load(): object %s with persistent id %s has been loaded from persistent store." % (type(obj), p_id))
            if self._post:
                self._post(obj)
            manager.proxy_loaded(obj)
        return obj

    def proxy_last_accessed(self):
        """
        Return the value of the `time.time()` function at the time of
        last access of the object. Returns `-1` if it was never
        accessed.
        """
        return object.__getattribute__(self, "_last_access")

    def proxy_saved(self):
        """
        Returns True if the object is correctly saved and not present
        in the internal reference. Returns False otherwise.
        """
        return object.__getattribute__(self, '_saved')

    def __reduce_ex__(self, proto):
        """
        Produce a special representation of the object so that pickle
        will be able to rebuild the Proxy instance correctly.
        """
        extra = {}
        try:
            extra['persistent_id'] = self.persistent_id
        except AttributeError:
            pass
        return ( create_proxy_class,
                 (Proxy,
                  object.__getattribute__(self, '_obj'),
                  extra ),
                 )

## main: run tests

if "__main__" == __name__:
    import nose
    nose.runmodule()
