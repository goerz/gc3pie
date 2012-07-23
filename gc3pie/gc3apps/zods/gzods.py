#!/usr/bin/env python
#
#   gzods.py -- Front-end script for submitting multiple ZODS jobs
#
#   Copyright (C) 2012 GC3, University of Zurich
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
Front-end script for submitting multiple ZODS jobs.
It uses the generic `gc3libs.cmdline.SessionBasedScript` framework.

See the output of ``gzods --help`` for program usage instructions.
"""
__version__ = 'development version (SVN $Revision$)'
# summary of user-visible changes
__changelog__ = """
  2012-07-17:
    * Initial releases.
"""
__author__ = 'Lukasz Miroslaw <lukasz.miroslaw@uzh.ch>'
__docformat__ = 'reStructuredText'


if __name__ == '__main__':
        import gzods
        gzods.ZodsScript().run()


import os
import xml.dom.minidom
import gc3libs
import gc3libs.cmdline


class GzodsApp(gc3libs.Application):
    """
    This class is derived from gc3libs.Application and defines ZODS app with its input and output files.
    """
    def __init__(self, filename,**kw):
        if self.check_input(filename) is None:
                gc3libs.log.warning("Input files for ZODS app was not detected.")
                return None
        (input1, input2) = self.check_input(filename)
        input1 = os.path.abspath(input1)
        input2 = os.path.abspath(input2)
        gc3libs.log.debug("Detected input files for ZODS: %s, %s and %s.", filename, input1, input2)
        gc3libs.Application.__init__(
            self,
            tags=["APPS/CHEM/ZODS-01"],
            executable = '$MPIRUN', # mandatory
            arguments = [
                # these are arguments to `mpirun`
                "-n", kw['requested_cores'],
                # this is the real ZODS command-line
                '$ZODS_BINDIR/simulator', os.path.basename(filename),
            ],
            inputs = [filename, input1, input2],    # mandatory, inputs are files that will be copied to the site
            outputs = gc3libs.ANY_OUTPUT,                 # mandatory
            stderr = "stderr.txt",
            stdout = "stdout.txt",
            **kw)


    def terminated(self):
        filename = os.path.join(self.output_dir, self.stdout)
        gc3libs.log.debug("ZODS single job based on %s has TERMINATED", filename)
        for output in self.outputs:
                gc3libs.log.debug("Retrieved the following file from ZODS job %s", output)

# Detect the following references to external files in input.xml
#   <average_structure>
#      <file format="cif" name="californium_simple_3.cif"/>
#   </average_structure>
# <reference_intensities file_format="xml" file_name="data.xml"/>

    def check_input(self,filename):
        if not os.path.exists(filename):
            raise RuntimeError("Input file '%s' DOES NOT exists." % filename)
        basedir = os.path.dirname(filename)
        DOMTree = xml.dom.minidom.parse(filename)
        cNodes = DOMTree.childNodes
        if len(cNodes[0].getElementsByTagName('reference_intensities')) > 0 and len(cNodes[0].getElementsByTagName('average_structure')) > 0:
            data_file = cNodes[0].getElementsByTagName('reference_intensities')[0].getAttribute('file_name')
            avg_file = cNodes[0].getElementsByTagName('average_structure')[0].getElementsByTagName('file')[0].getAttribute('name')
            data_file = os.path.join(basedir,data_file)
            avg_file = os.path.join(basedir,avg_file)
            gc3libs.log.debug("%s references to the following files: %s and  %s.", filename, avg_file, data_file)
            if os.path.exists(avg_file)  == False or os.path.exists(data_file) == False:
                gc3libs.log.warning("Averaged structure file %s or reference intensities file %s DO NOT exist.", avg_file, data_file)
                raise RuntimeError("Input file '%s' DOES NOT exists." % filename)
            else:
                gc3libs.log.info(
                    "Input file '%s' references"
                    " averaged structure file '%s'"
                    " and reference intesities file '%s'.",
                    filename, avg_file, data_file)
                return (data_file, avg_file)
        else:
            raise RuntimeError("Input file '%s' is NOT a valid XML file for ZODS application." % filename)


class ZodsScript(gc3libs.cmdline.SessionBasedScript):
        """
This application runs the ZODS program on distributed resources.

Any (non-option) argument given on the command line is interpreted as
a directory name; the script scans any directories recursively for
'input*.xml' files, and submits a ZODS job for each input file found.

Job progress is monitored and, when a job is done, its output files
are retrieved back into the same directory where the input '.xml' file is.

The `-c` option allows to set the number of CPU cores for running
parallel jobs; for instance, the following will run parallel ZODS on
file `input.xml` using on 5 CPUs::

  ./gzods input.xml -c 5

        """
        version = "1.0"

        def new_tasks(self, extra):
           if self.params.args is None or len(self.params.args) == 0:
                self.log.warning(
                        "No arguments given on the command line: no new jobs are created."
                        " Existing jobs will still be managed.")
                return []
           tasks=[]
           listOfFiles = self._search_for_input_files(self.params.args, pattern="input*.xml")
           gc3libs.log.debug("List of detected input files for ZODS: %s", listOfFiles)
           for i, filename in enumerate(listOfFiles):
               filename = os.path.abspath(filename)
               tasks.append(("Zods"+str(i), GzodsApp, [filename], extra.copy()))
           return tasks
