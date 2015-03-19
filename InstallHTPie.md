# HTPie installation instructions #

It is recommended that you develop and run under a [Python Virtualenv](http://pypi.python.org/pypi/virtualenv) environment.

It is recommended that you use python version 2.6, although it should work on 2.5 and 2.7 as well.

  * Download the code from the svn
  * Manually install the [Graphviz](http://www.graphviz.org/) library
  * mkdir ~/.htpie and cp etc/htpie.conf.example ~/.htpie/htpie.conf
  * Run 'setup.py install' to install the software globally

## External Dependencies ##
  * Required
    * Must be installed by user
      * [Graphviz](http://www.graphviz.org/) is used to render the state machine diagrams (sudo apt-get install libgraphviz-dev)
      * Python development files (sudo apt-get install python-dev)
      * [ASE](https://wiki.fysik.dtu.dk/ase/download.html#download-and-install) Atomic simulation environment
    * Automatically installed through pypi
      * [PyGraph](http://networkx.lanl.gov/pygraphviz/) is used to generate the state machine diagrams
      * [Pyparsing](http://pyparsing.wikispaces.com/) is an easy to use text parser
      * [MongoEngine](http://mongoengine.org/) used to interface to the database (this should include at least pymongo 1.8)
      * [argparse](http://code.google.com/p/argparse/) command line paring library
      * [ConcurrentLogHandler](http://pypi.python.org/pypi/ConcurrentLogHandler) multi-thread safe filelogger
      * [numpy](http://numpy.scipy.org/) is used for numerics. It doesn't always install through pypi well, you might have to manually install it (sudo apt-get install python-numpy)

## Config file ##

You must have a config file in ~/.htpie/htpie.conf which identifies your MongoDB username, database name, ip, and port.  For example:

```
cat ~/.htpie/htpie.conf

[SETTINGS]
database_user=bob
database_name=bob
database_uri=127.0.0.1
database_port=27017
verbosity=10
```


# Notes #

  * create instructions on how to create a virtualenv for your own personal testing environment.  no system-level anything should be needed.
  * monbodb is bound to an ip, so in your config file you need specifiy the same IP that is in mongodb.conf (check later: is it possible to have multiple ips, wildcards, or non-ip hostnames)
  * configfile: security is not really handled right now.  if you want different users to have access to the same mongodb instance, each should great their own database
  * currently user needs ~/gc3\_jobs folder (we can fix this later)
  * testing that it works: run 'htpie task gbig', then 'htpie gtaskscheduler'.  output should look something like this:

```
$ htpie task gbig
Successfully create GBig 4cd3f4c8b14e7223ca00001e
$ htpie gtaskscheduler
Acquired lock: </home/mpackard/.htpie/gtaskscheduler.lock 9176@ocikbgtw>
2010-11-05 13:13:10,027 - htpie - INFO - 0 GHessian task(s) are going to be processed
2010-11-05 13:13:10,204 - htpie - INFO - 1 GBig task(s) are going to be processed
2010-11-05 13:13:10,225 - htpie - DEBUG - GBigStateMachine is processing 4cd3f4c8b14e7223ca00001e STATE_READY
2010-11-05 13:13:10,252 - htpie - INFO - 10 GLittle task(s) are going to be processed
2010-11-05 13:13:10,254 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca000002 STATE_READY
2010-11-05 13:13:10,259 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca000005 STATE_READY
2010-11-05 13:13:10,263 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca000008 STATE_READY
2010-11-05 13:13:10,268 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca00000b STATE_READY
2010-11-05 13:13:10,273 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca00000e STATE_READY
2010-11-05 13:13:10,278 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca000011 STATE_READY
2010-11-05 13:13:10,283 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca000014 STATE_READY
2010-11-05 13:13:10,288 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca000017 STATE_READY
2010-11-05 13:13:10,292 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca00001a STATE_READY
2010-11-05 13:13:10,297 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f4c8b14e7223ca00001d STATE_READY
2010-11-05 13:13:10,302 - htpie - INFO - 0 GSingle task(s) are going to be processed
2010-11-05 13:13:10,303 - htpie - INFO - 0 GHessianTest task(s) are going to be processed
2010-11-05 13:13:10,304 - htpie - INFO - 0 GString task(s) are going to be processed
2010-11-05 13:13:10,304 - htpie - INFO - TaskScheduler has processed 11 task(s)
--------------------------------------------------------------------------------
Released lock: </home/mpackard/.htpie/gtaskscheduler.lock 9176@ocikbgtw>
```