# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 10:33:51 2019

@author: Francesco Baldi

This file describes the classes of the OptiENEA tool

"""
import os
from datetime import datetime
from amplpy import AMPL
from OptiENEA.classes.unit import *
from OptiENEA.classes.problem_parameters import ProblemParameters
from OptiENEA.classes.objective_function import ObjectiveFunction
from OptiENEA.classes.layer import Layer
from OptiENEA.classes.amplpy import AmplMod, AmplDat
from OptiENEA.helpers.helpers import read_data_file, validate_project_structure

class Problem:
      # Initialization function
      def __init__(self, name: str, problem_folder = None, temp_folder = None, 
                   check_input_data = True, create_problem_folders = True):
            """
            :param: problem_folder        the folder where the main content of the problem is (data, results, etc)
            :param: temp_folder           the temporary folder where temporary data is saved. Useful to specify if problem_folder is on cloud and many simulations are expected
            """
            self.name = name
            self.problem_folder = problem_folder
            self.temp_folder = temp_folder
            self.units: list[Unit] | None = None
            self.parameters: ProblemParameters | None = None
            self.raw_unit_data: dict | None = None
            self.raw_general_data : dict | None = None
            self.objective: ObjectiveFunction | None
            # self.constraints: [Constraint] | None = None
            self.layers: set[Layer] | None = None
            # self.parametric = dict()
            self.has_typical_days: bool = False

            if check_input_data:
                  self.check_input_data()
            if create_problem_folders:
                  self.create_folders()

      def full_run(self):
            """
            Class method that simply runs the model as a whole. Useful once everything is set up to run things quickly
            """
            validate_project_structure(self.problem_folder)
            self.create_folders()  # Creates the project folders
            self.read_problem_data()  # Reads problem general data and data about units
            self.process_problem_data()  # Uses the problem data read before and saves them in the appropriate format
            # self.generate_amplpy_problem()  # Uses the data to create the amplpy problem
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
            os.mkdir(os.path.join(self.problem_folder,'Results'))
            os.mkdir(os.path.join(self.problem_folder,'Latest AMPL files'))

      def read_problem_data(self):
            """
            Reads the problem data. 
            They MUST be stored in the problem folder with the names:
                  - 'units.yml' for data related to problem units
                  - 'general.yml' for general data about the problem
            """
            with open(os.path.join(self.problem_folder, 'Input','units.yml'), 'r') as stream:
                  self.raw_unit_data = yaml.safe_load(stream)
            with open(os.path.join(self.problem_folder, 'Input','general.yml'), 'r') as stream:
                  self.raw_general_data = yaml.safe_load(stream)
      

      def process_problem_data(self):
            """
            Processes the problem data read by read_problem_data (which is basically a multi-level dictionary)
            Units and general are read separately
            """
            # Processing general data
            self.problem_parameters = ProblemParameters()
            self.problem_parameters.read_problem_paramters(self.raw_general_data)
            # Checking if the problem has typical days
            self.has_typical_days = True if len(self.problem_parameters.ampl_parameters["OCCURRENCE"] == 1) else False
            # Processing units data
            for unit_name, unit_info in self.raw_unit_data():
                  new_unit = Unit.load_unit(unit_name, unit_info)  # Create the new unit
                  # Check some specific cases
                  if isinstance(new_unit, StandardUtility):
                        new_unit.calculate_annualized_capex(interest_rate = self.parameters.interest_rate)  # Calculate its investment cost
                  elif isinstance(new_unit, Process): # If it is a process, we also check the power input (we might need to read another file)
                        new_unit.power = new_unit.check_power_input(self.problem_folder, self.has_typical_days)
                  elif isinstance(new_unit, Market): # If it is a market unit, we might need to read a file with time-dependent energy prices
                        self.energy_price = read_data_file(new_unit.energy_price, new_unit.name, self.problem_folder)
                  elif isinstance(new_unit, StorageUnit): # If it is a storage unit, let's also add the related charging and discharging units
                        aux_units = new_unit.create_auxiliary_units()
                        for aux_unit in aux_units:
                              aux_unit.calculate_annualized_capex(interest_rate = self.parameters.interest_rate)  # Calculate its investment cost
                              self.units.append(aux_unit)
                              self.layers.union(aux_unit.parse_layers())
                  self.units.append(new_unit)
                  self.layers.union(new_unit.parse_layers())        
            # Add problem objective function
            self.set_objective_function()
      
      def create_model_file(self):
            # Based on the available information, create the mod file
            self.mod = AmplMod()
            self.mod.parse_problem_units(self.units)
            self.mod.parse_problem_objective(self.objective)
            self.mod.write_mod_file()
            self.ampl_problem = AMPL()
            self.ampl_problem.read(self.mod.mod_string)
            self.ampl_problem.export_model(self.temp_folder)

      def create_data_file(self):
            # Basically parses the data internally to create the .dat file for running ampl
            aaa = 0
            

      def set_objective_function(self):
            # Sets the objective function
            if isinstance(self.problem_data.objective, str):
                  self.objective = ObjectiveFunction(self.problem_data.objective)
            elif isinstance(self.problem_data.objective, dict):
                  for key, info in self.problem_data.objective.items():
                        self.objective = ObjectiveFunction(key, info)



    
            

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