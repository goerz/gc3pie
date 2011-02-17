#! /usr/bin/env python
"""
Generic Python programming utility functions.

This module collects general utility functions, not specifically
related to GC3Libs.  A good rule of thumb for determining if a
function or class belongs in here is the following: place a function
or class in the :mod:`utils` if you could copy its code into the
sources of a different project and it would not stop working.
"""
# Copyright (C) 2009-2011 GC3, University of Zurich. All rights reserved.
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


import os
import os.path
import re
import shelve
import string
import sys
import time
import UserDict

from lockfile import FileLock

import gc3libs
import gc3libs.Exceptions


# ================================================================
#
#                     Generic functions
#
# ================================================================

class defaultdict(dict):
    """
    A backport of `defaultdict` to Python 2.4
    See http://docs.python.org/library/collections.html
    """
    def __new__(cls, default_factory=None):
        return dict.__new__(cls)
    def __init__(self, default_factory):
        self.default_factory = default_factory
    def __missing__(self, key):
        try:
            return self.default_factory()
        except:
            raise KeyError("Key '%s' not in dictionary" % key)
    def __getitem__(self, key):
        if not dict.__contains__(self, key):
            dict.__setitem__(self, key, self.__missing__(key))
        return dict.__getitem__(self, key)


def first(seq):
    """
    Return the first element of sequence or iterator `seq`.
    Raise `TypeError` if the argument does not implement
    either of the two interfaces.

    Examples::

      >>> s = [0, 1, 2]
      >>> first(s)
      0

      >>> s = {'a':1, 'b':2, 'c':3}
      >>> first(sorted(s.keys()))
      'a'
    """
    try: # try iterator interface
        return seq.next()
    except AttributeError:
        pass
    try: # seq is no iterator, try indexed lookup
        return seq[0]
    except IndexError:
        pass
    raise TypeError("Argument to `first()` method needs to be iterator or sequence.")


def get_and_remove(dictionary, key, default=None):
    """
    Return the value associated to `key` in `dictionary`, or `default`
    if there is no such key.  Remove `key` from `dictionary` afterwards.
    """
    if dictionary.has_key(key):
        result = dictionary[key]
        del dictionary[key]
    else:
        result = default
    return result


def ifelse(test, if_true, if_false):
    """
    Return `if_true` is argument `test` evaluates to `True`,
    return `if_false` otherwise.

    This is just a workaround for Python 2.4 lack of the
    conditional assignment operator::

      >>> a = 1
      >>> b = ifelse(a, "yes", "no"); print b
      yes
      >>> b = ifelse(not a, 'yay', 'nope'); print b
      nope

    """
    if test:
        return if_true
    else:
        return if_false


# In Python 2.7 still, `DictMixin` is an old-style class; thus, we need
# to make `Struct` inherit from `object` otherwise we loose properties
# when setting/pickling/unpickling
class Struct(object, UserDict.DictMixin):
    """
    A `dict`-like object, whose keys can be accessed with the usual
    '[...]' lookup syntax, or with the '.' get attribute syntax.

    Examples::

      >>> a = Struct()
      >>> a['x'] = 1
      >>> a.x
      1
      >>> a.y = 2
      >>> a['y']
      2

    Values can also be initially set by specifying them as keyword
    arguments to the constructor::

      >>> a = Struct(z=3)
      >>> a['z']
      3
      >>> a.z
      3
    """
    def __init__(self, initializer=None, **kw):
        if initializer is not None:
            try:
                # initializer is `dict`-like?
                for name, value in initializer.items():
                    self[name] = value
            except AttributeError: 
                # initializer is a sequence of (name,value) pairs?
                for name, value in initializer:
                    self[name] = value
        for name, value in kw.items():
            self[name] = value

    # the `DictMixin` class defines all std `dict` methods, provided
    # that `__getitem__`, `__setitem__` and `keys` are defined.
    def __setitem__(self, name, val):
        self.__dict__[name] = val
    def __getitem__(self, name):
        return self.__dict__[name]
    def keys(self):
        return self.__dict__.keys()


