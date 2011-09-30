#! /usr/bin/env python
#
#   cmdline.py -- Prototypes for GC3Libs-based scripts
#
#   Copyright (C) 2010, 2011 GC3, University of Zurich
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Prototype classes for GC3Libs-based scripts.

Classes implemented in this file provide common and recurring
functionality for GC3Libs command-line utilities and scripts.  User
applications should implement their specific behavior by subclassing 
and overriding a few customization methods.

There are currently two public classes provided here:

:class:`GC3UtilsScript`
  Base class for all the GC3Utils commands. Implements a few methods
  useful for writing command-line scripts that operate on jobs by ID.
 
:class:`SessionBasedScript`
  Base class for the ``grosetta``/``ggamess``/``gcodeml`` scripts.
  Implements a long-running script to submit and manage a large number
  of jobs grouped into a "session".

"""
__author__ = 'Riccardo Murri <riccardo.murri@uzh.ch>'
__docformat__ = 'reStructuredText'


import cli # pyCLI
import cli.app
import csv
import fnmatch
import lockfile
import logging
import os
import os.path
import re
import sys
import random
from texttable import Texttable
import time


## interface to Gc3libs

import gc3libs
import gc3libs.core
import gc3libs.exceptions
import gc3libs.persistence
import gc3libs.utils


## parse command-line



class _Script(cli.app.CommandLineApp):
    """
    Base class for GC3Libs scripts.  

    By default, only the standard options ``-h``/``--help`` and
    ``-V``/``--version`` are considered; to add more, override
    `setup_options`:meth:

    There is no defaults for positional arguments, you *must* override 
    `setup_args`:meth: in derived classes.
    
    """

    ##
    ## CUSTOMIZATION METHODS
    ##
    ## The following are meant to be freely customized in derived scripts.
    ##

    def setup_args(self):
        """
        Set up command-line argument parsing.

        The default command line parsing considers every argument as
        an (input) path name; processing of the given path names is
        done in `parse_args`:meth:
        """
        raise NotImplementedError("Abstract method `_Script.setup_args()` called,"
                                  " which should have been implemented in a derived class")
                       
    def setup_options(self):
        """
        Override this method to add command-line options.
        """
        pass


    def parse_args(self):
        """
        Do any parsing of the command-line arguments before the main
        loop starts.  This is the place to check validity of the
        parameters passed as command-line arguments, and to perform
        setup of shared data structures and default values.

        The default implementation does nothing; you are free to
        override this method in derived classes.
        """
        pass


    ##
    ## pyCLI INTERFACE METHODS
    ##
    ## The following methods adapt the behavior of the
    ## `SessionBasedScript` class to the interface expected by pyCLI
    ## applications.  Think twice before overriding them, and read
    ## the pyCLI docs before :-)
    ##

    def __init__(self, **kw):
        """
        Perform initialization and set the version, help and usage
        strings.

        The help text to be printed when the script is invoked with the 
        ``-h``/``--help`` option will be taken from (in order of preference): 
          * the keyword argument `description`
          * the attribute `self.description`
        If neither is provided, an `AssertionError` is raised.

        The text to output when the the script is invoked with the
        ``-V``/``--version`` options is taken from (in order of
        preference):
          * the keyword argument `version`
          * the attribute `self.version`
        If none of these is provided, an `AssertionError` is raised.

        The `usage` keyword argument (if provided) will be used to
        provide the program help text; if not provided, one will be
        generated based on the options and positional arguments
        defined in the code.

        Any additional keyword argument will be used to set a
        corresponding instance attribute on this Python object.

        XXX: version if not documented to be a required attribute
        XXX: why description and version are not declared as argument to be
        passed to the __init__ method even if they are treated as compulsory
        arguments ?
        """
        # use keyword arguments to set additional instance attrs
        for k,v in kw.items():
            if k not in ['name', 'description']:
                setattr(self, k, v)
        # init and setup pyCLI classes
        if not kw.has_key('version'):
            try:
                kw['version'] = self.version
            except AttributeError:
                raise AssertionError("Missing required parameter 'version'.")
        if not kw.has_key('description'):
            if self.__doc__ is not None:
                kw['description'] = self.__doc__
            else:
                raise AssertionError("Missing required parameter 'description'.")
        # allow overriding command-line options in subclasses
        def argparser_factory(*args, **kwargs):
            kwargs.setdefault('conflict_handler', 'resolve')
            kwargs.setdefault('formatter_class',
                              cli._ext.argparse.RawDescriptionHelpFormatter)
            return cli.app.CommandLineApp.argparser_factory(*args, **kwargs)
        self.argparser_factory = argparser_factory
        # init superclass
        cli.app.CommandLineApp.__init__(
            self,
            # remove the '.py' extension, if any
            name=os.path.splitext(os.path.basename(sys.argv[0]))[0],
            **kw
            )
        # provide some defaults
        self.verbose_logging_threshold = 0
        
    @property
    def description(self):
        """A string describing the application.

        Unless specified when the :class:`Application` was created, this
        property will examine the :attr:`main` callable and use its
        docstring (:attr:`__doc__` attribute).
        """
        if self._description is not None:
            return self._description
        else:
            return getattr(self.main, "__doc__", '')


    def setup(self):
        """
        Setup standard command-line parsing.

        GC3Utils scripts should probably override `setup_args`:meth: 
        and `setup_options`:meth: to modify command-line parsing.
        """
        ## setup of base classes
        cli.app.CommandLineApp.setup(self)

        self.add_param("-v", "--verbose", action="count", dest="verbose", default=0,
                       help="Print more detailed (debugging) information about the program's activity."
                       "The verbosity of the output can be controlled by adding/removing 'v' characters."
                       )
        return


    def pre_run(self):
        """
        Perform parsing of standard command-line options and call into
        `parse_args()` to do non-optional argument processing.

        Also sets up the ``gc3.gc3utils`` logger; it is controlled by
        the ``-v``/``--verbose`` command-line option.  Up to
        `self.verbose_logging_threshold` occurrences of ``-v`` are
        ignored, after which they start to lower the level of messages
        sent to standard error output.
        """
        ## finish setup
        self.setup_options()
        self.setup_args()

        ## parse command-line
        cli.app.CommandLineApp.pre_run(self)

        ## setup GC3Libs logging
        loglevel = max(1, logging.ERROR - 10 * max(0, self.params.verbose - self.verbose_logging_threshold))
        gc3libs.configure_logger(loglevel, self.name)
        self.log = logging.getLogger('gc3.gc3utils') # alternate: ('gc3.' + self.name)
        self.log.setLevel(loglevel)
        self.log.propagate = True

        # interface to the GC3Libs main functionality
        self._core = self._get_core()

        # call hook methods from derived classes
        self.parse_args()


    def run(self):
        """
        Execute `cli.app.Application.run`:meth: if any exception is
        raised, catch it, output an error message and then exit with
        an appropriate error code.
        """
        try:
            return cli.app.CommandLineApp.run(self)
        except gc3libs.exceptions.InvalidUsage, ex:
            # Fatal errors do their own printing, we only add a short usage message
            sys.stderr.write("Type '%s --help' to get usage help.\n" % self.name)
            return 64 # EX_USAGE in /usr/include/sysexits.h
        except KeyboardInterrupt:
            sys.stderr.write("%s: Exiting upon user request (Ctrl+C)\n" % self.name)
            return 13
        except SystemExit, ex:
            return ex.code
        # the following exception handlers put their error message
        # into `msg` and the exit code into `rc`; the closing stanza
        # tries to log the message and only outputs it to stderr if
        # this fails
        except lockfile.Error, ex:
            exc_info = sys.exc_info()
            msg = ("Error manipulating the lock file (%s: %s)."
                   " This likely points to a filesystem error"
                   " or a stale process holding the lock."
                   " If you cannot get this command to run after"
                   " a system reboot, please write to gc3pie@googlegroups.com"
                   " including any output you got by running '%s -vvvv %s'.")
            if len(sys.argv) > 0:
                msg %= (ex.__class__.__name__, str(ex),
                        self.name, str.join(' ', sys.argv[1:]))
            else:
                msg %= (ex.__class__.__name__, str(ex), self.name, '')
            rc = 1
        except AssertionError, ex:
            exc_info = sys.exc_info()
            msg = ("BUG: %s\n"
                   "Please send an email to gc3pie@googlegroups.com"
                   " including any output you got by running '%s -vvvv %s'."
                   " Thanks for your cooperation!")
            if len(sys.argv) > 0:
                msg %= (str(ex), self.name, str.join(' ', sys.argv[1:]))
            else:
                msg %= (str(ex), self.name, '')
            rc = 1
        except Exception, ex:
            msg = "%s: %s" % (ex.__class__.__name__, str(ex)) 
            if isinstance(ex, cli.app.Abort):
                rc = (ex.status)
            elif isinstance(ex, EnvironmentError):
                rc = 74 # EX_IOERR in /usr/include/sysexits.h
            else:
                # generic error exit
                rc = 1
        # output error message and -maybe- backtrace...
        try:
            self.log.critical(msg,
                              exc_info=(self.params.verbose > self.verbose_logging_threshold + 2))
        except:
            # no logging setup, output to stderr
            sys.stderr.write("%s: FATAL ERROR: %s\n" % (self.name, msg))
            if self.params.verbose > self.verbose_logging_threshold + 2:
                sys.excepthook(*exc_info)
        # ...and exit
        return 1


    ##
    ## INTERNAL METHODS
    ##
    ## The following methods are for internal use; they can be
    ## overridden and customized in derived classes, although there
    ## should be no need to do so.
    ##

    def _get_core(self,
                  config_file_locations=gc3libs.Default.CONFIG_FILE_LOCATIONS,
                  auto_enable_auth=True):
        """
        Return a `gc3libs.core.Core` instance configured by parsing
        the configuration file(s) located at `config_file_locations`.
        Order of configuration files matters: files read last overwrite
        settings from previously-read ones; list the most specific configuration
        files last.

        If `auto_enable_auth` is `True` (default), then `Core` will try to renew
        expired credentials; this requires interaction with the user and will
        certainly fail unless stdin & stdout are connected to a terminal.
        """
        # ensure a configuration file exists in the most specific location
        for location in reversed(config_file_locations):
            if os.access(os.path.dirname(location), os.W_OK|os.X_OK) \
                    and not gc3libs.utils.deploy_configuration_file(location, "gc3pie.conf.example"):
                # warn user
                self.log.warning("No configuration file '%s' was found;"
                                 " a sample one has been copied in that location;"
                                 " please edit it and define resources." % location)
        try:
            self.log.debug('Creating instance of Core ...')
            return gc3libs.core.Core(* gc3libs.core.import_config(config_file_locations, auto_enable_auth))
        except gc3libs.exceptions.NoResources:
            raise gc3libs.exceptions.FatalError(
                "No computational resources defined."
                " Please edit the configuration file(s): '%s'." 
                % (str.join("', '", config_file_locations)))
        except:
            self.log.debug("Failed loading config file from '%s'", 
                           str.join("', '", config_file_locations))
            raise


    def _select_resources(self, *resource_names):
        """
        Restrict resources to those listed in `resource_names`.
        Argument `resource_names` is a string listing all names of
        allowed resources (comma-separated), or a list of names of the
        resources to keep active.
        """
        patterns = [ ]
        for item in resource_names:
            patterns.extend(name for name in item.split(','))
        def keep_resource_if_matches(resource):
            """
            Return `True` iff `resource`'s `name` attribute matches
            one of the glob patterns in `patterns`.
            """
            for pattern in patterns:
                if fnmatch.fnmatch(resource.name, pattern):
                    return True
            return False
        kept = self._core.select_resource(keep_resource_if_matches)
        if kept == 0:
            raise gc3libs.exceptions.NoResources(
                "No resources match the names '%s'" 
                % str.join(',', resource_names))




class GC3UtilsScript(_Script):
    """
    Base class for GC3Utils scripts.  

    The default command line implemented is the following:

      script [options] JOBID [JOBID ...]

    By default, only the standard options ``-h``/``--help`` and
    ``-V``/``--version`` are considered; to add more, override
    `setup_options`:meth:
    To change default positional argument parsing, override 
    `setup_args`:meth:
    
    """

    ##
    ## CUSTOMIZATION METHODS
    ##
    ## The following are meant to be freely customized in derived scripts.
    ##

    def setup_args(self):
        """
        Set up command-line argument parsing.

        The default command line parsing considers every argument as a
        job ID; actual processing of the IDs is done in
        `parse_args`:meth:
        """
        self.add_param('args', nargs='*', metavar='JOBID', 
                       help="Job ID string identifying the jobs to operate upon.")
                       
    ##
    ## pyCLI INTERFACE METHODS
    ##
    ## The following methods adapt the behavior of the
    ## `SessionBasedScript` class to the interface expected by pyCLI
    ## applications.  Think twice before overriding them, and read
    ## the pyCLI docs before :-)
    ##

    def __init__(self, **kw):
        _Script.__init__(self, main=self.main, **kw)


    def setup(self):
        """
        Setup standard command-line parsing.

        GC3Utils scripts should probably override `setup_args`:meth: 
        and `setup_options`:meth: to modify command-line parsing.
        """
        ## setup of base classes (creates the argparse stuff)
        _Script.setup(self)
        ## local additions
        self.add_param("-s", "--session", action="store", default=gc3libs.Default.JOBS_DIR,
                       help="Directory where job information will be stored.")


    def pre_run(self):
        """
        Perform parsing of standard command-line options and call into
        `parse_args()` to do non-optional argument processing.
        """
        ## base class parses command-line
        _Script.pre_run(self)

        jobs_dir = self.params.session
        if jobs_dir != gc3libs.Default.JOBS_DIR:
            if (not os.path.isdir(jobs_dir)
                and not jobs_dir.endswith('.jobs')):
                jobs_dir = jobs_dir + '.jobs'
        self._store = gc3libs.persistence.FilesystemStore(
            jobs_dir, 
            idfactory=gc3libs.persistence.JobIdFactory()
            )


    ##
    ## INTERNAL METHODS
    ##
    ## The following methods are for internal use; they can be
    ## overridden and customized in derived classes, although there
    ## should be no need to do so.
    ##

    def _get_jobs(self, job_ids, ignore_failures=True):
        """
        Iterate over jobs (gc3libs.Application objects) corresponding
        to the given Job IDs.

        If `ignore_failures` is `True` (default), errors retrieving a
        job from the persistence layer are ignored and the jobid is
        skipped, therefore the returned list can be shorter than the
        list of Job IDs given as argument.  If `ignore_failures` is
        `False`, then any errors result in the relevant exception being
        re-raised.
        """
        for jobid in job_ids:
            try:
                yield self._store.load(jobid)
            except Exception, ex:
                if ignore_failures:
                    gc3libs.log.error("Could not retrieve job '%s' (%s: %s). Ignoring.", 
                                      jobid, ex.__class__.__name__, str(ex),
                                      exc_info=(self.params.verbose > 2))
                    continue
                else:
                    raise



class SessionBasedScript(_Script):
    """
    Base class for ``grosetta``/``ggamess``/``gcodeml`` and like scripts.
    Implements a long-running script to submit and manage a large number
    of jobs grouped into a "session".

    The generic scripts implements a command-line like the following:

      PROG [options] INPUT [INPUT ...]

    First, the script builds a list of input files by recursively
    scanning each of the given INPUT arguments for files matching the
    `self.input_file_pattern` glob string (you can set it via a
    keyword argument to the ctor).  To perform a different treatment
    of the command-line arguments, override the
    :py:meth:`process_args()` method.

    Then, new jobs are added to the session, based on the results of
    the `process_args()` method above.  For each tuple of items
    returned by `process_args()`, an instance of class
    `self.application` (which you can set by a keyword argument to the
    ctor) is created, passing it the tuple as init args, and added to
    the session.

    The script finally proceeds to updating the status of all jobs in
    the session, submitting new ones and retrieving output as needed.
    When all jobs are done, the method :py:meth:`done()` is called, 
    and its return value is used as the script's exit code.

    The script's exitcode tracks job status, in the following way.
    The exitcode is a bitfield; only the 4 least-significant bits 
    are used, with the following meaning:
       ===  ============================================================
       Bit  Meaning
       ===  ============================================================
         0  Set if a fatal error occurred: `gcodeml` could not complete
         1  Set if there are jobs in `FAILED` state
         2  Set if there are jobs in `RUNNING` or `SUBMITTED` state
         3  Set if there are jobs in `NEW` state
       ===  ============================================================
    This boils down to the following rules:
       * exitcode == 0: all jobs terminated successfully, no further action
       * exitcode == 1: an error interrupted script execution
       * exitcode == 2: all jobs terminated, not all of them successfully
       * exitcode > 3: run the script again to progress jobs

    """

    ##
    ## CUSTOMIZATION METHODS
    ##
    ## The following are meant to be freely customized in derived scripts.
    ##

    def setup_args(self):
        """
        Set up command-line argument parsing.

        The default command line parsing considers every argument as
        an (input) path name; processing of the given path names is
        done in `parse_args`:meth:
        """
        self.add_param('args', nargs='*', metavar='INPUT', 
                       help="Path to input file or directory."
                       " Directories are recursively scanned for input files"
                       " matching the glob pattern '%s'" 
                       % self.input_filename_pattern)


    def make_directory_path(self, pathspec, jobname, *args):
        """
        Return a path to a directory, suitable for storing the output
        of a job (named after `jobname`).  It is not required that the
        returned path points to an existing directory.

        This is called by the default `process_args`:meth: using
        `self.params.output` (i.e., the argument to the
        ``-o``/``--output`` option) as `pathspec`, and `jobname` and
        `args` exactly as returned by `new_tasks`:meth:

        The default implementation substitutes the following strings
        within `pathspec`:
          * ``SESSION`` is replaced with the name of the current session
            (as specified by the ``-s``/``--session`` command-line option)
            with a suffix ``.out`` appended;
          * ``PATH`` is replaced with the path to directory containing
            `args[0]` (if it's an existing filename), or to the
            current directory;
          * ``NAME`` is replaced with `jobname`;
          * ``DATE`` is replaced with the current date, in *YYYY-MM-DD* format;
          * ``TIME`` is replaced with the current time, in *HH:MM* format.
          
        """
        if len(args) == 0:
            path = os.getcwd()
        else:
            arg0 = str(args[0])
            if os.path.isdir(arg0):
                path = arg0
            elif os.path.isfile(arg0):
                path = os.path.dirname(arg0)
            else:
                path = os.getcwd()
        return (pathspec
                .replace('SESSION', self.params.session + '.out')
                .replace('PATH', path)
                .replace('NAME', jobname)
                .replace('DATE', time.strftime('%Y-%m-%d'))
                .replace('TIME', time.strftime('%H:%M')))

    
    def process_args(self):
        """
        Process command-line positional arguments and set up
        `tasks`:attr: accordingly.  In particular, new jobs should be
        appended to `tasks`:attr: in this method: `self.tasks` is not
        altered elsewhere.

        This method is called by the standard `_main`:meth: after
        loading existing tasks into `self.tasks`.  New jobs should be
        appended to `self.tasks` and it is also permitted to remove
        existing ones.

        The default implementation calls `new_tasks`:meth: and adds to
        the session all jobs whose name does not clash with the
        jobname of an already existing task.

        See also: `new_tasks`:meth:
        """
        ## build job list
        new_jobs = list(self.new_tasks(self.extra))
        # pre-allocate Job IDs
        if len(new_jobs) > 0:
            self.store.idfactory.reserve(len(new_jobs))

        # add new jobs to the session
        existing_job_names = set(task.jobname for task in self.tasks)
        random.seed()
        for jobname, cls, args, kwargs in new_jobs:
            #self.log.debug("SessionBasedScript.process_args():"
            #               " considering adding new job defined by:"
            #               " jobname=%s cls=%s args=%s kwargs=%s ..."
            #               % (jobname, cls, args, kwargs))
            if jobname in existing_job_names:
                #self.log.debug("  ...already existing job, skipping it.")
                continue
            #self.log.debug("New job '%s', adding it to session." % jobname)
            kwargs.setdefault('jobname', jobname)
            kwargs.setdefault('requested_memory', self.params.memory_per_core)
            kwargs.setdefault('requested_cores', self.params.ncores)
            kwargs.setdefault('requested_walltime', self.params.walltime)
            kwargs.setdefault('output_dir',
                              self.make_directory_path(self.params.output,
                                                       jobname, *args))
            # create a new `Application` object
            try:
                app = cls(*args, **kwargs)
                self.tasks.append(app)
                self.log.debug("Added job '%s' to session." % jobname)
            except Exception, ex:
                self.log.error("Could not create job '%s': %s."
                               % (jobname, str(ex)), exc_info=__debug__)
                # XXX: should we raise an exception here?
                #raise AssertionError("Could not create job '%s': %s: %s" 
                #                     % (jobname, ex.__class__.__name__, str(ex)))


    def new_tasks(self, extra):
        """
        Iterate over jobs that should be added to the current session.
        Each item yielded must have the form `(jobname, cls, args,
        kwargs)`, where:

        * `jobname` is a string uniquely identifying the job in the
          session; if a job with the same name already exists, this
          item will be ignored.

        * `cls` is a callable that returns an instance of
          `gc3libs.Application` when called as `cls(*args, **kwargs)`.

        * `args` is a tuple of arguments for calling `cls`.

        * `kwargs` is a dictionary used to provide keyword arguments
          when calling `cls`.

        This method is called by the default `process_args`:meth:, passing
        `self.extra` as the `extra` parameter.

        The default implementation of this method scans the arguments
        on the command-line for files matching the glob pattern
        `self.input_filename_pattern`, and for each matching file returns
        a job name formed by the base name of the file (sans
        extension), the class given by `self.application`, and the
        full path to the input file as sole argument.

        If `self.instances_per_file` and `self.instances_per_job` are
        set to a value other than 1, for each matching file N jobs are
        generated, where N is the quotient of
        `self.instances_per_file` by `self.instances_per_job`.

        See also: `process_args`:meth:
        """
        inputs = self._search_for_input_files(self.params.args)

        for path in inputs:
            if self.instances_per_file > 1:
                for seqno in range(1, 1+self.instances_per_file, self.instances_per_job):
                    if self.instances_per_job > 1:
                        yield ("%s.%d--%s" % (gc3libs.utils.basename_sans(path),
                                              seqno, 
                                              min(seqno + self.instances_per_job - 1,
                                                  self.instances_per_file)),
                               self.application, [path], extra.copy())
                    else:
                        yield ("%s.%d" % (gc3libs.utils.basename_sans(path), seqno),
                               self.application, [path], extra.copy())
            else:
                yield (gc3libs.utils.basename_sans(path),
                       self.application, [path], extra.copy())


    def make_task_controller(self):
        """
        Return a 'Controller' object to be used for progressing tasks
        and getting statistics.  In detail, a good 'Controller' object
        has to implement `progress` and `stats` methods with the same
        interface as `gc3libs.core.Engine`.

        By the time this method is called (from `_main`:meth:), the
        following instance attributes are already defined:

        * `self._core`: a `gc3libs.core.Core` instance;
        * `self.tasks`: the list of `Task` instances to manage;
        * `self.store`: the `gc3libs.persistence.Store` instance
          that should be used to save/load jobs

        In addition, any other attribute created during initialization
        and command-line parsing is of course available.
        """
        return gc3libs.core.Engine(self._core, self.tasks, self.store,
                                   max_submitted = self.params.max_running,
                                   max_in_flight = self.params.max_running)


    def print_summary_table(self, output, stats):
        """
        Print a text summary of the session status to `output`.
        This is used to provide the "normal" output of the
        script; when the ``-l`` option is given, the output
        of the `print_tasks_table` function is appended.

        Override this in subclasses to customize the report that you
        provide to users.  By default, this prints a table with the
        count of tasks for each possible state.
        
        The `output` argument is a file-like object, only the `write`
        method of which is used.  The `stats` argument is a
        dictionary, mapping each possible `Run.State` to the count of
        tasks in that state; see `Engine.stats` for a detailed
        description.

        """
        table = Texttable(0) # max_width=0 => dynamically resize cells
        table.set_deco(0)    # no decorations
        table.set_cols_align(['r', 'r', 'c'])
        total = stats['total']
        for state in sorted(stats.keys()):
            table.add_row([
                    state, 
                    "%d/%d" % (stats[state], total),
                    "(%.1f%%)" % (100.0 * stats[state] / total)
                    ])
        output.write(table.draw())
        output.write("\n")


    def print_tasks_table(self, output=sys.stdout, states=gc3libs.Run.State):
        """
        Output a text table to stream `output`, giving details about
        tasks in the given states.
        """
        table = Texttable(0) # max_width=0 => dynamically resize cells
        table.set_deco(Texttable.HEADER) # also: .VLINES, .HLINES .BORDER
        table.header(['JobID', 'Job name', 'State', 'Info'])
        #table.set_cols_width([10, 20, 10, 35])
        table.set_cols_align(['l', 'l', 'l', 'l'])
        table.add_rows([ (task.persistent_id, task.jobname,
                          task.execution.state, task.execution.info)
                         for task in self.tasks
                         if task.execution.state in states ],
                       header=False)
        # XXX: uses texttable's internal implementation detail
        if len(table._rows) > 0:
            output.write(table.draw())
            output.write("\n")


    ##
    ## pyCLI INTERFACE METHODS
    ##
    ## The following methods adapt the behavior of the
    ## `SessionBasedScript` class to the interface expected by pyCLI
    ## applications.  Think twice before overriding them, and read
    ## the pyCLI docs before :-)
    ##

    # XXX: please explain this.
    def __unset_application_cls(*args, **kwargs):
        """Raise an error if users did not set `application` in `SessionBasedScript` initialization."""
        raise gc3libs.exceptions.Error("PLEASE SET `application` in `SessionBasedScript` CONSTRUCTOR")

    def __init__(self, **kw):
        """
        Perform initialization and set the version, help and usage
        strings.

        The help text to be printed when the script is invoked with the 
        ``-h``/``--help`` option will be taken from (in order of preference): 
          * the keyword argument `description`
          * the attribute `self.description`
        If neither is provided, an `AssertionError` is raised.

        The text to output when the the script is invoked with the
        ``-V``/``--version`` options is taken from (in order of
        preference):
          * the keyword argument `version`
          * the attribute `self.version`
        If none of these is provided, an `AssertionError` is raised.

        The `usage` keyword argument (if provided) will be used to
        provide the program help text; if not provided, one will be
        generated based on the options and positional arguments
        defined in the code.

        Any additional keyword argument will be used to set a
        corresponding instance attribute on this Python object.
        """
        self.tasks = [ ]
        self.stats_only_for = None #: by default, print stats of all kind of jobs
        self.instances_per_file = 1
        self.instances_per_job = 1
        self.extra = { } #: extra kw arguments passed to `parse_args`
        # use bogus values that should point ppl to the right place
        self.input_filename_pattern = 'PLEASE SET `input_filename_pattern` IN `SessionBasedScript` CONSTRUCTOR'
        # XXX: what does the following call is for ?
        self.application = SessionBasedScript.__unset_application_cls
        ## init base classes
        _Script.__init__(
            self,
            main=self._main,
            **kw
            )
        
    def setup(self):
        """
        Setup standard command-line parsing.

        GC3Libs scripts should probably override `setup_args`:meth: 
        to modify command-line parsing.
        """
        ## setup of base classes
        _Script.setup(self)

        ## add own "standard options"
        
        # 1. job requirements
        self.add_param("-c", "--cpu-cores", dest="ncores", type=int, default=1, # 1 core
                       metavar="NUM",
                       help="Set the number of CPU cores required for each job (default: %(default)s)."
                       "NUM must be a whole number."
                       )
        self.add_param("-m", "--memory-per-core", dest="memory_per_core", type=int, default=2, # 2 GB
                       metavar="GIGABYTES",
                       help="Set the amount of memory required per execution core, in gigabytes (Default: %(default)s)."
                       "Currently, GIGABYTES can only be an integer number; no fractional amounts are allowed.")
        self.add_param("-r", "--resource", action="store", dest="resource_name", metavar="NAME",
                       default=None,
                       help="Select one or more computational resources;"
                       " NAME is a reource name or comma-separated list of such names."
                       " Use the command `glist` to list available resources")
        self.add_param("-w", "--wall-clock-time", dest="wctime", default=str(8), # 8 hrs
                       metavar="DURATION",
                       help="Set the time limit for each job (default %s for '8 hours')."
                       " Jobs exceeding this limit will be stopped and considered as 'failed'."
                       " The duration can be expressed as a whole number (indicating the duration in hours)"
                       " or as STRING in the form 'hours:minutes'."
                       )

        # 2. session control
        self.add_param("-s", "--session", dest="session", 
                       default=os.path.join(os.getcwd(), self.name),
                       metavar="PATH",
                       help="Use PATH to store jobs (default: '%(default)s')."
                       " If PATH is an existing directory, it will be used for storing job"
                       " information, and an index file (with suffix '.csv') will be created"
                       " in it.  Otherwise, the job information will be stored in a directory"
                       " named after PATH with a suffix '.jobs' appended, and the index file"
                       " will be named after PATH with a suffix '.csv' added."
                       )
        self.add_param("-N", "--new-session", dest="new_session", action="store_true", default=False,
                       help="Discard any information saved in the session directory (see '--session' option)"
                       " and start a new session afresh.  Any information about previous jobs is lost.")

        # 3. script execution control
        self.add_param("-C", "--continuous", type=int, dest="wait", default=0,
                       metavar="NUM",
                       help="Keep running, monitoring jobs and possibly submitting new ones or"
                       " fetching results every NUM seconds. Exit when all jobs are finished."
                       )
        self.add_param("-J", "--max-running", type=int, dest="max_running", default=50,
                       metavar="NUM",
                       help="Set the max NUMber of jobs (default: %(default)s)"
                       " in SUBMITTED or RUNNING state."
                       )
        self.add_param("-o", "--output",
                       dest="output", default=os.path.join(os.getcwd(), 'NAME'),
                       metavar='DIRECTORY',
                       help="Output files from all jobs will be collected in the specified"
                       " DIRECTORY path; by default, output files are placed in the same"
                       " directory where the corresponding input file resides.  If the"
                       " destination directory does not exist, it is created."
                       " The following strings will be substituted into DIRECTORY,"
                       " to specify an output location that varies with each submitted job:"
                       " the string 'PATH' is replaced by the directory where the job input resides;"
                       " the string 'NAME' is replaced by the job name;"
                       " 'DATE' is replaced by the submission date in ISO format (YYYY-MM-DD);"
                       " 'TIME' is replaced by the submission time formatted as HH:MM."
                       " 'SESSION' is replaced by the path to the session directory, with a '.out' appended."
                       )
        self.add_param("-l", "--state", action="store", nargs='?',
                       dest="states", default='',
                       const=str.join(',', gc3libs.Run.State),
                       help="Print a table of jobs including their status."
                       " Optionally, restrict output to jobs with a particular STATE or STATES"
                       " (comma-separated list)."
                       )
        return


    def pre_run(self):
        """
        Perform parsing of standard command-line options and call into
        `parse_args()` to do non-optional argument processing.
        """
        ## call base classes first (note: calls `parse_args()`)
        _Script.pre_run(self)

        ## consistency checks
        if self.params.max_running < 0:
            raise cli.app.Error("Argument to option -J/--max-running must be a non-negative integer.")
        if self.params.wait < 0: 
            raise cli.app.Error("Argument to option -C/--continuous must be a positive integer.")

        n = self.params.wctime.count(":")
        if 0 == n: # wctime expressed in hours
            duration = int(self.params.wctime)*60*60
            if duration < 1:
                raise cli.app.Error("Argument to option -w/--wall-clock-time must be a positive integer.")
            self.params.wctime = duration
        elif 1 == n: # wctime expressed as 'HH:MM'
            hrs, mins = self.params.wctime.split(":")
            self.params.wctime = hrs*60*60 + mins*60
        elif 2 == n: # wctime expressed as 'HH:MM:SS'
            hrs, mins, secs = self.params.wctime.split(":")
            self.params.wctime = hrs*60*60 + mins*60 + secs
        else:
            raise cli.app.Error("Argument to option -w/--wall-clock-time must have the form 'HH:MM' or be a duration expressed in hours.")
        self.params.walltime = int(self.params.wctime) / 3600

        ## determine the session file name (and possibly create an empty index)
        if ( os.path.exists(self.params.session)
             and os.path.isdir(self.params.session) ):
            self.session_dirname = os.path.realpath(self.params.session)
            self.session_filename = os.path.join(self.session_dirname, 'index.csv')
        else:
            if self.params.session.endswith('.jobs'):
                self.params.session = self.params.session[:-5]
            elif self.params.session.endswith('.csv'):
                self.params.session = self.params.session[:-4]
            self.session_dirname = self.params.session + '.jobs'
            self.session_filename = self.params.session + '.csv'

        # XXX: ARClib errors out if the download directory already exists, so
        # we need to make sure that each job downloads results in a new one.
        # The easiest way to do so is to append 'NAME' to the `output_dir`
        # (if it's not already there).
        if not 'NAME' in self.params.output:
            self.params.output = os.path.join(self.params.output, 'NAME')

        ## parse the `states` list
        self.params.states = self.params.states.split(',')
    
    
    ##
    ## INTERNAL METHODS
    ##
    ## The following methods are for internal use; they can be
    ## overridden and customized in derived classes, although there
    ## should be no need to do so.
    ##

    def _main(self, *args):
        """
        Implementation of the main logic in the `SessionBasedScript`.

        This is a template method, that you should not override in derived
        classes: rather use the provided customization hooks:
        :meth:`process_args`, :meth:`parse_args`, :meth:`setup_args`. 
        """

        ## create a `Persistence` instance to _save_session/_load_session jobs
        self.store = gc3libs.persistence.FilesystemStore(
            self.session_dirname, 
            idfactory=gc3libs.persistence.JobIdFactory()
            )

        ## load the session index file
        try:
            if os.path.exists(self.session_filename) and not self.params.new_session:
                session_file = file(self.session_filename, "r+b")
            else:
                session_file = file(self.session_filename, "w+b")
        except IOError, ex:
            self.log.critical("Cannot open session file '%s' in read+write mode: %s. Aborting."
                              % (self.params.session, str(ex)))
            return 1
        self._load_session(session_file, self.store)
        session_file.close()

        ## update session based on comman-line args
        self.process_args()

        # save the session list immediately, so newly added jobs will
        # be in it if the script is stopped here
        self._save_session(self.store)

        # obey the ``-r`` command-line option
        if self.params.resource_name:
            self._select_resources(self.params.resource_name)
            self.log.info("Retained only resources: %s (restricted by command-line option '-r %s')",
                          str.join(",", [res['name'] for res in self._core._resources]),
                          self.params.resource_name)

        ## create an `Engine` instance to manage the job list
        controller = self.make_task_controller()

        ## The main loop of the application: it is a local function so
        ## that we can call it just once or properly loop around it,
        ## as directed by the `self.params.wait` option.
        def loop():
            # advance all jobs
            controller.progress()
            # print results to user
            print ("Status of jobs in the '%s' session: (at %s)" 
                   % (os.path.basename(self.params.session),
                      time.strftime('%X, %x')))
            # summary
            stats = controller.stats(self.stats_only_for)
            total = stats['total']
            if total > 0:
                self.print_summary_table(sys.stdout, stats)
                # details table, as per ``-l`` option
                if self.params.states:
                    self.print_tasks_table(sys.stdout, self.params.states)
            else:
                if self.params.session is not None:
                    print ("  There are no tasks in session '%s'."
                           % self.params.session)
                else:
                    print ("  No tasks in this session.")
            # compute exitcode based on the running status of jobs
            rc = 0
            if stats['failed'] > 0:
                rc |= 2
            if stats[gc3libs.Run.State.RUNNING] > 0 or stats[gc3libs.Run.State.SUBMITTED] > 0:
                rc |= 4
            if stats[gc3libs.Run.State.NEW] > 0:
                rc |= 8
            return rc

        # ...now do a first round of submit/update/retrieve
        rc = loop()
        if self.params.wait > 0:
            self.log.info("sleeping for %d seconds..." % self.params.wait)
            try:
                while rc > 3:
                    # Python scripts become unresponsive during `time.sleep()`,
                    # so we just do the wait in small steps, to allow the interpreter
                    # to process interrupts in the breaks.  Ugly, but works...
                    for x in xrange(self.params.wait):
                        time.sleep(1)
                    rc = loop()
            except KeyboardInterrupt: # gracefully intercept Ctrl+C
                pass
        # save the session again before exiting, so the file reflects
        # jobs' statuses
        self._save_session()
        return rc


    def _load_session(self, session_file, store):
        """
        Load all jobs from a previously-saved session file into `self.tasks`.
        The `session_file` argument can be any file-like object suitable
        for passing to Python's stdlib `csv.DictReader`.
        """
        for row in csv.DictReader(session_file,
                                  ['jobname', 'persistent_id', 'state', 'info']):
            row['jobname'] = row['jobname'].strip()
            row['persistent_id'] = row['persistent_id'].strip()
            if (row['jobname'] == '' or row['persistent_id'] == ''):
                # invalid row, skip
                continue 
            # resurrect saved state
            task = store.load(row['persistent_id'])
            # append to this list
            self.tasks.append(task)


    def _save_session(self, store=None):
        """
        Save tasks into a given session file.  The `session`
        argument can be any file-like object suitable for passing to
        Python's standard library `csv.DictWriter`.

        If `store` is different from the default `None`, then each job
        in the session is also saved to it.
        """
        try:
            session_file = file(self.session_filename, "wb")
            for task in self.tasks:
                if store is not None:
                    store.save(task)
                csv.DictWriter(session_file, 
                               ['jobname', 'persistent_id', 'state', 'info'], 
                               extrasaction='ignore').writerow(task)
            session_file.close()
        except IOError, ex:
            self.log.error("Cannot save job list to session file '%s': %s"
                           % (self.params.session, str(ex)))


    def _search_for_input_files(self, paths):
        """
        Recursively scan each location in list `paths` for files
        matching the `self.input_filename_pattern` glob pattern, and
        return the set of path names to such files.
        """
        inputs = set()

        pattern = self.input_filename_pattern
        # special case for '*.ext' patterns
        ext = None
        if pattern.startswith('*.'):
            ext = pattern[1:]
            # re-check for more wildcard characters
            if '*' in ext or '?' in ext or '[' in ext:
                ext = None
        #self.log.debug("Input files must match glob pattern '%s' or extension '%s'"
        #               % (pattern, ext))

        def matches(name):
            return (fnmatch.fnmatch(os.path.basename(name), pattern)
                    or fnmatch.fnmatch(name, pattern))
        for path in paths:
            self.log.debug("Now processing input path '%s' ..." % path)
            if os.path.isdir(path):
                # recursively scan for input files
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        if matches(filename):
                            self.log.debug("Path '%s' matches pattern '%s',"
                                           " adding it to input list"
                                           % (os.path.join(dirpath, filename),
                                              pattern))
                            inputs.add(os.path.join(dirpath, filename))
            elif matches(path) and os.path.exists(path):
                self.log.debug("Path '%s' matches pattern '%s',"
                               " adding it to input list" % (path, pattern))
                inputs.add(path)
            elif ext is not None and not path.endswith(ext) and os.path.exists(path + ext):
                self.log.debug("Path '%s' matched extension '%s',"
                               " adding to input list"
                               % (path + ext, ext))
                inputs.add(os.path.realpath(path + ext))
            else:
                self.log.error("Cannot access input path '%s' - ignoring it.", path)
            #self.log.debug("Gathered input files: '%s'" % str.join("', '", inputs))

        return inputs

