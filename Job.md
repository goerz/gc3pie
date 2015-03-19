This page documents the execution model that GC3Libs' `Job` object is
meant to support, and how it is mapped onto the execution models of
supported back-ends (ARC and SGE).


# Job Execution Model #

A GC3Libs' `Job` is an abstraction of an independent asynchronous
computation, i.e., a GC3Libs' `Job` behaves much like an independent
UNIX process.  Indeed, GC3Libs' `Job` objects mimick the POSIX process
interface: `Job`s are started by a parent process, run independently of
it, and need to have their final exit code and output reaped by the
calling process.

The following table makes the correspondence between POSIX processes
and GC3Libs' `Job` objects explicit.

| **POSIX system call**  | **GC3Libs function** | **purpose**                            |
|:-----------------------|:---------------------|:---------------------------------------|
| `exec`               | `Gcli.gsub`        | start new job                        |
| `kill` _(`SIGTERM`)_ | `Gcli.gkill`       | terminate executing job              |
| `wait` _(`WNOHANG`)_ | `Gcli.gstat`       | get job status (running, terminated) |
| _N/A_                | `Gcli.gget`        | retrieve output                      |


At any given moment, a GC3Libs job is in any one of a set of
pre-defined states, listed in the table below.

| **GC3Libs' `Job` state** | **purpose**  | **can change to** |
|:-------------------------|:-------------|:------------------|
| NEW                    | Job has not yet been submitted/started (i.e., `gsub` not called) | SUBMITTED _(by `gsub`)_ |
| SUBMITTED              | Job has been sent to execution resource, `jobid` is known        | RUNNING, STOPPED |
| STOPPED                | Trap state: job needs manual intervention (either user- or sysadmin-level) to resume normal execution | TERMINATED _(by gkill)_, SUBMITTED _(by miracle)_ |
| RUNNING                | Job is executing on remote resource | TERMINATED |
| TERMINATED             | Job execution is finished (correctly or not) and will not be resumed | _N/A_ |

A job that is not in the `NEW` or `TERMINATED` state is said to be a
"live" job.

![http://gc3pie.googlecode.com/svn/wiki/GC3Libs_Job_states.png](http://gc3pie.googlecode.com/svn/wiki/GC3Libs_Job_states.png)

When a `Job` object is first created, it is assigned the state `NEW`.

After a _successful_ invocation of `Gcli.gsub()`, the `Job` object is
transitioned to state `SUBMITTED` and assigned a `jobid` attribute,
which uniquely identifies this `Job` object among all submitted jobs.
The `jobid` can be used to refer to the submitted job and operate on
it across multiple processes, or different invocations of the same
program.  Compare this with the POSIX PID, which can be used to
uniquely refer to a process (after a successful call to
`fork()`/`exec()`); unlike PIDs, the `jobid` will never be recycled.

Further transitions to `RUNNING` or `STOPPED` or `TERMINATED` state,
happen completely independently of the creator program.  The
`Gcli.gstat()` call provides updates on the status of a job.
(Somewhat like the POSIX `wait(..., WNOHANG)` system call, except that
GC3Libs provide explicit `RUNNING` and `STOPPED` states, instead of
encoding them into the return value.)

The `STOPPED` state is a kind of generic "run time error" state: a job
can get into the `STOPPED` state if its execution is stopped (e.g., a
SIGSTOP is sent to the remote process) or delayed indefinitely (e.g.,
the remote batch system puts the job "on hold").  _There is no way a
job can get out of the `STOPPED` state by itself:_ all transitions
from the `STOPPED` state require manual intervention, either by the
submitting user (e.g., cancel the job), or by the remote systems
administrator (e.g., by releasing the hold).

The `TERMINATED` state is the final state of a job: once a job reaches
it, it cannot get back to any other state.  Jobs reach `TERMINATED`
state regardless of their exit code, or even if a system failure
occurred during remote execution; actually, jobs can reach the
`TERMINATED` status even if they didn't run at all!  Just like POSIX
encodes process termination information in the "return code", the
GC3Libs encode information about abnormal process termination using a
set of pseudo-signal codes in a job's `returncode` attribute: i.e., if
termination of a job is due to some gird/batch system/middleware
error, the job's `os.WIFSIGNALED(job.returncode)` will be `True` and
the signal code (as gotten from `os.WTERMSIG(job.returncode)`) will be
one of the following:

| **signal** | **error condition**                     |
|:-----------|:----------------------------------------|
| 125      | submission to batch system failed     |
| 124      | remote error (e.g., execution node crashed, batch system misconfigured) |
| 123      | data staging failure                  |
| 122      | job killed by batch system / sysadmin |
| 121      | job canceled by user                  |

In addition, each GC3Libs' `Job` object in `TERMINATED` state is guaranteed to have
these additional attributes:

  * `output_retrieved`: boolean flag, indicating whether job output has been fetched from the remote resource; use the `Gcli.gget()` function to retrieve the output. (_Note:_ for jobs in `TERMINATED` state, the output can be retrieved only _once_!)
  * ...



## Mapping to the ARC execution model ##

The ARC Grid Manager uses several different states, indicating the
interaction between the Grid Manager itself and various front-end and
back-end components (e.g., !GridFTP, batch system) in great detail.
The mapping to the GC3Libs' `Job` states is, however, quite
straightforward:

| **ARC GM status**                         | **GC3Libs' `Job` state** |
|:------------------------------------------|:-------------------------|
| ACCEPTING PREPARING SUBMITTING INLRMS:Q | SUBMITTED              |
| INLRMS:R INLRMS:X EXECUTED              | RUNNING                |
| INLRMS:S INLRMS:H                       | STOPPED                |
| FINISHED FAILED                         | TERMINATED             |


## Mapping to the SGE execution model ##

Refer to the ```qstat(1)``` man page for an explanation of the various SGE
job status letters.

| **SGE `qstat` code** | **GC3Libs' `Job` status** |
|:---------------------|:--------------------------|
| `qw`               | `SUBMITTED`             |
| `qh` `s` `S` `T`   | `STOPPED`               |
| `r` `R` `t`        | `RUNNING`               |
| `E` _(or no job)_  | `TERMINATED`            |

Note that SGE's **`qstat`** command will display no output in case a job
has finished running; the only way to tell if a job has finished (and
get information about its termination status, e.g., the exit code) is
to run **`qacct`**.