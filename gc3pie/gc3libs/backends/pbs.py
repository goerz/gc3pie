#! /usr/bin/env python
#
"""
Job control on PBS/Torque clusters (possibly connecting to the front-end via SSH).
"""
# Copyright (C) 2009-2012 GC3, University of Zurich. All rights reserved.
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
__version__ = 'development version (SVN $Revision$)'


import os
import posixpath
import random
import re
import sys
import tempfile
import time

from gc3libs.compat.collections import defaultdict

from gc3libs import log, Run
from gc3libs.backends import LRMS
import gc3libs.exceptions
import gc3libs.utils as utils # first, to_bytes
from gc3libs.utils import same_docstring_as

import transport

import batch

def count_jobs(qstat_output, whoami):
    """
    Parse PBS/Torque's ``qstat`` output (as contained in string `qstat_output`)
    and return a quadruple `(R, Q, r, q)` where:

      * `R` is the total number of running jobs in the PBS/Torque cell (from any user);
      * `Q` is the total number of queued jobs in the PBS/Torque cell (from any user);
      * `r` is the number of running jobs submitted by user `whoami`;
      * `q` is the number of queued jobs submitted by user `whoami`
    """
    total_running = 0
    total_queued = 0
    own_running = 0
    own_queued = 0
    n = 0
    _qstat_line_re = re.compile(r'^(?P<jobid>\d+)[^\d]+\s+'
                                '(?P<jobname>[^\s]+)\s+'
                                '(?P<username>[^\s]+)\s+'
                                '(?P<time_used>[^\s]+)\s+'
                                '(?P<state>[^\s]+)\s+'
                                '(?P<queue>[^\s]+)')
    for line in qstat_output.split('\n'):
        # import pdb; pdb.set_trace()
        log.info("Output line: %s" %  line)
        m = _qstat_line_re.match(line)
        if not m: continue
        if m.group('state') in ['R']:
            total_running += 1
            if m.group('username') == whoami:
                own_running += 1
        elif m.group('state') in ['Q']: 
            total_queued += 1
            if m.group('username') == whoami:
                own_queued += 1
        log.info("running: %d, queued: %d" % (total_running, total_queued))

    return (total_running, total_queued, own_running, own_queued)
        

_qsub_jobid_re = re.compile(r'(?P<jobid>\d+.*)', re.I)
_tracejob_last_re = re.compile('(?P<end_time>\d+/\d+/\d+\s+\d+:\d+:\d+)\s+.\s+Exit_status=(?P<exit_status>\d+)\s+'
                                  'resources_used.cput=(?P<used_cpu_time>[^ ]+)\s+'
                                  'resources_used.mem=(?P<mem>[^ ]+)\s+'
                                  'resources_used.vmem=(?P<used_memory>[^ ]+)\s+'
                                  'resources_used.walltime=(?P<used_walltime>[^ ]+)')
_tracejob_queued_re = re.compile('(?P<submission_time>\d+/\d+/\d+\s+\d+:\d+:\d+)\s+.\s+'
                                         'Job Queued at request of .*job name =\s*(?P<job_name>[^,]+),'
                                         '\s+queue =\s*(?P<queue>[^,]+)')


class PbsLrms(batch.BatchSystem):
    """
    Job control on PBS/Torque clusters (possibly by connecting via SSH to a submit node).
    """
    def __init__(self, resource, auths):
        """
        Create an `PbsLRMS` instance from a `Resource` object.

        For a `Resource` object `r` to be a valid `PbsLRMS` construction
        parameter, the following conditions must be met:
          * `r.type` must have value `Default.PBS_LRMS`;
          * `r.frontend` must be a string, containing the FQDN of an PBS/Torque cluster submit node;
          * `r.auth` must be a valid key to pass to `Auth.get()`.
        """
        # XXX: should these be `InternalError` instead?
        assert resource.type == gc3libs.Default.PBS_LRMS, \
            "PbsLRMS.__init__(): Failed. Resource type expected 'pbs'. Received '%s'" \
            % resource.type

        batch.BatchSystem.__init__(self, resource, auths)
        self.isValid = 1


    def _parse_submit_output(self, output):
        return self.get_jobid_from_submit_output( output,_qsub_jobid_re)
                                                 
    def _submit_command(self, app):
        qsub, script = app.pbs_qsub(self._resource)
        if 'queue' in self._resource:
            qsub += " -q %s" % self._resource['queue']
        if script is not None:
            # save script to a temporary file and submit that one instead
            script_name = '%s.%x.sh' % (app.get('application_tag', 'script'), 
                                        random.randint(0, sys.maxint))
            
        return (qsub, script, script_name)

    def _stat_command(self, job):
        return "qstat %s | grep ^%s" % (job.lrms_jobid,job.lrms_jobid)

    def _acct_command(self, job):
        return  'tracejob %s' % job.lrms_jobid
        
    def _parse_stat_output(self, stdout):
        # check that passed object obeys contract
        
        # parse `qstat` output
        job_status = stdout.split()[4]
        jobstatus = dict()
        log.debug("translating PBS/Torque's `qstat` code '%s' to gc3libs.Run.State" % job_status)
        if job_status in ['Q', 'W']:
            jobstatus['state'] = Run.State.SUBMITTED
        elif job_status in ['R']:
            jobstatus['state'] =  Run.State.RUNNING
        elif job_status in ['S', 'H', 'T'] or 'qh' in job_status:
            jobstatus['state'] = Run.State.STOPPED
        elif job_status in ['C', 'E']: 
            jobstatus['state'] = Run.State.TERMINATING 
        else:
            jobstatus['state'] = Run.State.UNKNOWN

        return jobstatus

    def _parse_acct_output(self, stdout):
        retstatus = {}
        for line in stdout.split('\n'):
            # skip empty and header lines
            if _tracejob_last_re.match(line):
                retstatus.update(_tracejob_last_re.match(line).groupdict())
            elif _tracejob_queued_re.match(line):
                retstatus.update(_tracejob_queued_re.match(line).groupdict())
        return retstatus
        
    def _cancel_command(self, jobid):
        return "qdel %s" % jobid
    
                
    @same_docstring_as(LRMS.get_resource_status)
    def get_resource_status(self):
        try:
            self.transport.connect()

            username = self._ssh_username
            log.debug("Running `qstat -a`...")
            _command = "qstat -a"
            exit_code, qstat_stdout, stderr = self.transport.execute_command(_command)

            # self.transport.close()

            log.debug("Computing updated values for total/available slots ...")
            (total_running, self._resource.queued, 
             self._resource.user_run, self._resource.user_queued) = count_jobs(qstat_stdout, username)
            self._resource.total_run = total_running
            self._resource.free_slots = -1
            self._resource.used_quota = -1

            log.info("Updated resource '%s' status:"
                     " free slots: %d,"
                     " total running: %d,"
                     " own running jobs: %d,"
                     " own queued jobs: %d,"
                     " total queued jobs: %d",
                     self._resource.name,
                     self._resource.free_slots,
                     self._resource.total_run,
                     self._resource.user_run,
                     self._resource.user_queued,
                     self._resource.queued,
                     )
            return self._resource

        except Exception, ex:
            # self.transport.close()
            log.error("Error querying remote LRMS, see debug log for details.")
            log.debug("Error querying LRMS: %s: %s",
                      ex.__class__.__name__, str(ex))
            raise


## main: run tests

if "__main__" == __name__:
    import doctest
    doctest.testmod(name="sge",
                    optionflags=doctest.NORMALIZE_WHITESPACE)
