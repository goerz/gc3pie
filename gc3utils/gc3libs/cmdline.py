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

There are two base classes provided here:

:py:class:`OneShotScript`
  Base class for GC3Utils commands: provides just the minimal setup
  needed for using GC3Libs and common command-line options.
  
:py:class:`SessionBasedScript`
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
import logging
import operator
import os
import os.path
from optparse import OptionParser
import re
import sys
import random
from texttable import Texttable
import time


## interface to Gc3libs

import gc3libs
import gc3libs.core
import gc3libs.Default
import gc3libs.persistence
import gc3libs.utils



## parse command-line

class SessionBasedScript(cli.app.CommandLineApp):
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
    :py:method:`process_args()` method.

    Then, new jobs are added to the session, based on the results of
    the `process_args()` method above.  For each tuple of items
    returned by `process_args()`, an instance of class
    `self.application` (which you can set by a keyword argument to the
    ctor) is created, passing it the tuple as init args, and added to
    the session.

    The script finally proceeds to updating the status of all jobs in
    the session, submitting new ones and retrieving output as needed.
    When all jobs are done, the method :py:method:`done()` is called, 
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
        done in `parse_args`:method:
        """
        self.add_param('args', nargs='*', metavar='INPUT', 
                       help="Path to input file or directory."
                       " Directories are recursively scanned for input files"
                       " matching the glob pattern '%s'" 
                       % self.input_filename_pattern)
                       
    def setup_options(self):
        """
        Override this method to add command-line options, or
        modify the standard ones.
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


    def process_args(self, extra):
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

        This method is called by the default `_main`, passing
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

        def matches(name):
            return fnmatch.fnmatch(name, pattern)
        for path in self.params.args:
            self.log.debug("Now processing input argument '%s' ..." % path)
            if os.path.isdir(path):
                # recursively scan for input files
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        if matches(filename):
                            inputs.add(os.path.join(dirpath, filename))
            elif matches(path) and os.path.exists(path):
                inputs.add(path)
            elif ext is not None and not path.endswith(ext) and os.path.exists(path + ext):
                inputs.add(os.path.realpath(path + ext))
            else:
                self.log.error("Cannot access input path '%s' - ignoring it.", path)
            self.log.debug("Gathered input files: '%s'" % str.join("', '", inputs))

        def filename_sans(path):
            # return base name without the extension
            return os.path.splitext(os.path.basename(path))[0]
        for path in inputs:
            if self.instances_per_file > 1:
                for seqno in range(1, 1+self.instances_per_file, self.instances_per_job):
                    if self.instances_per_job > 1:
                        yield ("%s.%d--%s" % (filename_sans(path), seqno, 
                                              min(seqno + self.instances_per_job - 1,
                                                  self.instances_per_file)),
                               self.application, [path], extra.copy())
                    else:
                        yield ("%s.%d" % (filename_sans(path), seqno),
                               self.application, [path], extra.copy())
            else:
                yield (filename_sans(path), self.application, [path], extra.copy())


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
        """
        self.tasks = [ ]
        self.instances_per_file = 1
        self.instances_per_job = 1
        self.extra = { } #: extra kw arguments passed to `parse_args`
        # use bogus values that should point ppl to the right place
        self.input_filename_pattern = 'PLEASE SET `input_filename_pattern` IN `SessionBasedScript` CONSTRUCTOR'
        def _unset_application_cls(*args, **kwargs):
            raise Error("PLEASE SET `application` in `SessionBasedScript` CONSTRUCTOR")
        self.application = _unset_application_cls
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
        cli.app.CommandLineApp.__init__(
            self,
            main=self._main,
            name=os.path.basename(sys.argv[0]),
            **kw
            )
        
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

        GC3Libs scripts should probably override `setup_args`:method: 
        to modify command-line parsing.
        """
        ## setup of base classes
        cli.app.CommandLineApp.setup(self)

        ## add own "standard options"
        
        # 1. job requirements
        self.add_param("-c", "--cpu-cores", dest="ncores", type=int, default=1, # 1 core
                           metavar="NUM",
                           help="Require the specified number of CPU cores (default: %(default)s)"
                           " for each CODEML job. NUM must be a whole number."
                           )
        self.add_param("-m", "--memory-per-core", dest="memory_per_core", type=int, default=2, # 2 GB
                           metavar="GIGABYTES",
                           help="Require that at least GIGABYTES (a whole number)"
                                " are available to each execution core. (Default: %(default)s)")
        self.add_param("-r", "--resource", action="store", dest="resource_name", metavar="STRING",
                           default=None, help='Select resource destination')
        self.add_param("-w", "--wall-clock-time", dest="wctime", default=str(8), # 8 hrs
                           metavar="DURATION",
                           help="Each CODEML job will run for at most DURATION time"
                           " (default: %(default)s hours), after which it"
                           " will be killed and considered failed. DURATION can be a whole"
                           " number, expressing duration in hours, or a string of the form HH:MM,"
                           " specifying that a job can last at most HH hours and MM minutes."
                           )

        # 2. session control
        self.add_param("-s", "--session", dest="session", 
                           default=os.path.join(os.getcwd(), self.name + '.csv'),
                           metavar="FILE",
                           help="Use FILE to store the index of running jobs (default: '%(default)s')."
                           " Any input files specified on the command line will be added to the existing"
                           " session.  Any jobs already in the session will be monitored and"
                           " their output will be fetched if the jobs are done."
                           )
        self.add_param("-N", "--new-session", dest="new_session", action="store_true", default=False,
                           help="Discard any information saved in the session file (see '--session' option)"
                           " and start a new session afresh.  Any information about previous jobs is lost.")

        # 3. script execution control
        self.add_param("-C", "--continuous", type=int, dest="wait", default=0,
                           metavar="INTERVAL",
                           help="Keep running, monitoring jobs and possibly submitting new ones or"
                           " fetching results every INTERVAL seconds. Exit when all jobs are finished."
                           )
        self.add_param("-J", "--max-running", type=int, dest="max_running", default=50,
                           metavar="NUM",
                           help="Allow no more than NUM concurrent jobs (default: %(default)s)"
                           " to be in SUBMITTED or RUNNING state."
                           )
        self.add_param("-o", "--output", dest="output", default=os.getcwd(),
                           metavar='DIRECTORY',
                           help="Output files from all jobs will be collected in the specified"
                           " DIRECTORY path; by default, output files are placed in the same"
                           " directory where the corresponding input file resides.  If the"
                           " destination directory does not exist, it is created."
                           " Some special strings will be substituted into DIRECTORY,"
                           " to specify an output location that varies with the submitted job:"
                           " PATH is replaced by the directory where the session file resides;"
                           " NAME is replaced by the input file name;"
                           " DATE is replaced by the submission date in ISO format (YYYY-MM-DD);"
                           " TIME is replaced by the submission time formatted as HH:MM."
                           )
        self.add_param("-t", "--table", action="store_true", dest="table", default=False,
                           help="Print table of all submitted jobs and their statuses."
                           )
        self.add_param("-v", "--verbose", action="count", dest="verbose", default=0,
                       help="Be more detailed in reporting program activity."
                       " Repeat to increase verbosity.")
        self.setup_args()
        self.setup_options()
        return


    def pre_run(self):
        """
        Perform parsing of standard command-line options and call into
        `parse_args()` to do non-optional argument processing.
        """
        ## parse command-line
        cli.app.CommandLineApp.pre_run(self)

        ## setup GC3Libs logging
        loglevel = max(1, logging.ERROR - 10 * self.params.verbose)
        gc3libs.configure_logger(loglevel, self.name)
        self.log = logging.getLogger('gc3.' + self.name)
        self.log.setLevel(loglevel)
        self.log.propagate = True

        ## consistency checks
        if self.params.max_running < 1:
            raise cli.app.Error("Argument to option -J/--max-running must be a positive integer.")
        if self.params.wait < 0: 
            raise cli.app.Error("Argument to option -C/--continuous must be a positive integer.")

        n = self.params.wctime.count(":")
        if 0 == n: # wctime expressed in hours
            duration = int(self.params.wctime)*60*60
            if duration < 1:
                raise cli.app.Error("Argument to option -w/--wall-clock-time must be a positive integer.")
            self.params.wctime = duration
        elif 1 == n: # wctime expressed as 'HH:MM'
            hrs, mins = str.split(":", self.params.wctime)
            self.params.wctime = hrs*60*60 + mins*60
        elif 2 == n: # wctime expressed as 'HH:MM:SS'
            hrs, mins, secs = str.split(":", self.params.wctime)
            self.params.wctime = hrs*60*60 + mins*60 + secs
        else:
            raise cli.app.Error("Argument to option -w/--wall-clock-time must have the form 'HH:MM' or be a duration expressed in seconds.")
        self.params.walltime = int(self.params.wctime / 3600)

        # call hook methods from derived classes
        self.parse_args()

        # XXX: ARClib errors out if the download directory already exists, so
        # we need to make sure that each job downloads results in a new one.
        # The easiest way to do so is to append 'NAME' to the `output_dir`
        # (if it's not already there).
        if not 'NAME' in self.params.output:
            self.params.output = os.path.join(self.params.output, 'NAME')


    def run(self):
        """
        Execute `cli.app.Application.run`:method: if any exception is
        raised, catch it, output an error message and then exit with
        an appropriate error code.
        """
        try:
            return cli.app.CommandLineApp.run(self)
        except Exception, ex:
            self.log.critical("%s: %s" % (ex.__class__.__name__, str(ex)), 
                              exc_info=(self.params.verbose > 2))
            if isinstance(ex, cli.app.Abort):
                sys.exit(ex.status)
            elif isinstance(ex, EnvironmentError):
                sys.exit(74) # EX_IOERR in /usr/include/sysexits.h
            else:
                # generic error exit
                sys.exit(1)


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
        :method:`process_args`, :method:`parse_args`, :method:`setup_args`. 
        """

        ## create a `Persistence` instance to _save_session/_load_session jobs
        self.store = gc3libs.persistence.FilesystemStore(idfactory=gc3libs.persistence.JobIdFactory)

        ## load the session file, or create a new empty one if not existing
        try:
            self.params.session = os.path.realpath(self.params.session)
            if os.path.exists(self.params.session) and not self.params.new_session:
                session_file = file(self.params.session, "r+b")
            else:
                session_file = file(self.params.session, "w+b")
        except IOError, ex:
            self.log.critical("Cannot open session file '%s' in read+write mode: %s. Aborting."
                              % (self.params.session, str(ex)))
            return 1
        self._load_session(session_file, self.store)
        session_file.close()

        ## build job list
        new_jobs = list(self.process_args(self.extra))
        # pre-allocate Job IDs
        if len(new_jobs) > 0:
            gc3libs.persistence.Id.reserve(len(new_jobs))

        # add new jobs to the session
        existing_job_names = set(task.jobname for task in self.tasks)
        random.seed()
        for jobname, cls, args, kwargs in new_jobs:
            self.log.debug("SessionBasedScript.main(): considering adding new job defined by:"
                           " jobname=%s cls=%s args=%s kwargs=%s"
                           % (jobname, cls, args, kwargs))
            if jobname in existing_job_names:
                continue
            kwargs.setdefault('jobname', jobname)
            kwargs.setdefault('requested_memory', self.params.memory_per_core)
            kwargs.setdefault('requested_cores', self.params.ncores)
            kwargs.setdefault('requested_walltime', self.params.walltime)
            kwargs.setdefault('output_dir',                         
                              self.params.output
                              .replace('PATH', os.path.dirname(args[0]) # XXX: assumes `args[0]` exists and is a path name!
                                       or os.getcwd())
                              .replace('NAME', jobname)
                              .replace('DATE', time.strftime('%Y-%m-%d', time.localtime(time.time())))
                              .replace('TIME', time.strftime('%H:%M', time.localtime(time.time()))))
            # create a new `Application` object
            try:
                app = cls(*args, **kwargs)
            except Exception, ex:
                self.log.error("Could not create job '%s': %s."
                               % (jobname, str(ex)))
                # XXX: should we raise an exception here?
                #raise AssertionError("Could not create job '%s': %s: %s" 
                #                     % (jobname, ex.__class__.__name__, str(ex)))
            self.tasks.append(app)

        # save the session list immediately, so newly added jobs will
        # be in it if the script is stopped here
        self._save_session(self.store)

        ## create a `Core` instance to interface with the Grid middleware
        grid = gc3libs.core.Core(*gc3libs.core.import_config(
                gc3libs.Default.CONFIG_FILE_LOCATIONS
                ))

        if self.params.resource_name:
            grid.select_resource(self.params.resource_name)
            self.log.info("Retained only resources: %s (restricted by command-line option '-r %s')",
                          str.join(",", [res['name'] for res in grid._resources]),
                          self.params.resource_name)

        ## create an `Engine` instance to manage the job list
        engine = gc3libs.core.Engine(grid, self.tasks, self.store,
                                     max_in_flight = self.params.max_running)

        ## The main loop of the application: it is a local function so
        ## that we can call it just once or properly loop around it,
        ## as directed by the `self.params.wait` option.
        def loop():
            # advance all jobs
            engine.progress()
            # print results to user
            stats = engine.stats()
            if self.params.table:
                self._print_tasks_table(sys.stdout)
            else:
                print ("Status of jobs in the '%s' session:" 
                       % os.path.basename(self.params.session))
                total = len(self.tasks)
                if total > 0:
                    table = Texttable(0) # max_width=0 => dynamically resize cells
                    table.set_deco(0)    # no decorations
                    table.set_cols_align(['r', 'c', 'c'])
                    for state in sorted(stats.keys()):
                        table.add_row([
                                state, 
                                "%d/%d" % (stats[state], total),
                                "(%.1f%%)" % (100.0 * stats[state] / total)
                                ])
                    print (table.draw())
                else:
                    print ("  No jobs in this session.")
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
            try:
                while rc > 3:
                    time.sleep(self.params.wait)
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
            session_file = file(self.params.session, "wb")
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


    def _print_tasks_table(self, output=sys.stdout):
        """
        Output a summary table to stream `output`.
        """
        if len(self.tasks) == 0:
            if self.params.session is not None:
                print ("There are no jobs in session file '%s'." % self.params.session)
            else:
                print ("There are no jobs in session file.")
        else:
            table = Texttable(0) # max_width=0 => dynamically resize cells
            table.set_deco(Texttable.HEADER) # also: .VLINES, .HLINES .BORDER
            table.header(['JobID', 'Job name', 'State', 'Info'])
            #table.set_cols_width([10, 20, 10, 35])
            table.set_cols_align(['l', 'l', 'l', 'l'])
            table.add_rows([ (task.persistent_id, task.jobname,
                              task.execution.state, task.execution.info)
                             for task in self.tasks ],
                           header=False)
            output.write(table.draw())
            output.write("\n")
