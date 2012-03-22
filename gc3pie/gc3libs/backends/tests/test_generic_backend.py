#! /usr/bin/env python
#
"""
"""
# Copyright (C) 2011, GC3, University of Zurich. All rights reserved.
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
"""
Check if all the backends are implementing all the needed methods.
"""
__docformat__ = 'reStructuredText'
__version__ = '$Revision$'

from gc3libs.backends import LRMS
import inspect

def check_class(cls):
    for name,attr in inspect.getmembers(LRMS):
        if inspect.ismethod(attr):
            if getattr(cls, name) == getattr(LRMS, name):
                raise NotImplementedError("Attribute %s of class %s not implemented" % (name, cls.__name__))

def test_shellcmd_backends():
    from gc3libs.backends.shellcmd import ShellcmdLrms    
    check_class(ShellcmdLrms)

def test_lsf_backends():
    from gc3libs.backends.lsf import LsfLrms    
    check_class(LsfLrms)

def test_pbs_backends():
    from gc3libs.backends.pbs import PbsLrms    
    check_class(PbsLrms)

def test_sge_backends():
    from gc3libs.backends.sge import SgeLrms    
    check_class(SgeLrms)


if "__main__" == __name__:
    test_shellcmd_backends()
    test_lsf_backends()
    test_pbs_backends()
    test_sge_backends()
