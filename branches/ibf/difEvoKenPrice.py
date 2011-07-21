"""
Driver script for performing an global optimization over the parameter space. 
This code is an adaptation of the following MATLAB code: http://www.icsi.berkeley.edu/~storn/DeMat.zip
Please refer to this web site for more information: http://www.icsi.berkeley.edu/~storn/code.html#deb1
"""

import numpy as np
import sys, os
import logbook
from supportGc3 import StatefulStreamHandler, StatefulFileHandler
try:
  import matplotlib
  matplotlib.use('SVG')
  import matplotlib.pyplot as plt
  matplotLibAvailable = True
except:
  matplotLibAvailable = False


class deKenPrice:
  '''
    Differential evolution optimizer class. 
    Solver iterations can be driven externally (see for ex. gParaSearchDriver) or from within the class (self.deopt()).
    Instance needs two properties, supplied through evaluator class or set externally: 
      1) Target function that takes x and generates f(x)
      2) nlc function that takes x and generates constraint function values c(x) >= 0. 
  '''

  def __init__(self, paraStruct, evaluator = None):
    '''
      Inputs: 
        paraStruct: Dict carrying solver settings. 
        evaluator: Class carrying target and nlc. 
    '''
    if evaluator:
      self.evaluator = evaluator
      self.target    = evaluator.target
      self.nlc       = evaluator.nlc
    self.S_struct = paraStruct
    self.lowerBds = self.S_struct['lowerBds']
    self.upperBds = self.S_struct['upperBds']

    # This is just for notational convenience and to keep the code uncluttered.--------
    self.I_NP         = self.S_struct['I_NP']
    self.F_weight     = self.S_struct['F_weight']
    self.F_CR         = self.S_struct['F_CR']
    self.I_D          = self.S_struct['I_D']
    self.I_itermax    = self.S_struct['I_itermax']
    self.F_VTR        = self.S_struct['F_VTR']
    self.I_strategy   = self.S_struct['I_strategy']
    self.I_plotting   = self.S_struct['I_plotting']
    self.xConvCrit    = self.S_struct['xConvCrit']
    self.workingDir   = self.S_struct['workingDir']
    self.verbosity    = self.S_struct['verbosity']

    # Set up loggers
    self.mySH = StatefulStreamHandler(stream = sys.stdout, level = self.verbosity, format_string = '{record.message}', bubble = True)
    self.mySH.format_string = '{record.message}'
    self.myFH = StatefulFileHandler(filename = os.path.join(self.workingDir, __name__ + '.log'), level = 'DEBUG', bubble = True)
    self.myFH.format_string = '{record.message}'
    self.logger = logbook.Logger(__name__)
    self.logger.handlers.append(self.mySH)
    self.logger.handlers.append(self.myFH)  
    
    # Initialize variables that needed for state retention. 
    self.FM_popold     = np.zeros( (self.I_NP, self.I_D) )  # toggle population
    self.FVr_bestmem   = np.zeros( self.I_D )               # best population member ever
    self.FVr_bestmemit = np.zeros( self.I_D )               # best population member in iteration
    self.I_nfeval      = 0                                  # number of function evaluations 


    # Check input variables
    if ( ( self.F_CR < 0 ) or ( self.F_CR > 1 ) ):
      self.F_CR = 0.5
      self.logger.debug('F_CR should be from interval [0,1]; set to default value 0.5')
    if self.I_NP < 5:
      self.logger.warning('Set I_NP >= 5 for difEvoKenPrice to work. ')

    # Fix seed for debugging
    np.random.seed(1000)

    # set initial value for iteration count
    self.I_iter = -1

    # Create folder to save plots
    self.figSaveFolder = os.path.join(self.workingDir, 'difEvoFigures')
    if not os.path.exists(self.figSaveFolder):
      os.mkdir(self.figSaveFolder)


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
    self.I_iter += 1
    if self.I_iter == 0:
      self.FM_pop = self.drawInitialSample()
      # Evaluate target for the first time
      self.evaluator.createJobs_x(self.FM_pop)
      self.S_vals = self.target(self.FM_pop)
      self.logger.debug('x -> f(x)')
      for x, fx in zip(self.FM_pop, self.S_vals):
        self.logger.debug('%s -> %s' % (x.tolist(), fx))
      # Remember the best population members and their value. 
      self.updatePopulation(self.FM_pop, self.S_vals)
      # Stats for initial population: 
      self.printStats()
      # make plots
      if self.I_plotting:
        self.plotPopulation() 
      return False

    elif self.I_iter > 0:
      # self.I_iter += 1
      self.FM_ui = self.evolvePopulation(self.FM_pop)
      # Check constraints and resample points to maintain population size. 
      self.FM_ui = self.enforceConstrReEvolve(self.FM_ui)
      # EVALUATE TARGET #
      self.evaluator.createJobs_x(self.FM_ui)
      self.S_tempvals = self.target(self.FM_ui)
      self.logger.debug('x -> f(x)')
      for x, fx in zip(self.FM_ui, self.S_tempvals):
        self.logger.debug('%s -> %s' % (x.tolist(), fx))
      self.updatePopulation(self.FM_ui, self.S_tempvals)
      # create output
      self.printStats()
      # make plots
      if self.I_plotting:
        self.plotPopulation()      
      return self.checkConvergence()

  def checkConvergence(self):
    converged = False
    # Check convergence
    if self.I_iter > self.I_itermax:
      converged = True
      self.logger.info('Exiting difEvo. I_iter >self.I_itermax ')
    if self.S_bestval < self.F_VTR:
      converged = True
      self.logger.info('converged self.S_bestval < self.F_VTR')
    if self.populationConverged(self.FM_pop):
      converged = True
      self.logger.info('converged self.populationConverged(self.FM_pop)')
    return converged


  def drawInitialSample(self):
    # Draw population
    pop = self.drawPopulation(self.I_NP, self.I_D) 
    # Check constraints and resample points to maintain population size. 
    return self.enforceConstrResample(pop)

  def updatePopulation(self, newPop = None, newVals = None):
    if self.I_iter == 0:
      self.FM_pop = newPop.copy()
      self.S_vals = newVals.copy()
      # Determine bestmemit and bestvalit for random draw. 
      for k in range(self.I_NP):                          # check the remaining members
        if k == 0:
          self.S_bestval = newVals[0].copy()                # best objective function value so far
          self.I_nfeval  = self.I_nfeval + 1
          self.I_best_index  = 0
        self.I_nfeval  += 1
        if newVals[k] < self.S_bestval == 1:
          self.I_best_index   = k              # save its location
          self.S_bestval      = newVals[k].copy()
      self.FVr_bestmemit = newPop[self.I_best_index, :].copy() # best member of current iteration
      self.S_bestvalit   = self.S_bestval              # best value of current iteration

      self.FVr_bestmem = self.FVr_bestmemit            # best member ever
      
    elif self.I_iter > 0:

      for k in range(self.I_NP):
        self.I_nfeval  = self.I_nfeval + 1
        if newVals[k] < self.S_vals[k]:
          self.FM_pop[k,:] = newPop[k, :].copy()                    # replace old vector with new one (for new iteration)
          self.S_vals[k]   = newVals[k].copy()                      # save value in "cost array"

          #----we update S_bestval only in case of success to save time-----------
          if newVals[k] < self.S_bestval:
            self.S_bestval = newVals[k].copy()                    # new best value
            self.FVr_bestmem = newPop[k,:].copy()                 # new best parameter vector ever

      self.FVr_bestmemit = self.FVr_bestmem       # freeze the best member of this iteration for the coming 
                                          # iteration. This is needed for some of the strategies.
    return 


  def evolvePopulation(self, pop):

    FM_popold      = pop                 # save the old population
    F_CR           = self.F_CR
    F_weight       = self.F_weight
    I_NP           = self.I_NP
    I_D            = self.I_D
    FVr_bestmemit  = self.FVr_bestmemit
    I_strategy     = self.I_strategy

    FM_pm1   = np.zeros( (I_NP, I_D) )   # initialize population matrix 1
    FM_pm2   = np.zeros( (I_NP, I_D) )   # initialize population matrix 2
    FM_pm3   = np.zeros( (I_NP, I_D) )   # initialize population matrix 3
    FM_pm4   = np.zeros( (I_NP, I_D) )   # initialize population matrix 4
    FM_pm5   = np.zeros( (I_NP, I_D) )   # initialize population matrix 5
    FM_bm    = np.zeros( (I_NP, I_D) )   # initialize FVr_bestmember  matrix
    FM_ui    = np.zeros( (I_NP, I_D) )   # intermediate population of perturbed vectors
    FM_mui   = np.zeros( (I_NP, I_D) )   # mask for intermediate population
    FM_mpo   = np.zeros( (I_NP, I_D) )   # mask for old population
    FVr_rot  = np.arange(0, I_NP, 1)    # rotating index array (size I_NP)
    FVr_rotd = np.arange(0, I_D, 1)     # rotating index array (size I_D)
    FVr_rt   = np.zeros(I_NP)            # another rotating index array
    FVr_rtd  = np.zeros(I_D)                 # rotating index array for exponential crossover
    FVr_a1   = np.zeros(I_NP)                # index array
    FVr_a2   = np.zeros(I_NP)                # index array
    FVr_a3   = np.zeros(I_NP)                # index array
    FVr_a4   = np.zeros(I_NP)                # index array
    FVr_a5   = np.zeros(I_NP)                # index array
    FVr_ind  = np.zeros(4)

    # BJ: Need to add +1 in definition of FVr_ind otherwise there is one zero index that leaves creates no shuffling. 
    FVr_ind = np.random.permutation(4) + 1             # index pointer array. 
    FVr_a1  = np.random.permutation(I_NP)              # shuffle locations of vectors
    FVr_rt  = ( FVr_rot + FVr_ind[0] ) % I_NP          # rotate indices by ind(1) positions
    FVr_a2  = FVr_a1[FVr_rt]                           # rotate vector locations
    FVr_rt  = ( FVr_rot + FVr_ind[1] ) % I_NP
    FVr_a3  = FVr_a2[FVr_rt]                
    FVr_rt  = ( FVr_rot + FVr_ind[2] ) % I_NP
    FVr_a4  = FVr_a3[FVr_rt]                
    FVr_rt  = ( FVr_rot + FVr_ind[3] ) % I_NP
    FVr_a5  = FVr_a4[FVr_rt]                


    FM_pm1 = FM_popold[FVr_a1, :]             # shuffled population 1
    FM_pm2 = FM_popold[FVr_a2, :]             # shuffled population 2
    FM_pm3 = FM_popold[FVr_a3, :]             # shuffled population 3
    FM_pm4 = FM_popold[FVr_a4, :]             # shuffled population 4
    FM_pm5 = FM_popold[FVr_a5, :]             # shuffled population 5


    for k in range(I_NP):                              # population filled with the best member
      FM_bm[k,:] = FVr_bestmemit                       # of the last iteration

    FM_mui = np.random.random_sample( (I_NP, I_D ) ) < F_CR  # all random numbers < F_CR are 1, 0 otherwise

    #----Insert this if you want exponential crossover.----------------
    #FM_mui = sort(FM_mui')	  # transpose, collect 1's in each column
    #for k  = 1:I_NP
    #  n = floor(rand*I_D)
    #  if (n > 0)
    #     FVr_rtd     = rem(FVr_rotd+n,I_D)
    #     FM_mui(:,k) = FM_mui(FVr_rtd+1,k) #rotate column k by n
    #  end
    #end
    #FM_mui = FM_mui'			  # transpose back
    #----End: exponential crossover------------------------------------

    FM_mpo = FM_mui < 0.5    # inverse mask to FM_mui

    if ( I_strategy == 1 ):                             # DE/rand/1
      FM_ui = FM_pm3 + F_weight * ( FM_pm1 - FM_pm2 )   # differential variation
      FM_ui = FM_popold * FM_mpo + FM_ui * FM_mui       # crossover
      FM_origin = FM_pm3
    elif (I_strategy == 2):                         # DE/local-to-best/1
      FM_ui = FM_popold + F_weight * ( FM_bm - FM_popold ) + F_weight * ( FM_pm1 - FM_pm2 )
      FM_ui = FM_popold * FM_mpo + FM_ui * FM_mui
      FM_origin = FM_popold
    elif (I_strategy == 3):                         # DE/best/1 with jitter
      FM_ui = FM_bm + ( FM_pm1 - FM_pm2 ) * ( (1 - 0.9999 ) * np.random.random_sample( (I_NP, I_D ) ) +F_weight )               
      FM_ui = FM_popold * FM_mpo + FM_ui * FM_mui
      FM_origin = FM_bm
    elif (I_strategy == 4):                         # DE/rand/1 with per-vector-dither
      f1 = ( ( 1 - F_weight ) * np.random.random_sample( (I_NP, 1 ) ) + F_weight)
      for k in range(I_D):
        FM_pm5[:,k] = f1
      FM_ui = FM_pm3 + (FM_pm1 - FM_pm2) * FM_pm5    # differential variation
      FM_origin = FM_pm3
      FM_ui = FM_popold * FM_mpo + FM_ui * FM_mui     # crossover
    elif (I_strategy == 5):                          # DE/rand/1 with per-vector-dither
      f1 = ( ( 1 - F_weight ) * np.random.random_sample() + F_weight )
      FM_ui = FM_pm3 + ( FM_pm1 - FM_pm2 ) * f1         # differential variation
      FM_origin = FM_pm3
      FM_ui = FM_popold * FM_mpo + FM_ui * FM_mui   # crossover
    else:                                              # either-or-algorithm
      if (np.random.random_sample() < 0.5):                               # Pmu = 0.5
        FM_ui = FM_pm3 + F_weight * ( FM_pm1 - FM_pm2 )# differential variation
        FM_origin = FM_pm3
      else:                                           # use F-K-Rule: K = 0.5(F+1)
        FM_ui = FM_pm3 + 0.5 * ( F_weight + 1.0 ) * ( FM_pm1 + FM_pm2 - 2 * FM_pm3 )
        FM_ui = FM_popold * FM_mpo + FM_ui * FM_mui     # crossover 

    return FM_ui




  def printStats(self):
    self.logger.debug('Iteration: %d,  x: %s f(x): %f' % 
                      (self.I_iter, self.FVr_bestmem, self.S_bestval))

  def plotPopulation(self, pop):
    # Plot population
    if self.I_D == 2:
      x = pop[:, 0]
      y = pop[:, 1]
      if matplotLibAvailable:
        # determine bounds
        xDif = self.upperBds[0] - self.lowerBds[0]
        yDif = self.upperBds[1] - self.lowerBds[1]
        scaleFac = 0.3
        xmin = self.lowerBds[0] - scaleFac * xDif
        xmax = self.upperBds[0] + scaleFac * xDif
        ymin = self.lowerBds[1] - scaleFac * yDif
        ymax = self.upperBds[1] + scaleFac * yDif

        # make plot
        fig = plt.figure()
        ax = fig.add_subplot(111)

        ax.scatter(x, y)
        # x box constraints
        ax.plot([self.lowerBds[0], self.lowerBds[0]], [ymin, ymax])
        ax.plot([self.upperBds[0], self.upperBds[0]], [ymin, ymax])
        # all other linear constraints
        c_xmin = self.nlc.linearConstr(xmin)
        c_xmax = self.nlc.linearConstr(xmax)
        for ixC in range(len(c_xmin)):
          ax.plot([xmin, xmax], [c_xmin[ixC], c_xmax[ixC]])
        ax.axis(xmin = xmin, xmax = xmax,  
                ymin = ymin, ymax = ymax)
        ax.set_xlabel('EH')
        ax.set_ylabel('sigmaH')
        ax.set_title('Best: x %s, f(x) %f' % (self.FVr_bestmem, self.S_bestval))

        fig.savefig(os.path.join(self.figSaveFolder, 'pop%d' % (self.I_iter)))    

  def drawPopulation(self, size, dim):
    pop = np.zeros( (size, dim ) )
    for k in range(size):
      pop[k,:] = self.drawPopulationMember(dim)
    return pop

  def drawPopulationMember(self, dim):
    return self.lowerBds + np.random.random_sample( dim ) * ( self.upperBds - self.lowerBds )

  def enforceConstrResample(self, pop):
    maxDrawSize = self.I_NP * 100
    dim = self.I_D
    for ixEle, ele in enumerate(pop):
      constr = self.nlc(ele)
      ctr = 0
      while not sum(constr > 0) == len(constr) and ctr < maxDrawSize:
        pop[ixEle, :] = self.drawPopulationMember(dim)
        constr = self.nlc(ele)
        ctr += 1
      if ctr >= maxDrawSize: 
        pass
        #self.logger.debug('Couldnt sample a feasible point with {0} draws', maxDrawSize)
    return pop

  def checkConstraints(self, pop):
    cSat = np.empty( ( len(pop) ), dtype = bool)
    for ixEle, ele in enumerate(pop):
      constr = self.nlc(ele)
      cSat[ixEle] = sum(constr > 0) == len(constr)
    return cSat

  def enforceConstrReEvolve(self, pop):
    popNew = np.zeros( (self.I_NP, self.I_D ) )
    cSat = self.checkConstraints(pop)
    popNew = pop[cSat, :]
    while not len(popNew) >= self.I_NP:
      reEvolvePop = self.evolvePopulation(pop)
      cSat = self.checkConstraints(reEvolvePop)
      popNew = np.append(popNew, reEvolvePop[cSat, :], axis = 0)
    reEvlolvedPop = popNew[:self.I_NP, :]
    #self.logger.debug('reEvolved population: ')
    #self.logger.debug(popNew)
    return reEvlolvedPop

  def populationConverged(self, pop):
    '''
    Check if population has converged. 
    '''
    diff = np.abs(pop[:, :] - pop[0, :])
    return (diff <= self.xConvCrit).all()

