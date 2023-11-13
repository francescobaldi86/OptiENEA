# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 10:33:51 2019

@author: Francesco Baldi

This file describes the classes of the OptiENEA tool

"""
import os
from datetime import datetime
from unit import Unit, StorageUnit
from problem_parameters import ProblemParameters
from problem_data import ProblemData
from objective import Objective
from constraint import Constraint
from layer import Layer

class Problem:
      # Initialization function
      def __init__(self, name: str, problem_folder = None, temp_folder = None):
            """
            :param: problem_folder        the folder where the main content of the problem is (data, results, etc)
            :param: temp_folder           the temporary folder where temporary data is saved. Useful to specify if problem_folder is on cloud and many simulations are expected
            """
            self.name = name
            self.problem_folder = problem_folder
            self.temp_folder = temp_folder
            self.units: [Unit] | None = None
            self.parameters: ProblemParameters | None = None
            self.problem_data: ProblemData | None = None
            self.objective: Objective | None
            self.constraints: [Constraint] | None = None
            self.layers: [Layer] | None = None
            # self.parametric = dict()

      def full_run(self):
            """
            Class method that simply runs the model as a whole. Useful once everything is set up to run things quickly
            """
            self.create_folders()  # Creates the project folders
            self.read_problem_data()  # Reads problem general data and data about units
            self.process_problem_data()  # Uses the problem data read before and saves them in the appropriate format
            self.generate_amplpy_problem()  # Uses the data to create the amplpy problem
            self.create_model_file()  # Creates the problem mod file
            self.create_data_file()  # Creates the problem data file
            self.solve()  # Solves the optimization problem
            self.read_output()  # Reads the output generated 
            self.save_output()  # Saves the output into useful and readable data structures
            self.generate_plots()  # Generates required figures


      def create_folders(self):
            """
            Creates the project folders
            """
            os.mkdir(f'{self.problem_folder}\\Results')
            os.mkdir(f'{self.problem_folder}\\Latest AMPL files')

      def read_problem_data(self):
            """
            Reads the problem data. 
            They MUST be stored in the problem folder with the names:
                  - 'units.txt' for data related to problem units
                  - 'general.txt' for general data about the problem
            """
            self.problem_data = ProblemData()
            self.problem_data.read_problem_data(self.problem_folder)
      

      def process_problem_data(self):
            """
            Processes the problem data read by read_problem_data (which is basically a multi-level dictionary)
            Units and general are read separately
            """
            # Processing general data
            self.problem_parameters = ProblemParameters(self.problem_data.general_data)
            # Processing units data
            for unit_name, unit_info in self.problem_data.unit_data.items():
                  new_unit = Unit.load_unit(unit_name, unit_info)
                  new_unit.calculate_annualized_capex(interest_rate = self.parameters.interest_rate)
                  self.units.append()
            # Checking for storage units and add related auxiliary units
            for unit in self.units:
                  if isinstance(unit, StorageUnit):
                        self.units = self.units + unit.create_auxiliary_units()
            


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
            
            

"""
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
"""