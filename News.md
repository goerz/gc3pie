This page summarizes the user-visible changes from
one release of GC3Pie to another.
Read carefully before upgrading!


# Released GC3Pie #

## 1.0 ##

### Configuration file changes ###

  * Renamed configuration file to `gc3pie.conf`: the file `gc3utils.conf` will no longer be read!
  * SGE clusters must now have `type = sge` in the configuration file (instead of `type = ssh-sge`)
  * All computational resource must have an `architecture = ...` line; see the ConfigurationFile wiki page for details
  * Probably more changes than it's worth to list here: check your configuration against the ConfigurationFile wiki page!

### Command-line utilities changes ###

  * GC3Utils and GC3Apps (grosetta/ggamess/etc.) now all accept a `-s`/`--session` option for locating the job storage directory: this allows grouping jobs into folders instead of shoveling them all into `~/.gc3/jobs`.
  * GC3Apps: replaced option `-t`/`--table` with `-l`/`--states`.  The new option prints a table of submitted jobs in addition to the summary stats; if a comma-separated list of job states follows the option, only job in those states are printed.
  * Command `gstat` will now print a summary of the job states if the list is too long to fit on screen; use the `-v` option to get the full job listing regardless of its length.
  * Command `gstat` can now print information on jobs in a certain state only; see help text for option `--state`
  * Removed `-l` option from `ginfo`; use `-v` instead.
  * GC3Utils: all commands accepting multiple job IDs on the command line, now exit with the number of errors/failures occurred.  Since exit codes are practically limited to 7 bits, exit code 126 means that more than 125 failures happened.


## 0.10 ##

  * First release for public use outside of GC3


# In-development code #

### Configuration file changes ###

  * The `architecture` value is now required for every resource.