def progressive_number(qty=None):
    """
    Return a positive integer, whose value is guaranteed to
    be monotonically increasing across different invocations
    of this function, and also across separate instances of the
    calling program.

    Example::

      >>> n = progressive_number()
      >>> m = progressive_number()
      >>> m > n
      True

    If you specify a positive integer as argument, then a list of
    monotonically increasing numbers is returned.  For example::

      >>> ls = progressive_number(5)
      >>> len(ls)
      5

    In other words, `progressive_number(N)` is equivalent to::

      nums = [ progressive_number() for n in range(N) ]

    only more efficient, because it has to obtain and release the lock
    only once.  

    After every invocation of this function, the last returned number
    is stored into the file ``~/.gc3/next_id.txt``.

    *Note:* as file-level locking is used to serialize access to the
    counter file, this function may block (default timeout: 30
    seconds) while trying to acquire the lock, or raise a
    `LockTimeout` exception if this fails.

    @raise LockTimeout
    
    @return A positive integer number, monotonically increasing with every call.
            A list of such numbers if argument `qty` is a positive integer.
    """
    assert qty is None or qty > 0, \
        "Argument `qty` must be a positive integer"
    # FIXME: should use global config value for directory
    id_filename = os.path.expanduser("~/.gc3/next_id.txt")
    # ``FileLock`` requires that the to-be-locked file exists; if it
    # does not, we create an empty one (and avoid overwriting any
    # content, in case another process is also writing to it).  There
    # is thus no race condition here, as we attempt to lock the file
    # anyway, and this will stop concurrent processes.
    if not os.path.exists(id_filename):
        open(id_filename, "a").close()
    lock = FileLock(id_filename, threaded=False) 
    lock.acquire(timeout=30) # XXX: can raise 'LockTimeout'
    id_file = open(id_filename, 'r+')
    id = int(id_file.read(8) or "0", 16)
    id_file.seek(0)
    if qty is None:
        id_file.write("%08x -- DO NOT REMOVE OR ALTER THIS FILE: it is used internally by the gc3libs\n" % (id+1))
    else: 
        id_file.write("%08x -- DO NOT REMOVE OR ALTER THIS FILE: it is used internally by the gc3libs\n" % (id+qty))
    id_file.close()
    lock.release()
    if qty is None:
        return id+1
    else:
        return [ (id+n) for n in range(1, qty+1) ]


def defproperty(fn):
    """
    Decorator to define properties with a simplified syntax in Python 2.4.
    See http://code.activestate.com/recipes/410698-property-decorator-for-python-24/#c6
    for details and examples.
    """
    p = { 'doc':fn.__doc__ }
    p.update(fn())
    return property(**p)


def dirname(pathname):
    """
    Same as `os.path.dirname` but return `.` in case of path names with no directory component.
    """
    dirname = os.path.dirname(pathname)
    if not dirname:
        dirname = '.'
    # FIXME: figure out if this is a desirable outcome.  i.e. do we want dirname to be empty, or do a pwd and find out what the current dir is, or keep the "./".  I suppose this could make a difference to some of the behavior of the scripts, such as copying files around and such.
    return dirname


class Enum(frozenset):
    """
    A generic enumeration class.  Inspired by:
    http://stackoverflow.com/questions/36932/whats-the-best-way-to-implement-an-enum-in-python/2182437#2182437
    with some more syntactic sugar added.

    An `Enum` class must be instanciated with a list of strings, that
    make the enumeration "label"::

      >>> Animal = Enum('CAT', 'DOG')
    
    Each label is available as an instance attribute, evaluating to
    itself::

      >>> Animal.DOG
      'DOG'

      >>> Animal.CAT == 'CAT'
      True

    As a consequence, you can test for presence of an enumeration
    label by string value::

      >>> 'DOG' in Animal
      True

    Finally, enumeration labels can also be iterated upon::

      >>> for a in Animal: print a
      DOG
      CAT
    """
    def __new__(cls, *args):
        return frozenset.__new__(cls, args)
    def __getattr__(self, name):
            if name in self:
                    return name
            else:
                    raise AttributeError("No '%s' in enumeration '%s'"
                                         % (name, self.__class__.__name__))
    def __setattr__(self, name, value):
            raise SyntaxError("Cannot assign enumeration values.")
    def __delattr__(self, name):
            raise SyntaxError("Cannot delete enumeration values.")


