# Examples #



## Submit Job: gsub ##

```
gsub gamess -c 8 -r example1 exam01.inp

Successfully submitted job.4; use the 'gstat' command to monitor its progress.
```


## Job Status: gstat ##

```
gstat

Job ID            Status    
===========================
job.1             COMPLETED 
job.2             COMPLETED 
job.3             FINISHED  
```

More verbose:

```
gstat -l job.3


===========================
status                FINISHED   
queue                 all.q      
resource_name         exampl1  
system_failed         0          
used_memory           1.626G     
outputs               {'exam01.out': 'exam01.out', 'exam01.dat': 'exam01.dat'} 
cpu_count             8          
stdout_filename       exam01.o6474 
exit_code             0          
job_name              exam01     
job_local_dir         /home/bob/tmp 
completion_time       2010-11-03 14:30:17 
lrms_jobid            6474       
submission_time       2010-11-03 14:30:08 
remote_ssh_folder     /home/bob/.gc3utils_jobs/lrms_job.EhVvfk9643 
unique_token          job.3      
used_walltime         7          
lrms_job_name         exam01     
used_cpu_time         0.290      
stderr_filename       exam01.o6474 
```

## Retrieve Results: gget ##

```
gget job.4

Job results successfully retrieved in '/home/bob/tmp/job.4'
```


## Check Running Job Output: gtail ##

```
gtail job.4

```


## Kill a Running Job: gkill ##

```
gkill job.4

Sent request to kill job job.4
It may take a few moments for the job to finish.
```

## Remove Job from Status List: gclean ##

```
gclean job.1

```

## Resubmit Job: gresub ##

```
gresub job.1

```