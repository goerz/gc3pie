#! /usr/bin/env python
"""
Authentication support for the GC3Libs.
"""
# Copyright (C) 2009-2010 GC3, University of Zurich. All rights reserved.
#
# Includes parts adapted from the ``bzr`` code, which is
# copyright (C) 2005, 2006, 2007, 2008, 2009 Canonical Ltd
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


from gc3libs.Exceptions import AuthenticationException


class Auth(object):
    types = {}
    # new proposal
    def __init__(self, authorizations, auto_enable):
        self.auto_enable = auto_enable
        self.__auths = { }
        self._auth_dict = authorizations
        self._auth_type = { }
        for auth_name, auth_params in self._auth_dict.items():
            self._auth_type[auth_name] = Auth.types[auth_params['type']]

    def get(self, auth_name):
        if not self.__auths.has_key(auth_name):
            try:
                a =  self._auth_type[auth_name](** self._auth_dict[auth_name])
                if not a.is_valid():
                    raise Exception('Missing required configuration parameters')

                if not a.check():
                    if self.auto_enable:
                        try:
                            a.enable()
                        except Exception, x:
                            gc3libs.log.debug("Got exception while enabling auth '%s',"
                                               " will remember for next invocations:"
                                               " %s: %s" % (auth_name, x.__class__.__name__, x))
                            a = x
                    else:
                        a = AuthenticationException("No valid credentials of type '%s'"
                                                    " and `auto_enable` not set." % auth_name)
            except KeyError:
                a = ConfigurationError("Unknown auth '%s' - check configuration file" % auth_name)
            except Exception, x:
                a = AuthenticationException("Got error while creating auth '%s': %s: %s"
                                            % (auth_name, x.__class__.__name__, x))

            self.__auths[auth_name] = a

        a = self.__auths[auth_name]
        if isinstance(a, Exception):
            raise a
        return a

    @staticmethod
    def register(auth_type, ctor):
        Auth.types[auth_type] = ctor


class NoneAuth(object):
    """Authentication proxy to use when no authentication is needed."""
    def __init__(self, **authorization):
        self.__dict__.update(authorization)

    def is_valid(self):
        return True
    
    def check(self):
        return True

    def enable(self):
        return True

Auth.register('none', NoneAuth)
# register additional authentication types
# FIXME: it would be nice to have some kind of auto-discovery instead
import gc3libs.authentication.grid
import gc3libs.authentication.ssh
    

## main: run tests

if "__main__" == __name__:
    import doctest
    doctest.testmod(name="__init__",
                    optionflags=doctest.NORMALIZE_WHITESPACE)