def deploy_configuration_file(filename, template_filename=None):
    """
    Ensure that configuration file `filename` exists; possibly
    copying it from the specified `template_filename`.

    Return `True` if a file with the specified name exists in the 
    configuration directory.  If not, try to copy the template file
    over and then return `False`; in case the copy operations fails, 
    a `NoConfigurationFile` exception is raised.

    If parameter `filename` is not an absolute path, it is interpreted
    as relative to `gc3libs.Default.RCDIR`; if `template_filename` is
    `None`, then it is assumed to be the same as `filename`.
    """
    if template_filename is None:
        template_filename = os.path.basename(filename)
    if not os.path.isabs(filename):
        filename = os.path.join(gc3libs.Default.RCDIR, filename)
    if os.path.exists(filename):
        return True
    else:
        try:
            # copy sample config file 
            if not os.path.exists(dirname(filename)):
                os.makedirs(dirname(filename))
            from pkg_resources import Requirement, resource_filename, DistributionNotFound
            sample_config = resource_filename(Requirement.parse("gc3pie"), 
                                              "gc3libs/etc/" + template_filename)
            import shutil
            shutil.copyfile(sample_config, filename)
            return False
        except IOError, x:
            gc3libs.log.critical("CRITICAL ERROR: Failed copying configuration file: %s" % x)
            raise gc3libs.Exceptions.NoConfigurationFile("No configuration file '%s' was found, and an attempt to create it failed. Aborting." % filename)
        except ImportError:
            raise gc3libs.Exceptions.NoConfigurationFile("No configuration file '%s' was found. Aborting." % filename)
        except DistributionNotFound, ex:
            raise AssertionError("BUG: Cannot access resources for Python package: %s."
                                 " Installation error?" % str(ex))


def from_template(template, **kw):
    """
    Return the contents of `template`, substituting all occurrences
    of Python formatting directives '%(key)s' with the corresponding values 
    taken from dictionary `kw`.

    If `template` is an object providing a `read()` method, that is
    used to gather the template contents; else, if a file named
    `template` exists, the template contents are read from it;
    otherwise, `template` is treated like a string providing the
    template contents itself.
    """
    if hasattr(template, 'read') and callable(template.read):
        template_contents = template.read()
    elif os.path.exists(template):
        template_file = file(template, 'r')
        template_contents = template_file.read()
        template_file.close()
    else:
        # treat `template` as a string
        template_contents = template
    # substitute `kw` into `t` and return it
    return (template_contents % kw)


class Log(object):
    """
    A list of messages with timestamps and (optional) tags.

    The `append` method should be used to add a message to the `Log`::

      >>> L = Log()
      >>> L.append('first message')
      >>> L.append('second one')

    The `last` method returns the text of the last message appended::

      >>> L.last()
      'second one'

    Iterating over a `Log` instance returns message texts in the
    temporal order they were added to the list::

      >>> for msg in L: print(msg)
      first message
      second one

    """
    def __init__(self):
        self._messages = [ ]

    def append(self, message, *tags):
        """
        Append a message to this `Log`.  

        The message is timestamped with the time at the moment of the
        call.

        The optional `tags` argument is a sequence of strings. Tags
        are recorded together with the message and may be used to
        filter log messages given a set of labels. *(This feature is
        not yet implemented.)*
        
        """
        self._messages.append((message, time.time(), tags))

    def last(self):
        """
        Return text of last message appended. 
        If log is empty, return empty string.
        """
        if len(self._messages) == 0:
            return ''
        else:
            return self._messages[-1][0]

    # shortcut for append
    def __call__(self, message, *tags):
        """Shortcut for `Log.append` (which see)."""
        self.append(message, *tags)

    def __iter__(self):
        """Iterate over messages in the temporal order they were added."""
        return iter([record[0] for record in self._messages])

    def __str__(self):
        """Return all messages texts in a single string, separated by newline characters."""
        return str.join('\n', [record[0] for record in self._messages])


def mkdir_with_backup(path):
    """
    Like `os.makedirs`, but if `path` already exists, rename the
    existing one appending a `.NUMBER` suffix.
    """
    if os.path.isdir(path):
        # directory exists; find a suitable extension and rename
        parent_dir = os.path.dirname(path)
        prefix = os.path.basename(path) + '.'
        p = len(prefix)
        suffix = 1
        for name in [ x for x in os.listdir(parent_dir) if x.startswith(prefix) ]:
            try:
                n = int(name[p:])
                suffix = max(suffix, n+1)
            except ValueError:
                # ignore non-numeric suffixes
                pass
        os.rename(path, "%s.%d" % (path, suffix))
    os.makedirs(path)


