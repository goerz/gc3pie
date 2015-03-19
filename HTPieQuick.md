# Examples #



## htpie task {command} ##

### htpie task ghessian ###

```
htpie task ghessian

Successfully create GHessian 4cd965a5b14e7252cc000002
```


### htpie task gstring ###

```
htpie task gstring

Successfully create GString 4cd965e4b14e725309000002
```

### htpie task ghessiantest ###

```
htpie task ghessiantest

Successfully create GHessianTest 4cd969fab14e72549b000027
```

### htpie task gsingle ###

```
htpie task gsingle

Successfully create GSingle 4cd96a19b14e7254b6000002
```


### htpie task gbig ###

```
htpie task gbig

Successfully create GBig 4cd96a26b14e7254c500001e
```

## htpie gcontrol {command} ##

### htpie gcontrol info ###

```
htpie gcontrol info -i 4cd96443b14e72523f000002

GSingle 4cd96443b14e72523f000002 STATE_READY STATUS_PAUSED
Input file(s):
/tmp/4cd96443b14e72523f000002/inputs/water_UHF_gradient.inp
```


### htpie gcontrol query ###

```
htpie gcontrol query -i 4cd96443b14e72523f000002

2010-11-09 16:10:44,160 - htpie - ERROR - Task 4cd96443b14e72523f000002 is unknown
Traceback (most recent call last):
  File "/usr/local/bin/htpie", line 9, in <module>
    load_entry_point('htpie==0.1.00', 'console_scripts', 'htpie')()
  File "/usr/local/lib/python2.6/dist-packages/htpie-0.1.00-py2.6.egg/htpie/gcmd.py", line 185, in main
    options.func(options)
  File "/usr/local/lib/python2.6/dist-packages/htpie-0.1.00-py2.6.egg/htpie/gcmd.py", line 42, in gcontrol
    GControl.query(options.id, options.time_ago, options.long_format)
  File "/usr/local/lib/python2.6/dist-packages/htpie-0.1.00-py2.6.egg/htpie/usertasks/gcontrol.py", line 57, in query
    task_class = usertasks.fsm_classes[match(type)][0]
  File "/usr/local/lib/python2.6/dist-packages/htpie-0.1.00-py2.6.egg/htpie/usertasks/gcontrol.py", line 56, in match
    raise UnknownTaskException('Task %s is unknown'%(type))
htpie.lib.exceptions.UnknownTaskException: Task 4cd96443b14e72523f000002 is unknown
```


### htpie gcontrol retry ###

```
htpie gcontrol retry -i 4cd96443b14e72523f000002

2010-11-09 16:13:44,558 - htpie - INFO - Task 4cd96443b14e72523f000002 will be retried
```

### htpie gcontrol kill ###

```
htpie gcontrol kill -i 4cd96443b14e72523f000002

2010-11-09 16:11:22,294 - htpie - DEBUG - GSingle 4cd96443b14e72523f000002 will be killed
2010-11-09 16:11:22,294 - htpie - INFO - Task 4cd96443b14e72523f000002 will be killed
mpackard@ocikbgtw:~/tmp/htpie$ htpie gcontrol statediag -i 4cd96443b14e72523f000002
```

### htpie gcontrol statediag ###

```
htpie gcontrol statediag -i 4cd96443b14e72523f000002

Traceback (most recent call last):
  File "/usr/local/bin/htpie", line 9, in <module>
    load_entry_point('htpie==0.1.00', 'console_scripts', 'htpie')()
  File "/usr/local/lib/python2.6/dist-packages/htpie-0.1.00-py2.6.egg/htpie/gcmd.py", line 185, in main
    options.func(options)
  File "/usr/local/lib/python2.6/dist-packages/htpie-0.1.00-py2.6.egg/htpie/gcmd.py", line 46, in gcontrol
    GControl.statediag(options.id, options.long_format)
  File "/usr/local/lib/python2.6/dist-packages/htpie-0.1.00-py2.6.egg/htpie/usertasks/gcontrol.py", line 45, in statediag
    fsm = usertasks.get_fsm_match_lower(id)()
  File "/usr/local/lib/python2.6/dist-packages/htpie-0.1.00-py2.6.egg/htpie/usertasks/usertasks.py", line 23, in get_fsm_match_lower
    return lower_dict[cls_task_name][1]
KeyError: '4cd96443b14e72523f000002'
```




