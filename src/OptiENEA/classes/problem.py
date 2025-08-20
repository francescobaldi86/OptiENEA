# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 10:33:51 2019

@author: Francesco Baldi

This file describes the classes of the OptiENEA tool

"""
import os, sys
from datetime import datetime
from pathlib import Path
from OptiENEA.classes.unit import *
from OptiENEA.classes.set import Set
from OptiENEA.classes.parameter import Parameter
from OptiENEA.classes.objective_function import ObjectiveFunction
from OptiENEA.classes.layer import Layer
from OptiENEA.classes.amplpy import AmplProblem
from OptiENEA.helpers.helpers import read_data_file, validate_project_structure, safe_to_list

class Problem:
      # Initialization function
      def __init__(self, name: str, problem_folder = None, temp_folder = None):
            """
            :param: problem_folder        the folder where the main content of the problem is (data, results, etc)
            :param: temp_folder           the temporary folder where temporary data is saved. Useful to specify if problem_folder is on cloud and many simulations are expected
            """
            self.name = name
            self.problem_folder = problem_folder or Path(sys.argv[0]).resolve().parent
            self.temp_folder = temp_folder
            self.units: dict[Unit] | None = {}
            self.sets: dict[Set] | None = Set.create_empty_sets()
            self.parameters: dict[Parameter] | None = Parameter.create_empty_parameters()
            self.layers: set[Layer] | None = set()
            self.raw_unit_data: dict | None = None
            self.raw_general_data : dict | None = None
            self.objective: ObjectiveFunction | None
            self.ampl_problem = AmplProblem()
            self.has_typical_days: bool = False

            self.interpreter: str = 'ampl'
            self.solver: str = 'highs'
            # Addiing ampl parameters
            self.interest_rate = 0.06
            self.simulation_horizon = 8760
            self.ampl_parameters = {"OCCURRENCE": [1], "TIME_STEP_DURATION": [1]}


      def full_run(self):
            """
            Class method that simply runs the model as a whole. Useful once everything is set up to run things quickly
            """
            validate_project_structure(self.problem_folder)
            self.create_folders()  # Creates the project folders
            self.read_problem_data()  # Reads problem general data and data about units
            self.read_units_data()  # Uses the problem data read before and saves them in the appropriate format
            self.set_objective_function()  # Reads and sets the objective function
            self.create_ampl_model()  # Creates the problem mod file
            self.solve_ampl_problem()  # Solves the optimization problem
            self.read_output()  # Reads the output generated 
            self.save_output()  # Saves the output into useful and readable data structures
            self.generate_plots()  # Generates required figures


      def create_folders(self):
            """
            Creates the project folders
            """
            for folder in ['Results', 'Temporary files']:
                  try:
                        os.mkdir(os.path.join(self.problem_folder,folder))
                  except FileExistsError:
                        pass  # Insert log

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
            self.raw_timeseries_data = pd.read_csv(
                  os.path.join(self.problem_folder, 'Input', 'timeseries_data.csv'), 
                  header = [0,1,2], 
                  index_col = 0, 
                  sep = ";")
     
      def read_problem_parameters(self):
            # Reads the problem's general data into the deidcated structure
            self.interpreter = self.raw_general_data['Settings']['Interpreter']
            self.solver = self.raw_general_data['Settings']['Solver']
            # Addiing ampl parameters
            self.interest_rate = self.raw_general_data['Standard parameters']['Interest rate']
            self.simulation_horizon: int = self.raw_general_data['Standard parameters']['NT']
            self.ampl_parameters["OCCURRENCE"] = safe_to_list(self.raw_general_data['Standard parameters']['Occurrence'])
            self.ampl_parameters["TIME_STEP_DURATION"] = safe_to_list(self.raw_general_data['Standard parameters']['Time step duration'])
            # Checking if problem has typical days
            self.has_typical_days = True if len(self.ampl_parameters["OCCURRENCE"]) == 1 else False
      

      def read_units_data(self):
            """
            Processes the problem data read by read_problem_data (which is basically a multi-level dictionary)
            Units and general are read separately
            """            
            # Processing units data
            for unit_name, unit_info in self.raw_unit_data.items():
                  new_unit = Unit.load_unit(unit_name, unit_info)  # Create the new unit
                  # Check some specific cases
                  if isinstance(new_unit, StandardUtility):
                        new_unit.calculate_annualized_capex(interest_rate = self.interest_rate)  # Calculate its investment cost
                  elif isinstance(new_unit, Process): # If it is a process, we also check the power input (we might need to read another file)
                        new_unit.check_power_input(self.raw_timeseries_data)
                  elif isinstance(new_unit, Market): # If it is a market unit, we might need to read a file with time-dependent energy prices
                        new_unit.read_energy_prices(self.raw_timeseries_data)
                  elif isinstance(new_unit, StorageUnit): # If it is a storage unit, let's also add the related charging and discharging units
                        aux_units = new_unit.create_auxiliary_units()
                        for aux_unit in aux_units:
                              aux_unit.calculate_annualized_capex(interest_rate = self.interest_rate)  # Calculate its investment cost
                              self.units[aux_unit.name] = aux_unit
                              self.layers.union(aux_unit.parse_layers())
                  self.units[unit_name] = new_unit
                  self.layers.union(new_unit.parse_layers())        
            

      def parse_sets(self):
            self.sets['timeSteps'] = [int(x) for x in range(self.simulation_horizon, step = self.ampl_parameters['TIME_STEP_DURATION'])]
            for layer in self.layers:
                  self.sets['layers'].append(layer.name)
            for _, unit in self.units.items():
                  for layer in unit.layers:
                        self.sets['layersOfUnit'].append(layer, unit.name)
                  self.sets['MainLayerOfUnit'].append(unit.main_layer, unit.name)
                  if isinstance(unit, Process):
                        self.sets['processes'].append(unit.name)
                  if isinstance(unit, StandardUtility):
                        self.sets['standardUtilities'].append(unit.name)
                  if isinstance(unit, StorageUnit):
                        self.sets['storageUnits'].append(unit.name)
                  if isinstance(unit, ChargingUnit):
                        self.sets['chargingUtilitiesOfStorageUnit'].append(unit.name, unit.storage_unit)
                  if isinstance(unit, DischargingUnit):
                        self.sets['dischargingUtilitiesOfStorageUnit'].append(unit.name, unit.storage_unit)

      def parse_parameters(self, units: list):
        # Parses data for the parameters
        # First, general parameters

        for unit in units:
            if isinstance(unit, Process):
                  for layer in unit.layers:
                        if unit.time_dependent_power_profile:
                              for ts in range(len(unit.power[layer])):
                                    self.parameters['POWER'][unit.name][layer][ts] = unit.power[layer][ts]
                        else:
                             for ts in range(len(unit.power[layer])):
                                    self.parameters['POWER'][unit.name][layer][ts] = unit.power[layer]
            elif isinstance(unit, Utility):
                self.parameters['SPECIFIC_INVESTMENT_COST_ANNUALIZED'][unit.name] = unit.specific_annualized_capex
                self.parameters['POWER_MAX'][unit.name] = {}
                for layer in unit.layers:
                    if unit in self.mod.units_with_time_dependent_maximum_power:
                        self.parameters['POWER_MAX'][unit.name][layer] = max(unit.power_max[layer])
                        self.parameters['POWER_MAX_REL'][unit.name][layer] = [x / self.POWER_MAX[unit.name][layer] for x in unit.power_max[layer]]
                    else:
                        self.parameters['POWER_MAX'][unit.name][layer] = unit.power_max[layer]
                    if isinstance(unit, Market):
                        if layer in self.mod.layers_with_time_dependent_price:
                            self.parameters['ENERGY_PRICE'][layer] = sum(unit.energy_price[layer]) / len(unit.energy_price[layer])
                            self.parameters['ENERGY_PRICE_VARIATION'][layer] = [x / self.parameters['ENERGY_PRICE'][layer] for x in unit.energy_price[layer]]
                        else:
                            self.parameters['ENERGY_PRICE'][layer] = unit.energy_price[layer]
                if isinstance(unit, StorageUnit):
                    self.parameters['ENERGY_MAX'][unit.name] = unit.capacity
                    self.parameters['CRATE'][unit.name] = unit.c_rate
                    self.parameters['ERATE'][unit.name] = unit.e_rate
            else:
                raise TypeError(f'Unit {unit.name} has wrong unit type: should be either Process Utility, or StorageUnit')

      
      def create_ampl_model(self):
            # Based on the available information, create the mod file
            self.ampl_problem.parse_problem_units(self.units)
            self.ampl_problem.parse_problem_objective(self.objective)
            self.ampl_problem.temp_folder = os.path.join(self.problem_folder,'Temporary folder', f'Run {datetime.now().strftime("%Y-%m-%d %H:%M").replace(":", ".")}')
            os.mkdir(self.ampl_problem.temp_folder)
            self.ampl_problem.write_mod_file()
            self.ampl_problem.write_sets_to_amplpy()
            self.ampl_problem.write_parameters_to_amplpy()
            self.ampl_problem.export_model(os.path.join(self.ampl_problem.temp_folder, 'modfile.mod'))
            self.ampl_problem.export_data(os.path.join(self.ampl_problem.temp_folder, 'datfile.dat'))
      
      def solve_ampl_problem(self):
            """
            Calls the required routine to solve the ampl problem
            """
            self.ampl_problem.solve(solver = self.solver)
            print(self.ampl_problem.solve_result())

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