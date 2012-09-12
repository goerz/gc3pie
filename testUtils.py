#! /usr/bin/env python

#   ggamess.py -- Front-end script for submitting multiple GAMESS jobs to SMSCG.
#
#   Copyright (C) 2010-2012 GC3, University of Zurich
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more delasts.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Logic for executing tests within GAMESS. Tests are executed if INP files include their definition in an appropriate format.

"""
__version__ = 'development version (SVN $Revision$)'
# summary of user-visible changes
__changelog__ = """
  2012-09-05: * Initial release of GAMESS Test Suite by modifing terminated() and , not refactorized and optimized. 
  2012-09-06: * Created a class template for test implementation (testScenario.py) and derived TestNextLine and TestLine classes as sample implementations 
"""
__author__ = 'Lukasz Miroslaw <lukasz.miroslaw@uzh.ch>'
__docformat__ = 'reStructuredText'

import os.path
import sys
import re
import gc3libs

from testScenarios import TestLine, TestNextLine

#This class is responsible for running the tests. Directory with log files.
class GamessTestSuite:
       
	def __init__(self):
 		self.exQ = []
		self.list_of_analyzed_files = []
		
	def prepareInputFiles(self):
		listOfFiles = _getInputFiles(self)
		for filename in listOfFiles:
			FILE = open(filename, 'w')
			lines = FILE.readlines()	
			posLine = self.grep(r"\$[A-Za-z]+", FILE)
			FILE.close()

# Search for pattern in a file	
	def grep(self,pattern,file_obj):
		r=[]
  		for line in file_obj:
			if re.search(pattern,line):
				r.append(line)
		return r
	
	def runTests(self):
		self.log = []
		self.final_flag = True
		self.is_correct = False
		if self.filename_inp is None:
		   gc3libs.log.debug("The list with tests is empty. Skipping.")
	 	   return
		#TODO: if Failed testLogs is empty - fix
		#import pdb;pdb.set_trace()
		for testObj in self.exQ:
			(self.is_correct, test_log) = testObj.run()
			local_flag = False
			if (self.is_correct):
				local_flag = True
			else:
				local_flag = False
				self.log.append(test_log)
			#import pdb;pdb.set_trace()
			self.final_flag = self.final_flag and local_flag 

# Generate tests, e.g. call appropriate method from testLine and testNextLine class. If there is a "GC3" keyword in the INP file the test is added to a list of tests.
# In case the files do not exist just report it so that the execution continues.

	def generate_tests(self,filename_inp, filename_out):
		try:	
			file = open(filename_inp, 'r') 
			foundlines = self.grep("ggamess test", file)	
			file.close()
		except IOError:
			gc3libs.log.warning("There is a problem with a file %s. Skipping.", filename_inp)
			return 
		if os.path.exists(filename_out) == False:
			gc3libs.log.debug("The file %s does not exists. Skipping.", filename_out)
			return 
		if foundlines is None:
			gc3libs.log.debug("File %s does not contain tests. Skipping.", filename_inp)
			return 
		self.filename_inp = filename_inp
		self.filename_out =  filename_out		
			
		param_list = []
		function_list = []
		label_analyze ="grepLinesAndAnalyze"
		label_follow = "grepAndFollow"  
		suffix1 = len(label_analyze+"(")
		suffix2 = len(label_follow+"(")
		for line in foundlines:
		    if  line.find(label_analyze)> 0:
			pos1 = line.find(label_analyze)+suffix1  
			end = line.rfind(")") # Find the last occurence of ")"
			arg1 = line[pos1:end]
			param_list.append(arg1)
			function_list.append(label_analyze)
			pos1 = -1
			continue
		    if line.find(label_follow) > 0:
			pos2 = line.find(label_follow) + suffix2
			end = line.rfind(")")
			arg2 = line[pos2:end]
			pos2 = -1
			function_list.append(label_follow)
			param_list.append(arg2)	
			continue 	
		for args,function in zip(param_list, function_list):
			 arg_list = args.split(",")
			 arg_list_new = []
			 # Remove "" 
			 for arg in arg_list:
				argnew = re.sub(r"[ \"]", r"", arg)
				arg_list_new.append(argnew) 
			 arg_list = arg_list_new
			 try:
				if function==label_follow:
					app = TestNextLine(filename_out)
					fn = getattr(app, label_follow)   
					#import pdb;pdb.set_trace()
					fn(arg_list[0], arg_list[1], arg_list[2], int(arg_list[3]), float(arg_list[4]), arg_list[5], arg_list[6])
					self.exQ.append(app)
	   			elif function==label_analyze:
					app = TestLine(filename_out)
					fn = getattr(app, label_analyze)   
					fn(arg_list[0], arg_list[1], int(arg_list[2]), float(arg_list[3]), arg_list[4], arg_list[5])
					self.exQ.append(app)
			 except IndexError:
				gc3libs.log.warning("Index error. No. of arguments %d exceeds the required number %d. in file %s", len(arg_list), 7, filename_out)                                                                           		
					
			 except AttributeError:
				#import pdb;pdb.set_trace()
				gc3libs.log.warning("Attribute error. arguments %s in function %s from object %s on file %s are incorrect", args, function, app, filename_out)                                                                           		
			 
#python -m pdb ./gdemo.py

#NOTES:
#Incorrect grepex expression is not supported. Example:grepLinesAndAnalyze("TOTAL \s INTERACTION \s (DELTA", .. will raise a traceback.
#Special characters such as : < ( * need to be defined as /< /( /*
#first -2 | last -1 is translated into "2"
#Interesting cases: exam39

#TUTORIAL
# Each test is started with a search for a regular expression. The regular expression
# outputs either a single line or a group of lines. 
# matchedLinePosition defines which matched line to select: first, last or Nth line. (last | first | "" | "2" | 2)
# and returns ONE final line with target information.
# 
# There are two cases. 
# 1. If you want to extract the values from the target line run grepLinesAndAnalyze.
# 2. If you want to extract the values from the line that FOLLOWS the target line run grepAndFollow.

# positionInLine extracts the value from the target line by extracting the column WITHIN the line.

# Value defines a value which will be compared with the value extracted from the file.
# Tol - acceptable difference between Value and value extracted from the text		
