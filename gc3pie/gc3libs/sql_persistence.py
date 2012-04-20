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
"""This file implements an SQL-based persistency driver to store
GC3pie objects in a SQL DB instead of using Pickle from
`persistent.FilesystemStore` class"""

__docformat__ = 'reStructuredText'
__version__ = '$Revision$'

from gc3libs.persistence import Store, IdFactory
from gc3libs.utils import same_docstring_as
import gc3libs.exceptions
from gc3libs import Task

import cPickle as pickle

class DummyObject:
    pass

def sqlite_factory(url):
    assert url.scheme == 'sqlite'
    try:
        import sqlite3 as sqlite
    except ImportError:
        import pysqlite2.dbapi2 as sqlite
    conn = sqlite.connect(url.path)
    c = conn.cursor()
    c.execute("select name from sqlite_master where type='table' and name='jobs'")
    try:
        c.next()
    except StopIteration:
        c.execute("create table jobs (id int not null, data blob, type varchar(128), jobid varchar(128), jobname varchar(255), jobstatus varchar(128), persistent_attributes text, primary key (id))")
    c.close()
    return conn

def mysql_factory(url):
    assert url.scheme == 'mysql'
    import MySQLdb, MySQLdb.constants.ER
    try:
        port = int(url.port)
    except:
        port=3306
    conn = MySQLdb.connect(host=url.hostname, port=port, user=url.username, passwd=url.password, db=url.path.strip('/'))
    c = conn.cursor()
    try:
        c.execute('select count(*) from jobs')
    except MySQLdb.ProgrammingError, e:
        if e.args[0] == MySQLdb.constants.ER.NO_SUCH_TABLE:
            c.execute("create table jobs (id int not null, data blob, type varchar(128), jobid varchar(128), jobname varchar(255), jobstatus varchar(128), persistent_attributes text,  primary key (id))")
    c.close()
    return conn

DRIVERS={'sqlite': sqlite_factory,
         'mysql': mysql_factory,
         }

def sql_next_id_factory(db):
    """
    This function will return a function which can be used as
    `next_id_fn` argument for the `IdFactory` class constructor.

    `db` is DB connection class conform to DB API2.0 specs

    The function returned has signature:

        sql_next_id(n=1)

    the id returned is the maximum `id` field in the `jobs` table plus
    1.
    """
    def sql_next_id(n=1):
        c = db.cursor()
        c.execute('select max(id) from jobs')
        nextid = c.fetchone()[0]
        if not nextid: nextid = 1
        else: nextid = int(nextid)+1
        c.close()
        return nextid
    
    return sql_next_id


class IntId(int):
    def __new__(cls, prefix, seqno):
        return int.__new__(cls, seqno)

    def __getnewargs__(self):
        return (None, int(self))

class SQL(Store):
    """
    Save and load objects in a SQL db. Uses Python's `pickle` module
    to serialize objects and parse the `Url` object to define the
    driver to use (`sqlite`, `MySQL`, `postgres`...), db, and
    optionally user and password.    

    >>> import tempfile, os
    >>> (fd, name) = tempfile.mkstemp()
    >>> from gc3libs.url import Url
    >>> url = Url('sqlite:///%s' % name)
    >>> db = SQL(url)
    >>> from sql_persistence import DummyObject
    >>> obj = DummyObject()
    >>> obj.x = 'test'
    >>> db.save(obj)
    1
    >>> db.list()
    [1]
    >>> db.save(obj)
    1
    >>> del obj
    >>> y = db.load(1)
    >>> y.x
    'test'
    >>> c = db._SQL__conn.cursor()
    >>> _ = c.execute('select  persistent_attributes from jobs where id=1')
    >>> pickle.loads(c.fetchone()[0].decode('base64'))
    {}
    >>> y.__persistent_attributes__ = ['pattr']
    >>> y.pattr = 'persistent'
    >>> db.replace(1, y)
    >>> _ = c.execute('select  persistent_attributes from jobs where id=1')
    >>> pickle.loads(c.fetchone()[0].decode('base64'))
    {'pattr': 'persistent'}
    
    >>> import os
    >>> os.remove(name)
    """
    def __init__(self, url, idfactory=None):
        """
        Open a connection to the storage database identified by
        url. It will use the correct backend (MySQL, psql, sqlite3)
        based on the url.scheme value
        """
        if url.scheme not in DRIVERS:
            raise NotImplementedError("DB Driver %s not supported" % url.scheme)
        
        self.__conn = DRIVERS[url.scheme](url)
        self.idfactory = idfactory
        if not idfactory:
            self.idfactory = IdFactory(next_id_fn=sql_next_id_factory(self.__conn), id_class=IntId)
            
    @same_docstring_as(Store.list)
    def list(self):
        c = self.__conn.cursor()
        c.execute('select id from jobs')
        ids = [i[0] for i in c.fetchall()]
        self.__conn.commit()
        c.close()
        return ids

    @same_docstring_as(Store.replace)
    def replace(self, id_, obj):
        self._save_or_replace(id_, obj, 'replace')
                              
    # copied from FilesystemStore
    @same_docstring_as(Store.save)
    def save(self, obj):
        if not hasattr(obj, 'persistent_id'):
            obj.persistent_id = self.idfactory.new(obj)
        return self._save_or_replace(obj.persistent_id, obj, 'save')

    def _save_or_replace(self, id_, obj, action):
        c = self.__conn.cursor()

        extra_fields = {}
        if hasattr(obj, '__persistent_attributes__'):
            for attr in obj.__persistent_attributes__:
                if hasattr(obj, attr):
                    extra_fields[attr] = getattr(obj, attr)

        pdata = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL).encode('base64')
        pextra = pickle.dumps(extra_fields, protocol=pickle.HIGHEST_PROTOCOL).encode('base64')
        # insert into db
        otype = ''
        jobid = ''
        jobname = ''
        jobstatus = ''
        
        if isinstance(obj, Task):
            otype = 'job'
            jobstatus = obj.execution.state
            if hasattr(obj.execution, 'lrms_jobid'):
                jobid = obj.execution.lrms_jobid
            jobname = obj.jobname

        c.execute("select id from jobs where id=%d" % id_)
        if not c.fetchone():
            c.execute("""insert into jobs ( \
id, data, type, jobid, jobname, jobstatus, persistent_attributes) \
values (?, ?, ?, ?, ?, ?, ?)""", (
id_, pdata, otype, jobid, jobname, jobstatus, pextra ))
        else:
            c.execute("""update jobs set  \
data=?, type=?, jobid=?, jobstatus=?, jobname=?, persistent_attributes=? \
where id=?""", (pdata,otype, jobid, jobstatus, jobname, pextra, id_))
        obj.persistent_id = id_
        self.__conn.commit()
        c.close()

        # return id
        return obj.persistent_id

    @same_docstring_as(Store.load)
    def load(self, id_):
        c = self.__conn.cursor()
        c.execute('select data  from jobs where id=%d' % id_)
        rawdata = c.fetchone()
        if not rawdata:
            raise gc3libs.exceptions.LoadError("Unable to find object %d" % id_)
        data = pickle.loads(rawdata[0].decode('base64'))
        self.__conn.commit()
        c.close()
        return data

    @same_docstring_as(Store.remove)
    def remove(self, id_):
        c = self.__conn.cursor()
        c.execute('delete from jobs where id=%d' % id_)
        self.__conn.commit()
        c.close()



## main: run tests

if "__main__" == __name__:
    import doctest
    doctest.testmod(name="sql_persistence",
                    optionflags=doctest.NORMALIZE_WHITESPACE)
