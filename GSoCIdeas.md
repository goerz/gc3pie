# Introduction #

This is a short list of ideas on how you could contribute code to
GC3Pie during [Google's Summer of Code 2013.](http://www.google-melange.com/gsoc/homepage/google/gsoc2013)
We welcome ideas and suggestions not listed here; please read section _Contact us_ below.




## Prerequisites ##

GC3Pie is a Python framework, using object orientation from the
grounds up.  Therefore, to be able to successfully hack your way
through GC3Pie, you need to:

  * be fluent the [Python programming language](http://www.python.org),
  * be at ease with object-oriented programming,
  * read and write [idiomatic python](http://python.net/~goodger/projects/pycon/2007/idiomatic/handout.html)
  * be familiar with SVN or Git
  * agree to the [coding conventions of GC3Pie](http://gc3pie.readthedocs.org/en/latest/developers/contributing.html)


## Contact us ##

Still got questions? Feel free to send an email to the GC3Pie users
mailing list [gc3pie@googlegroups.com](https://groups.google.com/forum/?fromgroups#!forum/gc3pie)
or to the GC3Pie development mailing list
[gc3pie-dev@googlegroups.com](https://groups.google.com/forum/?fromgroups#!forum/gc3pie-dev).



# Project Ideas #

## Make GC3Pie a replacement for Python's `subprocess`, `futures`, and the like ##

GC3Pie is -in essence- a supercharged `subprocess` module.  However,
its API would need some changes to be used as an (almost) drop-in
replacement for Python's standard module `subprocess`.  Your task
would be to make the discuss the necessary API modifications with the
[development team](https://groups.google.com/forum/?fromgroups#!forum/gc3pie-dev) and implement
them, complete with tests.

Resolution of the following
[To-Do items](http://code.google.com/p/gc3pie/issues/list) would
constitute the bulk of this project:

  * [The `Application` constructor should be source-compatible with `subprocess.Popen`](https://code.google.com/p/gc3pie/issues/detail?id=295)
  * [Implement Python's futures interface](https://code.google.com/p/gc3pie/issues/detail?id=200)
  * [Allow execution of generic Python callables, not just external commands](https://code.google.com/p/gc3pie/issues/detail?id=323)


## Visualization and statistics support for GC3Pie sessions ##

GC3Pie sessions already contain quite a lot of interesting
information: e.g., job start and end times, success ratio, etc.
A welcome addition to GC3Pie would be a module that allows analyzing
and plotting such data.

At a minimum, we would need the kind of plots that the R package
[cloudUtil](http://cran.r-project.org/web/packages/cloudUtil/index.html)
can generate, although more sophisticated analyses are
possible.

Your task would be to implement such a module and an command-line
frontend for it, e.g. using [matplotlib](http://matplotlib.org/).


## Reliability-based scheduling in GC3Pie ##

The default scheduler in GC3Pie is rather basic: it just ranks compute
resources according to capacity (the `free_slots` parameter) and
submits to the one with larger capacity. Although `Application`
classes could replace it to implement custom scheduling policies, none
does.

Your task would be to implement a new default scheduler, that weighs
resources using reliability and turnaround time statistics to achieve
faster execution of jobs and reduce the number of failed jobs.

Ask on the [https://groups.google.com/forum/?fromgroups#!forum/gc3pie-dev developers mailing
list] for more details.


## Integrate GC3Pie into the IPython notebook ##

The [IPython Notebook](http://ipython.org/notebook.html) is a web
application that provides a versatile environment for data analysis
and exploratory scientific programming.  We foresee two ways in which
GC3Pie couldfruitfully interoperate with IPython; they could actually
be executed as separate GSoC projects.

### Enhanced representation of GC3Pie task classes ###

IPython provides a formatter protocol for Python objects to specify
how to render themselves as different MIME types.  You would have to
write formatters for GC3Pie `Task` objects (and, specifically, for the
`*TaskCollection` objects, which are the building blocks for
workflows), that provide a summary representation of the execution
state.  For instance, the text representation of a `TaskCollection`
should report on how many tasks are completed (how many ok/failed),
how many are still pending and how many are running; a graphical
representation could use colored bars to represent the same
information.

### GC3Pie as an IPython execution engine ###

IPython already has the ability to execute Python code on remote
servers.  This ability is however quite primitive compared to what
GC3Pie can do (access to remote execution facilities,
checkpoint/restart, on-demand spawning of virtual machines).  Your
task would be to write an IPython execution backend that uses GC3Pie
to dispatch work to remote computational facilities.


### Warning: additional requisites ###

This project requires you to gain confidence (and eventually do actual
work) on two separate code bases:
[GC3Pie](http://code.google.com/p/gc3pie/source/browse) and
[IPython](http://github.com/ipython/ipython).  This means interacting
with two communities and adapting your code to different writing
styles.  On the other hand, you could earn double glory and popularity
:-)


## Got an idea? We're glad to listen! ##

We welcome ideas and suggestions for other ways of improving GC3Pie!
We are especially interested in ideas and projects that allow GC3Pie
to better interoperate with other scientific software (be it
Python-based or not).  Please [https://groups.google.com/forum/?fromgroups#!forum/gc3pie-dev
contact us]: we're happy to discuss!