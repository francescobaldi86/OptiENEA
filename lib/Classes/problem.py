# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 10:33:51 2019

@author: Francesco Baldi

This file describes the classes of the OptiENEA tool

"""
import os
from datetime import datetime
from lib.Functions.helpers import read_input_from_file
from lib.Functions.inputParser import parse_sets
from lib.Functions.inputParser import parse_parameters
import lib.Functions.GUI as GUI

class Problem:
      # Initialization function
      def __init__(self):
            self.name = None
            self.problem_folder = None
            self.sim_folder = None
            self.optienea_folder = None
            self.temp_problem_folder = None
            self.temp_folder = None
            self.units = dict()
            self.parameters = dict()
            self.parametric = dict()
            self.sets = dict()
            self.main = dict()
            self.nSim = 0
            self.interpreter = "glpk"  # The type of interpreter of the project. It can be either "ampl" or "glpk", the latter being the default value
            self.solver = "glpsol"  # The type of interpreter of the project. It can be either "cplexamp" or "glpsol", the latter being the default value
            self.solver_options = dict()

      def set_problem_name(self):
            # Set the folder of the "OptiENEA" toolbox, which is where this file is located
            self.optienea_folder = os.getcwd() + "\\"
            found = False
            for file in os.listdir(self.optienea_folder + "Problems"):
                  if file.endswith(".txt"):
                        if file.startswith("UP_"):
                              self.name = file[3:-4]
                              found = True
            if found:
                  temp = read_input_from_file(dict(), self.optienea_folder + "Problems\\UP_" + self.name + ".txt")
                  self.problem_folder = temp["Main"]
                  if "Temp" in temp.keys():
                        self.temp_problem_folder = temp["Temp"]
            else:
                  self.problem_folder, self.temp_problem_folder = GUI.get_problem_directories()
            self.problem_folder = self.problem_folder + "\\"
            if self.temp_problem_folder is not None:
                  self.temp_problem_folder = self.temp_problem_folder + "\\"

      def set_sim_folder(self):
            date = datetime.now().strftime("%Y-%m-%d %Hh%M")
            sim_folder_addend = self.name + " - " + self.simulation_name + " - " + date + "\\"
            self.sim_folder = self.problem_folder + sim_folder_addend
            print(self.sim_folder)
            os.mkdir(self.sim_folder)
            # If the information about a temporary folder is given, we create it. Otherwise not
            if self.temp_problem_folder is not None:
                  self.temp_folder = self.temp_problem_folder + sim_folder_addend
                  os.mkdir(self.temp_folder)

      def parse_general_input_file(self):
            temp = read_input_from_file({}, self.problem_folder + "general.txt")
            for category, item in temp.items():
                  if category == "main":
                        #self.main = item
                        self.__dict__.update(item)
                  elif category == "parameters":
                        self.parameters = item
                  elif category == "parametric":
                        self.parametric.update(item)
                  elif category == "filenames":
                        self.filenames = item
                  else:
                        raise(ValueError, "The provided input type in the general.txt file is not recognized")

      def parse_problem_units(self):
            self.units = read_input_from_file({}, self.problem_folder + self.filenames["units"])


      def parse_problem_sets(self):
            self.sets = {"0": dict(), "1": dict(), "2": dict()}
            self.sets["0"]["timeSteps"] = list(
                  [str(i) for i in range(1, int(self.general_parameters["NT"]) + 1)])
            self.sets = parse_sets(self.sets, self.units)

      def parse_problem_parameters(self):
            for level in ["0", "1", "2", "3", "extra"]:
                  if level not in self.parameters.keys():
                        self.parameters[level] = dict()
            self.parameters = parse_parameters(self)
            
            
      