## htpie gtaskscheduler ##

```
htpie gtaskscheduler 


Acquired lock: </home/bob/.htpie/gtaskscheduler.lock 20972@ocikbgtw>
2010-11-09 16:06:10,255 - htpie - INFO - 0 GHessian task(s) are going to be processed
2010-11-09 16:06:10,258 - htpie - INFO - 3 GBig task(s) are going to be processed
2010-11-09 16:06:10,261 - htpie - DEBUG - GBigStateMachine is processing 4cd3f4c8b14e7223ca00001e STATE_POSTPROCESS
2010-11-09 16:06:10,281 - htpie - DEBUG - GBigStateMachine is processing 4cd9532eb14e724d4000001e STATE_WAIT
2010-11-09 16:06:10,298 - htpie - DEBUG - GBigStateMachine is processing 4cd954dbb14e724ddd00001e STATE_WAIT
2010-11-09 16:06:10,315 - htpie - INFO - 27 GLittle task(s) are going to be processed
2010-11-09 16:06:10,319 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f97fb14e722692000002 STATE_WAIT
2010-11-09 16:06:10,748 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f97fb14e722692000005 STATE_WAIT
2010-11-09 16:06:11,073 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f97fb14e72269200000e STATE_WAIT
2010-11-09 16:06:11,316 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f97fb14e722692000014 STATE_WAIT
2010-11-09 16:06:11,542 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f97fb14e722692000017 STATE_WAIT
2010-11-09 16:06:11,752 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f97fb14e72269200001a STATE_WAIT
2010-11-09 16:06:11,953 - htpie - DEBUG - GLittleStateMachine is processing 4cd3f97fb14e72269200001d STATE_WAIT
2010-11-09 16:06:12,161 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d4000001d STATE_WAIT
2010-11-09 16:06:12,207 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d4000001a STATE_WAIT
2010-11-09 16:06:12,257 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d40000017 STATE_WAIT
2010-11-09 16:06:12,313 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d40000014 STATE_WAIT
2010-11-09 16:06:12,371 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d40000011 STATE_WAIT
2010-11-09 16:06:12,429 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d4000000e STATE_WAIT
2010-11-09 16:06:12,500 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d4000000b STATE_WAIT
2010-11-09 16:06:12,541 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d40000008 STATE_WAIT
2010-11-09 16:06:12,587 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d40000005 STATE_WAIT
2010-11-09 16:06:12,630 - htpie - DEBUG - GLittleStateMachine is processing 4cd9532eb14e724d40000002 STATE_WAIT
2010-11-09 16:06:12,676 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd000002 STATE_WAIT
2010-11-09 16:06:12,701 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd000005 STATE_WAIT
2010-11-09 16:06:12,724 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd000008 STATE_WAIT
2010-11-09 16:06:12,746 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd00000b STATE_WAIT
2010-11-09 16:06:12,797 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd00000e STATE_WAIT
2010-11-09 16:06:12,824 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd000011 STATE_WAIT
2010-11-09 16:06:12,860 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd000014 STATE_WAIT
2010-11-09 16:06:12,882 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd000017 STATE_WAIT
2010-11-09 16:06:12,905 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd00001a STATE_WAIT
2010-11-09 16:06:12,930 - htpie - DEBUG - GLittleStateMachine is processing 4cd954dbb14e724ddd00001d STATE_WAIT
2010-11-09 16:06:13,061 - htpie - INFO - 0 GSingle task(s) are going to be processed
2010-11-09 16:06:13,065 - htpie - INFO - 0 GHessianTest task(s) are going to be processed
2010-11-09 16:06:13,069 - htpie - INFO - 0 GString task(s) are going to be processed
2010-11-09 16:06:13,071 - htpie - INFO - TaskScheduler has processed 30 task(s)
--------------------------------------------------------------------------------
Released lock: </home/bob/.htpie/gtaskscheduler.lock 20972@ocikbgtw>
```