def safe_repr(obj):
    """
    Return a string describing Python object `obj`.  Avoids calling
    any Python magic methods, so should be safe to use as a "last
    resort" in implementation of `__str__` and `__repr__` magic.
    """
    return ("<`%s` instance @ %x>" 
            % (obj.__class__.__name__, id(obj)))


def same_docstring_as(referenced_fn):
    """
    Function decorator: sets the docstring of the following function
    to the one of `referenced_fn`.  

    Intended usage is for setting docstrings on methods redefined in
    derived classes, so that they inherit the docstring from the
    corresponding abstract method in the base class.
    """
    def decorate(f):
            f.__doc__ = referenced_fn.__doc__
            return f
    return decorate


# see http://stackoverflow.com/questions/31875/is-there-a-simple-elegant-way-to-define-singletons-in-python/1810391#1810391
class Singleton(object):
    """
    Derived classes of `Singleton` can have only one instance in the
    running Python interpreter.

       >>> x = Singleton()
       >>> y = Singleton()
       >>> x is y
       True

    """
    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Singleton, cls).__new__(cls, *args, **kw)
        return cls._instance


class PlusInfinity(Singleton):
    """
    An object that is greater-than any other object.

        >>> x = PlusInfinity()

        >>> x > 1
        True
        >>> 1 < x
        True
        >>> 1245632479102509834570124871023487235987634518745 < x
        True

        >>> x > sys.maxint
        True
        >>> x < sys.maxint
        False
        >>> sys.maxint < x
        True

    `PlusInfinity` objects are actually larger than *any* given Python
    object::

        >>> x > 'azz'
        True
        >>> x > object()
        True

    Note that `PlusInfinity` is a singleton, therefore you always get
    the same instance when calling the class constructor::

        >>> x = PlusInfinity()
        >>> y = PlusInfinity()
        >>> x is y
        True

    Relational operators try to return the correct value when
    comparing `PlusInfinity` to itself::

        >>> x < y
        False
        >>> x <= y
        True
        >>> x == y 
        True
        >>> x >= y
        True
        >>> x > y
        False

    """
    def __gt__(self, other):
        if self is other:
            return False
        else:
            return True
    def __ge__(self, other):
        return True
    def __lt__(self, other):
        return False
    def __le__(self, other):
        if self is other:
            return True
        else:
            return False
    def __eq__(self, other):
        if self is other:
            return True
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)



def string_to_boolean(word):
    """
    Convert `word` to a Python boolean value and return it.
    The strings `true`, `yes`, `on`, `1` (with any
    capitalization and any amount of leading and trailing
    spaces) are recognized as meaning Python `True`.
    Any other word is considered as boolean `False`.
    """
    if word.strip().lower() in [ 'true', 'yes', 'on', '1' ]:
        return True
    else:
        return False


def to_bytes(s):
    """
    Convert string `s` to an integer number of bytes.  Suffixes like
    'KB', 'MB', 'GB' (up to 'YB'), with or without the trailing 'B',
    are allowed and properly accounted for.  Case is ignored in
    suffixes.

    Examples::

      >>> to_bytes('12')
      12
      >>> to_bytes('12B')
      12
      >>> to_bytes('12KB')
      12000
      >>> to_bytes('1G')
      1000000000

    Binary units 'KiB', 'MiB' etc. are also accepted:

      >>> to_bytes('1KiB')
      1024
      >>> to_bytes('1MiB')
      1048576

    """
    last = -1
    unit = s[last].lower()
    if unit.isdigit():
        # `s` is a integral number
        return int(s)
    if unit == 'b':
        # ignore the the 'b' or 'B' suffix
        last -= 1
        unit = s[last].lower()
    if unit == 'i':
        k = 1024
        last -= 1
        unit = s[last].lower()
    else:
        k = 1000
    # convert the substring of `s` that does not include the suffix
    if unit.isdigit():
        return int(s[0:(last+1)])
    if unit == 'k':
        return int(float(s[0:last])*k)
    if unit == 'm':
        return int(float(s[0:last])*k*k)
    if unit == 'g':
        return int(float(s[0:last])*k*k*k)
    if unit == 't':
        return int(float(s[0:last])*k*k*k*k)
    if unit == 'p':
        return int(float(s[0:last])*k*k*k*k*k)
    if unit == 'e':
        return int(float(s[0:last])*k*k*k*k*k*k)
    if unit == 'z':
        return int(float(s[0:last])*k*k*k*k*k*k*k)
    if unit == 'y':
        return int(float(s[0:last])*k*k*k*k*k*k*k*k)

 
