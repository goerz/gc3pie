#! /usr/bin/env python
#
"""
ForwardPremium-specific methods and overloads. 
"""
# Copyright (C) 2011 University of Zurich. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
__version__ = '$Revision$'
__author__ = 'Riccardo Murri <riccardo.murri@uzh.ch>, Benjamin Jonen <benjamin.jonen@bf.uzh.ch>'
# summary of user-visible changes
__changelog__ = """

"""
__docformat__ = 'reStructuredText'


import gc3libs.debug
import re, os
import numpy as np
from supportGc3 import lower, flatten, str2tuple, getIndex, extractVal, str2vals
from supportGc3 import format_newVal, update_parameter_in_file, safe_eval, str2mat, mat2str, getParameter
from paraLoop import paraLoop

from gc3libs import Application
import shutil


class GPremiumTaskMods():
    _invalid_chars = re.compile(r'[^_a-zA-Z0-9]+', re.X)

    def terminated(self):
        """
        Analyze the retrieved output, with a threefold purpose:

        - set the exit code based on whether there is a
          `simulation.out` file containing a value for the
          `FamaFrenchBeta` parameter;

        - parse the output file `simulation.out` (if any) and set
          attributes on this object based on the values stored there:
          e.g., if the `simulation.out` file contains the line
          ``FamaFrenchBeta: 1.234567``, then set `self.FamaFrenchBeta
          = 1.234567`.  Attribute names are gotten from the labels in
          the output file by translating any invalid character
          sequence to a single `_`; e.g. ``Avg. hB`` becomes `Avg_hB`.

        - work around a bug in ARC where the output is stored in a
          subdirectory of the output directory.
        """
        output_dir = self.output_dir
        # if files are stored in `output/output/`, move them one level up
        if os.path.isdir(os.path.join(output_dir, 'output')):
            wrong_output_dir = os.path.join(output_dir, 'output')
            for entry in os.listdir(wrong_output_dir):
                dest_entry = os.path.join(output_dir, entry)
                if os.path.isdir(dest_entry):
                    # backup with numerical suffix
                    gc3libs.utils.backup(dest_entry)
                os.rename(os.path.join(wrong_output_dir, entry), dest_entry)
        # set the exitcode based on postprocessing the main output file
        simulation_out = os.path.join(output_dir, 'simulation.out')
        if os.path.exists(simulation_out):
            ofile = open(simulation_out, 'r')
            # parse each line of the `simulation.out` file,
            # and try to set an attribute with its value;
            # ignore errors - this parser is not very sophisticated!
            for line in ofile:
                if ':' in line:
                    try:
                        var, val = line.strip().split(':', 1)
                        value = float(val)
                        attr = self._invalid_chars.sub('_', var)
                        setattr(self, attr, value)
                    except:
                        pass
            ofile.close()
            if hasattr(self, 'FamaFrenchBeta'):
                self.execution.exitcode = 0
                self.info = ("FamaFrenchBeta: %.6f" % self.FamaFrenchBeta)
            elif self.execution.exitcode == 0:
                # no FamaFrenchBeta, no fun!
                self.execution.exitcode = 1
        else:
            # no `simulation.out` found, signal error
            self.execution.exitcode = 2

            
class paraLoop_fp(paraLoop):
    '''
      Adds functionality for the forwardPremium application to the general paraLoop class by adding
      1) getCtryParas
      2) fillInputDir. 
      Both functions are used to prepare the input folder sent to the grid. 
    '''
    
    def getCtryParas(self, baseDir, Ctry1, Ctry2):
        '''
          Obtain the right markov input files (markovMatrices.in, markovMoments.in 
          and markov.out) and overwrite the existing ones in the baseDir/input folder. 
        '''
        import glob
        # Find Ctry pair
        inputFolder = os.path.join(baseDir, 'input')
        outputFolder = os.path.join(baseDir, 'output')
        markov_dir = os.path.join(baseDir, 'markov')
        CtryPresetPath = os.path.join(markov_dir, 'presets', Ctry1 + '-' + Ctry2)
        filesToCopy = glob.glob(CtryPresetPath + '/*.in')
        filesToCopy.append(os.path.join(CtryPresetPath, 'markov.out'))
        for fileToCopy in filesToCopy:
            shutil.copy(fileToCopy, inputFolder)
##        if not os.path.isdir(outputFolder): 
##            os.mkdir(outputFolder)
##        shutil.copy(os.path.join(CtryPresetPath, 'markov.out'), inputFolder)
        
    def fillInputDir(self, baseDir, input_dir):
        '''
          Copy folder /input and all files in the base dir to input_dir. 
          This is slightly more involved than before because we need to 
          exclude the markov directory which contains markov information
          for all country pairs. 
        '''
        import glob
        inputFolder = os.path.join(baseDir, 'input')
        gc3libs.utils.copytree(inputFolder , os.path.join(input_dir, 'input'))
        filesToCopy = glob.glob(baseDir + '/*')
        for fileToCopy in filesToCopy:
            if os.path.isdir(fileToCopy): continue
            shutil.copy(fileToCopy, input_dir)