def jacobianFD(x, fun):
  '''
    Compute jacobian for function fun. 
    Inputs: x: vector of input values
            fun: function returning vector of output values
  '''
  delta = 1.e-8
  fval = fun(x)
  m = len(fval)
  n = len(x)
  jac = np.empty( ( m, n ) )
  for ixCol in range(n):
    xNew = x.copy()
    xNew[ixCol] = xNew[ixCol] + delta
    fvalNew = fun(xNew)
    jac[:, ixCol] = ( fvalNew - fval ) / delta
  #   logger.debug(jac)
  return jac




def testFun(x):
  return x*x

class Rosenbrock:
  def __init__(self):
    #********************************************************************
    # Script file for the initialization and run of the differential 
    # evolution optimizer.
    #********************************************************************

    # F_VTR		"Value To Reach" (stop when ofunc < F_VTR)
    F_VTR = 1.e-8 

    # I_D		number of parameters of the objective function 
    I_D = 2 

    # FVr_minbound,FVr_maxbound   vector of lower and bounds of initial population
    #    		the algorithm seems to work especially well if [FVr_minbound,FVr_maxbound] 
    #    		covers the region where the global minimum is expected
    #               *** note: these are no bound constraints!! ***
    FVr_minbound = -2 * np.ones(I_D) 
    FVr_maxbound = +2 * np.ones(I_D) 
    I_bnd_constr = 0  #1: use bounds as bound constraints, 0: no bound constraints      

    # I_NP            number of population members
    I_NP = 20  #pretty high number - needed for demo purposes only

    # I_itermax       maximum number of iterations (generations)
    I_itermax = 200 

    # F_weight        DE-stepsize F_weight ex [0, 2]
    F_weight = 0.85 

    # F_CR            crossover probabililty constant ex [0, 1]
    F_CR = 1

    # I_strategy     1 --> DE/rand/1:
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
    #                      Choosing F_weight = 0.3 is a good start here.
    #                6 --> DE/rand/1 either-or-algorithm:
    #                      Alternates between differential mutation and three-point-
    #                      recombination.           

    I_strategy = 1

    # I_refresh     intermediate output will be produced after "I_refresh"
    #               iterations. No intermediate output will be produced
    #               if I_refresh is < 1
    I_refresh = 3

    # I_plotting    Will use plotting if set to 1. Will skip plotting otherwise.
    I_plotting = 1

    #-----Problem dependent constant values for plotting----------------

    #if (I_plotting == 1):
            #FVc_xx = [-2:0.125:2]
            #FVc_yy = [-1:0.125:3]
            #[FVr_x,FM_y]=meshgrid(FVc_xx',FVc_yy') 
            #FM_meshd = 100.*(FM_y-FVr_x.*FVr_x).^2 + (1-FVr_x).^2 

            #S_struct.FVc_xx    = FVc_xx
            #S_struct.FVc_yy    = FVc_yy
            #S_struct.FM_meshd  = FM_meshd 
    #end

    S_struct = {}
    S_struct['I_NP']         = I_NP
    S_struct['F_weight']     = F_weight
    S_struct['F_CR']         = F_CR 
    S_struct['I_D']          = I_D 
    S_struct['FVr_minbound'] = FVr_minbound
    S_struct['FVr_maxbound'] = FVr_maxbound
    S_struct['I_bnd_constr'] = I_bnd_constr
    S_struct['I_itermax']    = I_itermax
    S_struct['F_VTR']        = F_VTR
    S_struct['I_strategy']   = I_strategy
    S_struct['I_refresh']    = I_refresh
    S_struct['I_plotting']   = I_plotting

    deKenPrice(self, S_struct)

  def target(self, vectors):

    S_MSEvec = []
    for vector in vectors:
      #---Rosenbrock saddle-------------------------------------------
      F_cost = 100 * ( vector[1] - vector[0]**2 )**2 + ( 1 - vector[0] )**2

      #----strategy to put everything into a cost function------------
      S_MSE = {}
      S_MSE['I_nc']      = 0 #no constraints
      S_MSE['FVr_ca']    = 0 #no constraint array
      S_MSE['I_no']      = 1 #number of objectives (costs)
      S_MSE['FVr_oa'] = []
      S_MSE['FVr_oa'].append(F_cost)
      S_MSEvec.append(S_MSE)

    return S_MSEvec




if __name__ == '__main__':
  x = np.array([3., 5., 6.])
  jacobianFD(x, testFun)
#  Rosenbrock()