def send_mail(send_from, send_to, subject, text, files=[], server="localhost"):

    from smtplib import SMTP
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEBase import MIMEBase
    from email.MIMEText import MIMEText
    from email.Utils import COMMASPACE, formatdate
    from email import Encoders

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    
    msg.attach(MIMEText(text))
    
    for f in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(f,"rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 
                        'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)
        
    smtp = SMTP(server)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


## 
## Template support
##

try:
    import itertools
    SetProductIterator = itertools.product
except:
    # use our own implementation, in case `itertools` does not (yet)
    # provide the set-product
    class SetProductIterator(object):
        """Iterate over all elements in a cartesian product.

        Argument `factors` is a sequence, all whose items are sequences
        themselves: the returned iterator will return -upon each
        successive invocation- a list `[t_1, t_2, ..., t_n]` where `t_k`
        is an item in the `k`-th sequence.

        Examples::
          >>> list(SetProductIterator([]))
          [[]]
          >>> list(SetProductIterator([[1]]))
          [[1]]
          >>> list(SetProductIterator([[1],[1]]))
          [[1, 1]]
          >>> list(SetProductIterator([[1,2],[]]))
          [[]]
          >>> list(SetProductIterator([[1,2],[1]]))
          [[1, 1], [2, 1]]
          >>> list(SetProductIterator([[1,2],[1,2]]))
          [[1, 1], [2, 1], [1, 2], [2, 2]]
        """
        def __init__(self, *factors):
            self.__closed = False
            self.__factors = factors
            self.__L = len(factors)
            self.__M = [ len(s)-1 for s in factors ]
            self.__m = [0] * self.__L
            self.__i = 0

        def __iter__(self):
            return self

        def next(self):
            if self.__closed:
                raise StopIteration
            if (0 == self.__L) or (-1 in self.__M):
                # there are no factors, or one of them has no elements
                self.__closed = True
                return []
            else:
                if self.__i < self.__L:
                    # will return element corresponding to current multi-index
                    result = [ s[self.__m[i]]
                               for (i,s) in enumerate(self.__factors) ]
                    # advance multi-index
                    i = 0
                    while (i < self.__L):
                        if self.__m[i] == self.__M[i]:
                            self.__m[i] = 0
                            i += 1
                        else:
                            self.__m[i] += 1
                            break
                    self.__i = i
                    # back to caller
                    return result
                else:
                    # at end of iteration
                    self.__closed = True
                    raise StopIteration


class Template(object):
    """
    A template object is a pair `(obj, keywords)`.  Methods are
    provided to substitute the keyword values into `obj`, and to
    iterate over expansions of the given keywords (optionally
    filtering the allowed combination of keyword values).

    Second optional argument `validator` must be a function that
    accepts a set of keyword arguments, and returns `True` if the
    keyword combination is valid (can be expanded/substituted back
    into the template) or `False` if it should be discarded.
    The default validator passes any combination of keywords/values.
    """
    def __init__(self, template, 
                 validator=(lambda kws: True), **kw):
        self._template = template
        self._keywords = kw
        self._valid = validator

    def substitute(self, **kw):
        """
        Return result of interpolating the value of keywords into the
        template.  Keyword arguments `kw` can be used to override
        keyword values passed to the constructor.

        If the templated object provides a `substitute` method, then
        return the result of invoking it with the template keywords as
        keyword arguments.  Otherwise, return the result of applying
        Python standard library's `string.Template.safe_substitute()`
        on the string representation of the templated object.

        Raise `ValueError` if the set of keywords/values is not valid
        according to the validator specified in the constructor.
        """
        kws = self._keywords.copy()
        kws.update(kw)
        if self._valid(kws):
            try:
                return self._template.substitute(**kws)
            except AttributeError:
                return string.Template(str(self._template)).safe_substitute(kws)
        else:
            raise ValueError("Invalid substitution values in template.")
    def __str__(self):
        """Alias for `Template.substitute`."""
        return self.substitute()

    def __repr__(self):
        """
        Return a string representation such that `x == eval(repr(x))`.
        """
        return str.join('', ["Template(", 
                             str.join(', ', [repr(self._template)] +
                                      [ ("%s=%s" % (k,v)) 
                                        for k,v in self._keywords.items() ]),
                             ')'])
                         

    def expansions(self, **kws):
        """
        Iterate over all valid expansions of the templated object
        *and* the template keywords.  Returned items are `Template`
        instances constucted with the expanded template object and a
        valid combination of keyword values.
        """
        kws_ = self._keywords.copy()
        kws_.update(kws)
        for kw in expansions(kws_):
            #if self._valid(kw):
            for item in expansions(self._template, **kw):
                # propagate expanded keywords upwards;
                # this allows container templates to
                # check validity based on keywords expanded
                # on contained templates as well.
                new_kw = kw.copy()
                for v in kw.values():
                    if isinstance(v, Template):
                        new_kw.update(v._keywords)
                if self._valid(new_kw):
                    yield Template(item, self._valid, **new_kw)


def expansions(obj, **kw):
    """
    Iterate over all expansions of a given object, recursively
    expanding all templates found.  How the expansions are actually
    computed, depends on the type of object being passed in the first
    argument `obj`:

    * If `obj` is a `list`, iterate over expansions of items in `obj`.
      (In particular, this flattens out nested lists.)

      Example::

        >>> L = [0, [2, 3]]
        >>> list(expansions(L))
        [0, 2, 3]

    * If `obj` is a dictionary, return dictionary formed by all
      combinations of a key `k` in `obj` with an expansion of the
      corresponding value `obj[k]`.  Expansions are computed by
      recursively calling `expansions(obj[k], **kw)`.

      Example::
      
        >>> D = {'a':1, 'b':[2,3]}
        >>> list(expansions(D))
        [{'a': 1, 'b': 2}, {'a': 1, 'b': 3}]

    * If `obj` is a `tuple`, iterate over all tuples formed by the
      expansion of every item in `obj`.  (Each item `t[i]` is expanded
      by calling `expansions(t[i], **kw)`.)

      Example::

        >>> T = (1, [2, 3])
        >>> list(expansions(T))
        [(1, 2), (1, 3)]

    * If `obj` is a `Template` class instance, then the returned values
      are the result of applying the template to the expansion of each
      of its keywords.

      Example::

        >>> T1 = Template("a=${n}", n=[0,1])
        >>> list(expansions(T1))
        [Template('a=${n}', n=0), Template('a=${n}', n=1)]

      Note that keywords passed to the `expand` invocation override
      the ones used in template construction::

        >>> T2 = Template("a=${n}")
        >>> list(expansions(T2, n=[1,3]))
        [Template('a=${n}', n=1), Template('a=${n}', n=3)]

        >>> T3 = Template("a=${n}", n=[0,1])
        >>> list(expansions(T3, n=[2,3]))
        [Template('a=${n}', n=2), Template('a=${n}', n=3)]

    * Any other value is returned unchanged.

      Example:
      
        >>> V = 42
        >>> list(expansions(V))
        [42]

    """
    if isinstance(obj, dict):
        keys = tuple(obj.keys()) # fix a key order
        for items in SetProductIterator(*[ list(expansions(obj[keys[i]], **kw))
                                           for i in range(len(keys)) ]):
            yield dict((keys[i], items[i]) for i in range(len(keys)))
    elif isinstance(obj, tuple):
        for items in SetProductIterator(*[ list(expansions(u, **kw)) for u in obj ]):
            yield tuple(items)
    elif isinstance(obj, list):
        for item in obj:
            for result in expansions(item, **kw):
                yield result
    elif isinstance(obj, Template):
        for s in obj.expansions(**kw):
            yield s
    else:
        yield obj



##
## Main 
##

if __name__ == '__main__':
    import doctest
    doctest.testmod()
