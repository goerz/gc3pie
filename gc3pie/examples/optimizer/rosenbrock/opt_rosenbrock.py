#! /usr/bin/env python
#
"""
  Minimal example to illustrate global optimization using gc3pie.

  This example is meant as a starting point for other optimizations
  within the gc3pie framework.
"""

# Copyright (C) 2011, 2012 University of Zurich. All rights reserved.
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
__author__ = 'Benjamin Jonen <benjamin.jonen@bf.uzh.ch>'
# summary of user-visible changes
__changelog__ = """

"""
__docformat__ = 'reStructuredText'

import os
import sys
import sys
import gc3libs
import time
from gc3libs import Application
from gc3libs.cmdline import SessionBasedScript
from gc3libs.optimizer.support_gc3 import update_parameter_in_file

# optimizer specific imports
from gc3libs.optimizer.global_opt import GlobalOptimizer
from gc3libs.optimizer.dif_evolution import DifferentialEvolution

float_fmt = '%25.15f'

optimization_dir = os.path.join(os.getcwd(), 'optimizeRosenBrock')
pop_size = 100
def nlc(x):
    import numpy as np
    return np.array([ 1 ] * pop_size)

def task_constructor_rosenbrock(x_vals, iteration_directory, **extra_args):
    """
    Given solver guess `x_vals`, return an instance of :class:`Application`
    set up to produce the output :def:`target_fun` of :class:`GlobalOptimizer`
    analyzes to produce the corresponding function values.
    """
    import shutil

    # Set some initial variables
    path_to_rosenbrock_example = os.getcwd()
    path_to_executable = os.path.join(path_to_rosenbrock_example, 'bin/rosenbrock')
    base_dir = os.path.join(path_to_rosenbrock_example, 'base')

    x_vars = ['x1', 'x2']
    para_files = ['parameters.in', 'parameters.in']
    para_file_formats = ['space-separated', 'space-separated']
    index = 0 # We are dealing with scalar inputs

    jobname = 'para_' + '_'.join(['%s=' % var + ('%25.15f' % val).strip() for (var, val) in zip(x_vars, x_vals)])
    path_to_stage_dir = os.path.join(optimization_dir, iteration_directory, jobname)

    executable = os.path.basename(path_to_executable)
    # start the inputs dictionary with syntax: client_path: server_path
    inputs = { path_to_executable:executable }
    path_to_stage_base_dir = os.path.join(path_to_stage_dir, 'base')
    shutil.copytree(base_dir, path_to_stage_base_dir, ignore=shutil.ignore_patterns('.svn'))
    for var, val, para_file, para_file_format in zip(x_vars, x_vals, para_files, para_file_formats):
        val = (float_fmt % val).strip()
        update_parameter_in_file(os.path.join(path_to_stage_base_dir, para_file),
                                 var, index, val, para_file_format)

    prefix_len = len(path_to_stage_base_dir) + 1
    for dirpath,dirnames,filenames in os.walk(path_to_stage_base_dir):
        for filename in filenames:
            # cut the leading part, which is == to path_to_stage_base_dir
            relpath = dirpath[prefix_len:]
            # ignore output directory contents in resubmission
            if relpath.startswith('output'):
                continue
            remote_path = os.path.join(relpath, filename)
            inputs[os.path.join(dirpath, filename)] = remote_path
    # all contents of the `output` directory are to be fetched
    # outputs = { 'output/':'' }
    outputs = gc3libs.ANY_OUTPUT
    #{ '*':'' }
    #kwargs = extra.copy()
    kwargs = extra_args # e.g. architecture
    kwargs['stdout'] = executable + '.log'
    kwargs['join'] = True
    kwargs['output_dir'] =  os.path.join(path_to_stage_dir, 'output')
    gc3libs.log.debug("Output dir: %s" % kwargs['output_dir'])
    kwargs['requested_architecture'] = 'x86_64'
    kwargs['requested_cores'] = 1
    # hand over job to create
    return Application(['./' + executable], inputs, outputs, **kwargs)

def compute_target_rosenbrock(pop_task_tuple):
    '''
    Given a list of (population, task), compute and return list of target
    values.
    '''
    fxVals = []
    for (pop, task) in pop_task_tuple:
        outputDir = task.output_dir
        f = open(os.path.join(outputDir, 'rosenbrock.out'))
        line = f.readline().strip()
        fxVal = float(line)
        fxVals.append(fxVal)
    return fxVals


class RosenbrockScript(SessionBasedScript):
    """
    Execute Rosenbrock optimization.
    """

    def __init__(self):
        SessionBasedScript.__init__(
            self,
            version = '0.2',
            stats_only_for = Application
        )

    def new_tasks(self, extra):

        path_to_stage_dir = os.getcwd()

        de_solver = DifferentialEvolution(dim = 2, pop_size = pop_size, de_step_size = 0.85, prob_crossover = 1., itermax = 200,
                                          y_conv_crit = 0.1, de_strategy = 1, plotting = False, working_dir = path_to_stage_dir,
                                          lower_bds = [-2, -2], upper_bds = [2,2], x_conv_crit = None, verbosity = 'DEBUG', nlc = nlc)
        initial_pop = []
        if not initial_pop:
            de_solver.newPop = de_solver.drawInitialSample()
        else:
            de_solver.newPop = initial_pop

        # create an instance globalObt

        jobname = 'rosenbrock'
        kwargs = extra.copy()
        kwargs['path_to_stage_dir'] = optimization_dir
        kwargs['optimizer'] = de_solver
        kwargs['task_constructor'] = task_constructor_rosenbrock
        kwargs['target_fun'] = compute_target_rosenbrock

        return [GlobalOptimizer(jobname=jobname, **kwargs)]

if __name__ == '__main__':
    print 'starting'
    if os.path.isdir(optimization_dir):
        import shutil
        shutil.rmtree(optimization_dir)
    os.mkdir(optimization_dir)
    RosenbrockScript().run()
    print 'done'
