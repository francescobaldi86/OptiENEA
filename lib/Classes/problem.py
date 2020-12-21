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

class Problem:
      # Initialization function
      def __init__(self, name):
            self.name = name
            self.working_folder = dict()
            self.optienea_folder = os.getcwd() + "\\"
            self.output_folder = dict()
            self.units = dict()
            self.parameters = dict()
            self.parametric = dict()
            self.sets = dict()
            self.main = dict()
            self.nSim = 0

      def set_problem_folders(self, folders):
            date = datetime.now().strftime("%Y-%m-%d %Hh%M")
            for type in ["main"]:
                  self.working_folder[type] = "C:\\Users\\" + os.getcwd().split(sep="\\")[2] + "\\" + folders[type] + "\\" + self.name + "\\"
                  self.output_folder[type] = self.working_folder[type] + date + "\\"
                  os.mkdir(self.output_folder[type])

      def parse_general_input_file(self):
            temp = read_input_from_file({}, self.working_folder["main"] + "general.txt")
            for category, item in temp.items():
                  if category == "main":
                        self.main = item
                  elif category == "parameters":
                        self.parameters = item
                  elif category == "parametric":
                        self.parametric.update(item)
                  elif category == "filenames":
                        self.filenames = item
                  else:
                        raise(ValueError, "The provided input type in the general.txt file is not recognized")

      def parse_problem_units(self):
            self.units = read_input_from_file({}, self.working_folder["main"] + "units.txt")

      def parse_problem_sets(self):
            self.sets = {"0": dict(), "1": dict(), "2": dict()}
            self.sets["0"]["timeSteps"] = list(
                  [str(i) for i in range(1, int(self.main["General parameters"]["NT"]) + 1)])
            self.sets = parse_sets(self.sets, self.units)

      def parse_problem_parameters(self):
            for level in ["0", "1", "2", "3"]:
                  if level not in self.parameters.keys():
                        self.parameters[level] = dict()
            self.parameters = parse_parameters(self)
            
            
      