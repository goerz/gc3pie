#! /usr/bin/env python
#
"""
Driver script for performing an global optimization over the parameter space.
This code is an adaptation of the following MATLAB code: http://www.icsi.berkeley.edu/~storn/DeMat.zip
Please refer to this web site for more information: http://www.icsi.berkeley.edu/~storn/code.html#deb1
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
__docformat__ = 'reStructuredText'


import logging
import os
import sys

import numpy as np
try:
    import matplotlib
    matplotlib.use('SVG')
    import matplotlib.pyplot as plt
    matplotLibAvailable = True
except:
    matplotLibAvailable = False

from gc3libs.optimizer import EvolutionaryAlgorithm


np.set_printoptions(linewidth = 300, precision = 8, suppress = True)

# Variable changes from matlab implementation
# I_D -> dim
# I_NP -> pop_size
# FM_popold -> pop_old
# FVr_bestmem -> best
# FVr_bestmemit -> best_cur_iter
# I_nfeval -> n_fun_evals
# I_cur_iter -> cur_iter
# F_weight -> de_step_size
# F_CR -> prob_crossover
# I_itermax -> itermax
# F_VTR -> y_conv_crit
# I_strategy -> de_strategy
# I_plotting -> plotting
# lower_bds
# upper_bds
# x_conv_crit
# verbosity
# FM_pm1 -> pm1
# FM_pm2 -> pm2 population matrix (pm)
# FM_pm3 -> pm3
# FM_pm4 -> pm4
# FM_pm5 -> pm5
# FM_bm  -> bm best member matrix
# FM_ui  -> ui ??
# FM_mui -> mui # mask for intermediate population
# FM_mpo -> mpo # mask for old population
# FVr_rot -> rot  # rotating index array (size I_NP)
# FVr_rotd -> rotd  # rotating index array (size I_D)
# FVr_rt -> rt  # another rotating index array
# FVr_rtd -> rtd # rotating index array for exponential crossover
# FVr_a1 -> a1 # index array
# FVr_a2 -> a2 # index array
# FVr_a3 -> a3 # index array
# FVr_a4 -> a4 # index array
# FVr_a5 -> a5 # index array
# FVr_ind -> ind # index pointer array


class DifferentialEvolution(EvolutionaryAlgorithm):
    '''
    Differential evolution optimizer class.

    Solver iterations can be driven externally (see for ex. gParaSearchDriver) or from within the class (self.deopt()).
    Instance needs two properties, supplied through evaluator class or set externally:
    1) Target function that takes x and generates f(x)
    2) nlc function that takes x and generates constraint function values c(x) >= 0.
    '''

    def __init__(self, dim, pop_size, de_step_size, prob_crossover, itermax,
                 x_conv_crit, y_conv_crit, de_strategy, lower_bds, upper_bds, nlc=None,
                 target_fn=None, plotting=False, working_dir=os.getcwd(), verbosity='INFO'):

        # Set up loggers
        log = logging.getLogger('gc3.gc3libs.EvolutionaryAlgorithm')
        log.setLevel(logging.DEBUG)
        log.propagate = 0
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        import gc3libs
        log_file_name = os.path.join(working_dir, 'EvolutionaryAlgorithm.log')
        file_handler = logging.FileHandler(log_file_name, mode = 'w')
        file_handler.setLevel(logging.DEBUG)
        log.addHandler(stream_handler)
        log.addHandler(file_handler)
        self.logger = log
        #self.logger.debug('in dif_evo')

        # save parameters
        self.target = target_fn
        self.dim = dim
        self.pop_size = pop_size
        self.de_step_size = de_step_size
        self.prob_crossover = prob_crossover
        self.itermax = itermax
        self.y_conv_crit = y_conv_crit
        self.de_strategy = de_strategy
        self.plotting = plotting
        self.working_dir = working_dir
        self.lower_bds = np.array(lower_bds)
        self.upper_bds = np.array(upper_bds)
        self.x_conv_crit = x_conv_crit
        self.verbosity = verbosity

        #try:
            #self.nlc       = evaluator.nlc
        #except AttributeError:
            #self.nlc = lambda x: np.array([ 1 ] * pop_size)

        if not nlc:
            self.nlc = self._default_nlc
        else:
            self.nlc = nlc

        self.matplotLibAvailable = matplotLibAvailable

        # Initialize variables that needed for state retention.
        self.pop_old  = np.zeros( (self.pop_size, self.dim) )  # toggle population
        self.best = np.zeros( self.dim )                       # best population member ever
        self.best_iter = np.zeros( self.dim )                  # best population member in iteration
        self.n_fun_evals = 0                                   # number of function evaluations

        # Check input variables
        if ( ( self.prob_crossover < 0 ) or ( self.prob_crossover > 1 ) ):
            self.prob_crossover = 0.5
            self.logger.debug('prob_crossover should be from interval [0,1]; set to default value 0.5')
        if self.pop_size < 5:
            pass
            self.logger.warning('Set pop_size >= 5 for difEvoKenPrice to work. ')

        # Fix seed for debugging
        np.random.seed(1000)

        # set initial value for iteration count
        self.cur_iter = -1

        # Create folder to save plots
        #self.figSaveFolder = os.path.join(self.working_dir, 'difEvoFigures')
        #if not os.path.exists(self.figSaveFolder):
            #os.mkdir(self.figSaveFolder)

    def _default_nlc(self, x):
        return np.array([ 1 ] * self.pop_size)


    def deopt(self):
        '''
          Perform global optimization.
        '''
        self.logger.debug('entering deopt')
        converged = False
        while not converged:
            converged = self.iterate()
        self.logger.debug('exiting ' + __name__)

    def iterate(self):
        self.cur_iter += 1
        if self.cur_iter == 0:
            self.pop = self.drawInitialSample()
            self.ui  = self.pop.copy()

        elif self.cur_iter > 0:
            # self.cur_iter += 1
            self.ui = self.modify(self.pop)
            # Check constraints and resample points to maintain population size.
            self.ui = self.enforceConstrReEvolve(self.ui)

        # EVALUATE TARGET #
        self.S_tempvals = self.target(self.ui)
        self.logger.debug('x -> f(x)')
        for x, fx in zip(self.ui, self.S_tempvals):
            self.logger.debug('%s -> %s' % (x.tolist(), fx))
        self.updatePopulation(self.ui, self.S_tempvals)
        # create output
        self.printStats()
        # make plots
        if self.plotting:
            self.plotPopulation()

        return self.has_converged()

    def has_converged(self):
        converged = False
        # Check convergence
        if self.cur_iter > self.itermax:
            converged = True
            self.logger.info('Exiting difEvo. cur_iter >self.itermax ')
        if self.S_bestval < self.y_conv_crit:
            converged = True
            self.logger.info('converged self.S_bestval < self.y_conv_crit')
        if self.populationConverged(self.pop):
            converged = True
            self.logger.info('converged self.populationConverged(self.pop)')
        return converged

    def populationConverged(self, pop):
        '''
        Check if population has converged.
        '''
        diff = np.abs(pop[:, :] - pop[0, :])
        return (diff <= self.x_conv_crit).all()


    def drawInitialSample(self):
        # Draw population
        pop = self.drawPopulation(self.pop_size, self.dim)
        # Check constraints and resample points to maintain population size.
        return self.enforceConstrResample(pop)

    def updatePopulation(self, newPop = None, newVals = None):
        self.logger.debug('entering updatePopulation')
        newPop = np.array(newPop)
        newVals = np.array(newVals)
        if self.cur_iter == 0:
            self.pop = newPop.copy()
            self.S_vals = newVals.copy()
            # Determine bestmemit and bestvalit for random draw.
            self.I_best_index = np.argmin(self.S_vals)
            self.S_bestval = self.S_vals[self.I_best_index].copy()
            self.best_iter = newPop[self.I_best_index, :].copy()
            self.best_iter = newPop[self.I_best_index, :].copy()
            self.S_bestvalit = self.S_bestval.copy()
            self.best = self.best_iter.copy()


            # for k in range(self.pop_size):                          # check the remaining members
            #   if k == 0:
            #     self.S_bestval = newVals[0].copy()                # best objective function value so far
            #     self.n_fun_evals  = self.n_fun_evals + 1
            #     self.I_best_index  = 0
            #   self.n_fun_evals  += 1
            #   if newVals[k] < self.S_bestval:
            #     self.I_best_index   = k              # save its location
            #     self.S_bestval      = newVals[k].copy()
            # self.best_iter = newPop[self.I_best_index, :].copy() # best member of current iteration
            # self.S_bestvalit   = self.S_bestval              # best value of current iteration

            # self.best = self.best_iter            # best member ever

        elif self.cur_iter > 0:

            best_index = np.argmin(newVals)
            if newVals[best_index] < self.S_bestval:
                self.S_bestval   = newVals[best_index].copy()                    # new best value
                self.best = newPop[best_index, :].copy()                 # new best parameter vector ever


            for k in range(self.pop_size):
                self.n_fun_evals  = self.n_fun_evals + 1
                if newVals[k] < self.S_vals[k]:
                    self.pop[k,:] = newPop[k, :].copy()                    # replace old vector with new one (for new iteration)
                    self.S_vals[k]   = newVals[k].copy()                      # save value in "cost array"

                    # #----we update S_bestval only in case of success to save time-----------
                    # if newVals[k] < self.S_bestval:
                    #   self.S_bestval = newVals[k].copy()                    # new best value
                    #   self.best = newPop[k,:].copy()                 # new best parameter vector ever

            self.best_iter = self.best.copy()       # freeze the best member of this iteration for the coming

        self.logger.debug('new values %s' % newVals)
        self.logger.debug('best value %s' % self.S_bestval)


                                                                                    # iteration. This is needed for some of the strategies.
        return


    def modify(self, pop):

        popold      = pop                 # save the old population
        prob_crossover           = self.prob_crossover
        de_step_size       = self.de_step_size
        pop_size           = self.pop_size
        dim            = self.dim
        best_iter  = self.best_iter
        de_strategy     = self.de_strategy

        pm1   = np.zeros( (pop_size, dim) )   # initialize population matrix 1
        pm2   = np.zeros( (pop_size, dim) )   # initialize population matrix 2
        pm3   = np.zeros( (pop_size, dim) )   # initialize population matrix 3
        pm4   = np.zeros( (pop_size, dim) )   # initialize population matrix 4
        pm5   = np.zeros( (pop_size, dim) )   # initialize population matrix 5
        bm    = np.zeros( (pop_size, dim) )   # initialize FVr_bestmember  matrix
        ui    = np.zeros( (pop_size, dim) )   # intermediate population of perturbed vectors
        mui   = np.zeros( (pop_size, dim) )   # mask for intermediate population
        mpo   = np.zeros( (pop_size, dim) )   # mask for old population
        rot  = np.arange(0, pop_size, 1)    # rotating index array (size pop_size)
        rotd = np.arange(0, dim, 1)     # rotating index array (size dim)
        rt   = np.zeros(pop_size)            # another rotating index array
        rtd  = np.zeros(dim)                 # rotating index array for exponential crossover
        a1   = np.zeros(pop_size)                # index array
        a2   = np.zeros(pop_size)                # index array
        a3   = np.zeros(pop_size)                # index array
        a4   = np.zeros(pop_size)                # index array
        a5   = np.zeros(pop_size)                # index array
        ind  = np.zeros(4)

        # BJ: Need to add +1 in definition of ind otherwise there is one zero index that leaves creates no shuffling.
        ind = np.random.permutation(4) + 1             # index pointer array.
        a1  = np.random.permutation(pop_size)              # shuffle locations of vectors
        rt  = ( rot + ind[0] ) % pop_size          # rotate indices by ind(1) positions
        a2  = a1[rt]                           # rotate vector locations
        rt  = ( rot + ind[1] ) % pop_size
        a3  = a2[rt]
        rt  = ( rot + ind[2] ) % pop_size
        a4  = a3[rt]
        rt  = ( rot + ind[3] ) % pop_size
        a5  = a4[rt]


        pm1 = popold[a1, :]             # shuffled population 1
        pm2 = popold[a2, :]             # shuffled population 2
        pm3 = popold[a3, :]             # shuffled population 3
        pm4 = popold[a4, :]             # shuffled population 4
        pm5 = popold[a5, :]             # shuffled population 5


        for k in range(pop_size):                              # population filled with the best member
            bm[k,:] = best_iter                       # of the last iteration

        mui = np.random.random_sample( (pop_size, dim ) ) < prob_crossover  # all random numbers < prob_crossover are 1, 0 otherwise

        #----Insert this if you want exponential crossover.----------------
        #mui = sort(mui')         # transpose, collect 1's in each column
        #for k  = 1:pop_size
        #  n = floor(rand*dim)
        #  if (n > 0)
        #     rtd     = rem(rotd+n,dim)
        #     mui(:,k) = mui(rtd+1,k) #rotate column k by n
        #  end
        #end
        #mui = mui'                       # transpose back
        #----End: exponential crossover------------------------------------

        mpo = mui < 0.5    # inverse mask to mui

        # de_strategy    1 --> DE/rand/1:
        #                      the classical version of DE.
        #                2 --> DE/local-to-best/1:
        #                      a version which has been used by quite a number
        #                      of scientists. Attempts a balance between robustness
        #                      and fast convergence.
        #                3 --> DE/best/1 with jitter:
        #                      taylored for small population sizes and fast convergence.
        #                      Dimensionality should not be too high.
        #                4 --> DE/rand/1 with per-vector-dither:
        #                      Classical DE with dither to become even more robust.
        #                5 --> DE/rand/1 with per-generation-dither:
        #                      Classical DE with dither to become even more robust.
        #                      Choosing de_step_size = 0.3 is a good start here.
        #                6 --> DE/rand/1 either-or-algorithm:
        #                      Alternates between differential mutation and three-point-
        #                      recombination.

        if ( de_strategy == 1 ):                             # DE/rand/1
            ui = pm3 + de_step_size * ( pm1 - pm2 )   # differential variation
            ui = popold * mpo + ui * mui       # crossover
            FM_origin = pm3
            if np.any(ui > 1.3):
                print 'below zero'
        elif (de_strategy == 2):                         # DE/local-to-best/1
            ui = popold + de_step_size * ( bm - popold ) + de_step_size * ( pm1 - pm2 )
            ui = popold * mpo + ui * mui
            FM_origin = popold
        elif (de_strategy == 3):                         # DE/best/1 with jitter
            ui = bm + ( pm1 - pm2 ) * ( (1 - 0.9999 ) * np.random.random_sample( (pop_size, dim ) ) +de_step_size )
            ui = popold * mpo + ui * mui
            FM_origin = bm
        elif (de_strategy == 4):                         # DE/rand/1 with per-vector-dither
            f1 = ( ( 1 - de_step_size ) * np.random.random_sample( (pop_size, 1 ) ) + de_step_size)
            for k in range(dim):
                pm5[:,k] = f1
            ui = pm3 + (pm1 - pm2) * pm5    # differential variation
            FM_origin = pm3
            ui = popold * mpo + ui * mui     # crossover
        elif (de_strategy == 5):                          # DE/rand/1 with per-vector-dither
            f1 = ( ( 1 - de_step_size ) * np.random.random_sample() + de_step_size )
            ui = pm3 + ( pm1 - pm2 ) * f1         # differential variation
            FM_origin = pm3
            ui = popold * mpo + ui * mui   # crossover
        else:                                              # either-or-algorithm
            if (np.random.random_sample() < 0.5):                               # Pmu = 0.5
                ui = pm3 + de_step_size * ( pm1 - pm2 )# differential variation
                FM_origin = pm3
            else:                                           # use F-K-Rule: K = 0.5(F+1)
                ui = pm3 + 0.5 * ( de_step_size + 1.0 ) * ( pm1 + pm2 - 2 * pm3 )
                ui = popold * mpo + ui * mui     # crossover

        return ui




    def printStats(self):
        pass
        self.logger.debug('Iteration: %d,  x: %s f(x): %f' %
                          (self.cur_iter, self.best, self.S_bestval))

    def plotPopulation(self, pop):
        # Plot population
        if self.dim == 2:
            x = pop[:, 0]
            y = pop[:, 1]
            if matplotLibAvailable:
                # determine bounds
                xDif = self.upper_bds[0] - self.lower_bds[0]
                yDif = self.upper_bds[1] - self.lower_bds[1]
                scaleFac = 0.3
                xmin = self.lower_bds[0] - scaleFac * xDif
                xmax = self.upper_bds[0] + scaleFac * xDif
                ymin = self.lower_bds[1] - scaleFac * yDif
                ymax = self.upper_bds[1] + scaleFac * yDif

                # make plot
                fig = plt.figure()
                ax = fig.add_subplot(111)

                ax.scatter(x, y)
                # x box constraints
                ax.plot([self.lower_bds[0], self.lower_bds[0]], [ymin, ymax])
                ax.plot([self.upper_bds[0], self.upper_bds[0]], [ymin, ymax])
                # all other linear constraints
                c_xmin = self.nlc.linearConstr(xmin)
                c_xmax = self.nlc.linearConstr(xmax)
                for ixC in range(len(c_xmin)):
                    ax.plot([xmin, xmax], [c_xmin[ixC], c_xmax[ixC]])
                ax.axis(xmin = xmin, xmax = xmax,
                        ymin = ymin, ymax = ymax)
                ax.set_xlabel('EH')
                ax.set_ylabel('sigmaH')
                ax.set_title('Best: x %s, f(x) %f' % (self.best, self.S_bestval))

                fig.savefig(os.path.join(self.figSaveFolder, 'pop%d' % (self.cur_iter)))

    def drawPopulation(self, size, dim):
        pop = np.zeros( (size, dim ) )
        for k in range(size):
            pop[k,:] = self.drawPopulationMember(dim)
        return pop

    def drawPopulationMember(self, dim):
        '''
          Draw one population member of dimension dim.
        '''
        return self.lower_bds + np.random.random_sample( dim ) * ( self.upper_bds - self.lower_bds )

    def enforceConstrResample(self, pop):
        '''
          Check that each ele satisfies fullfills all constraints. If not, then draw a new population memeber and check constraint.
        '''
        maxDrawSize = self.pop_size * 100
        dim = self.dim
        for ixEle, ele in enumerate(pop):
            constr = self.nlc(ele)
            ctr = 0
            while not sum(constr > 0) == len(constr) and ctr < maxDrawSize:
                pop[ixEle, :] = self.drawPopulationMember(dim)
                constr = self.nlc(ele)
                ctr += 1
            if ctr >= maxDrawSize:
                pass
                self.logger.debug('Couldnt sample a feasible point with {0} draws', maxDrawSize)
        return pop

    def checkConstraints(self, pop):
        '''
          Check which ele satisfies all constraints.
          cSat: Vector of length nPopulation. Each element signals whether the corresponding population member satisfies all constraints.
        '''
        cSat = np.empty( ( len(pop) ), dtype = bool)
        for ixEle, ele in enumerate(pop):
            constr = self.nlc(ele)
            cSat[ixEle] = sum(constr > 0) == len(constr)
        return cSat

    def enforceConstrReEvolve(self, pop):
        '''
          Check that each ele satisfies fullfills all constraints. If not, then draw a generate a new population memeber from the existing ones
          self.modify and check constraint.
        '''
        popNew = np.zeros( (self.pop_size, self.dim ) )
        cSat = self.checkConstraints(pop)
        popNew = pop[cSat, :]
        while not len(popNew) >= self.pop_size:
            reEvolvePop = self.modify(self.pop) # generate a completely new set of population members
            cSat = self.checkConstraints(reEvolvePop)        # cSat a points to the elements that satisfy the constraints.
            popNew = np.append(popNew, reEvolvePop[cSat, :], axis = 0) # Append all new members to the new population that satisfy the constraints.
        reEvlolvedPop = popNew[:self.pop_size, :]  # Subset the popNew to length pop_size. All members will satisfy the constraints.
        #self.logger.debug('reEvolved population: ')
        #self.logger.debug(popNew)
        return reEvlolvedPop

    # Adjustments for pickling
    def __getstate__(self):
        state = self.__dict__.copy()
        del state['logger']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        # Restore logging
        log = logging.getLogger('gc3.gc3libs.EvolutionaryAlgorithm')
        log.setLevel(logging.DEBUG)
        log.propagate = 0
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        import gc3libs
        log_file_name = os.path.join(self.working_dir, 'EvolutionaryAlgorithm.log')
        file_handler = logging.FileHandler(log_file_name, mode = 'a')
        file_handler.setLevel(logging.DEBUG)
        log.addHandler(stream_handler)
        log.addHandler(file_handler)
