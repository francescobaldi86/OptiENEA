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
from OptiENEA.classes.objective_function import ObjectiveFunction
from OptiENEA.classes.parameter import Parameter
from OptiENEA.classes.layer import Layer
from OptiENEA.classes.amplpy import AmplProblem
from OptiENEA.helpers.helpers import read_data_file, validate_project_structure, safe_to_list, dict_tree, to_dict

class Problem:
      name: str
      problem_folder: str
      temp_folder: str
      units: dict[Unit] | None
      sets: dict[Set] | None
      parameters: dict
      layers: set[Layer] | None
      raw_unit_data: dict | None
      raw_general_data : dict | None
      objective: ObjectiveFunction | None
      ampl_problem: AmplProblem
      has_typical_days: bool
      number_of_typical_days: int
      interpreter: str
      solver: str
      interest_rate: float
      simulation_horizon: int
      ampl_parameters : dict

      # Initialization function
      def __init__(self, name: str, problem_folder = None, temp_folder = None):
            """
            :param: problem_folder        the folder where the main content of the problem is (data, results, etc)
            :param: temp_folder           the temporary folder where temporary data is saved. Useful to specify if problem_folder is on cloud and many simulations are expected
            """
            self.name = name
            self.problem_folder = problem_folder or Path(sys.argv[0]).resolve().parent
            self.temp_folder = temp_folder
            self.units = {}
            self.sets = Set.create_empty_sets()
            self.parameters = Parameter.create_empty_parameters()
            self.layers = set()
            self.ampl_problem = AmplProblem(self)
            self.number_of_typical_days: int
            self.interpreter = 'ampl'
            self.solver = 'highs'
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
            self.parse_sets()
            self.parse_parameters()
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
            self.ampl_parameters["TIME_STEP_DURATION"] = self.raw_general_data['Standard parameters']['Time step duration']
            # Checking if problem has typical days
            self.has_typical_days = True if len(self.ampl_parameters["OCCURRENCE"]) == 1 else False
            self.number_of_typical_days = len(self.ampl_parameters["OCCURRENCE"])
            self.objective = ObjectiveFunction(self.raw_general_data['Settings']['Objective'])
      

      def read_units_data(self):
            """
            Processes the problem data read by read_problem_data (which is basically a multi-level dictionary)
            Units and general are read separately
            """            
            # Processing units data
            # first we parse Storage Units, so to add the corresponding charging and discharging units to the list
            for unit_name, unit_info in self.raw_unit_data.items():
                  auxiliary_units = {}
                  if unit_info['Type'] == 'StorageUnit':
                        charging_unit_info = StorageUnit.create_auxiliary_unit_info(unit_name, unit_info, 'Charging')
                        discharging_unit_info = StorageUnit.create_auxiliary_unit_info(unit_name, unit_info, 'Discharging')
                        auxiliary_units.update({charging_unit_info['Name']: charging_unit_info})
                        auxiliary_units.update({discharging_unit_info['Name']: discharging_unit_info})
            self.raw_unit_data.update(auxiliary_units)
            for unit_name, unit_info in self.raw_unit_data.items():
                  new_unit = self.load_unit(unit_name, unit_info)  # Create the new unit
                  self.units[unit_name] = new_unit
                  self.layers = self.layers.union(new_unit.parse_layers())
      
      def load_unit(self, name: str, info: dict):
            match info['Type']:
                  case 'Process':
                        return Process(name, info, self)
                  case 'Utility':
                        return StandardUtility(name, info, self)
                  case 'StorageUnit':
                        return StorageUnit(name, info, self)
                  case 'Market':
                        return Market(name, info, self)
                  case 'ChargingUnit': 
                        return ChargingUnit(name, info, self)
                  case 'DischargingUnit':
                        return DischargingUnit(name, info, self)   
            

      def parse_sets(self):
            # NOTE: The append method is a method of the class "Set"
            self.sets['timeSteps'].content.update([int(x) for x in range(0, self.simulation_horizon, self.ampl_parameters['TIME_STEP_DURATION'])])
            for layer in self.layers:
                  self.sets['layers'].append(layer.name)
            for _, unit in self.units.items():
                  for layer in unit.layers:
                        self.sets['layersOfUnit'].append(layer, unit.name)
                  self.sets['mainLayerOfUnit'].append(unit.main_layer, unit.name)
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

      def parse_parameters(self):
        # Parses data for the parameters
            for unit_name, unit in self.units.items():
                  if isinstance(unit, Process):
                        for layer in unit.layers:
                              if isinstance(unit.power[layer], pd.Series):
                                    temp = pd.DataFrame(index = unit.power[layer].index, columns = self.parameters['POWER'].content.columns)
                                    temp.loc[:, 'POWER'] = unit.power[layer]
                                    temp.loc[:, 'processes'] = unit_name
                                    temp.loc[:, 'layersOfUnit'] = layer
                              else:
                                    temp = pd.DataFrame(index = [x for x in range(self.simulation_horizon)], columns = self.parameters['POWER'].content.columns)
                                    temp.loc[:, 'POWER'] = unit.power[layer]
                                    temp.loc[:, 'processes'] = unit_name
                                    temp.loc[:, 'layersOfUnit'] = layer
                              temp.loc[:, 'timeSteps'] = temp.index
                              self.parameters['POWER'].list_content.append(temp)
                  elif isinstance(unit, Utility):
                        self.parameters['SPECIFIC_INVESTMENT_COST_ANNUALIZED'].list_content.append({'utilities': unit_name, 'SPECIFIC_INVESTMENT_COST_ANNUALIZED': unit.specific_annualized_capex})
                        if isinstance(unit, StandardUtility):
                              for layer in unit.layers:
                                    if isinstance(unit.max_power[layer], pd.Series):
                                          self.parameters['POWER_MAX'].list_content.append({'nonStorageUtilities': unit_name, 'layersOfUnit': layer, 'POWER_MAX': max(unit.max_power[layer])})
                                          temp = pd.DataFrame(index = unit.max_power[layer].index, columns = self.parameters['POWER_MAX_REL'].content.columns)
                                          temp.loc[:, 'POWER_MAX_REL'] = unit.max_power[layer] / max(unit.max_power[layer])
                                          temp.loc[:, 'nonStorageUtilities'] = unit_name
                                          temp.loc[:, 'layersOfUnit'] = layer
                                          temp.loc[:, 'timeSteps'] = temp.index
                                          self.parameters['POWER_MAX_REL'].list_content.append(temp)
                                    else:
                                          self.parameters['POWER_MAX'].list_content.append({'nonStorageUtilities': unit_name, 'layersOfUnit': layer, 'POWER_MAX': unit.max_power[layer]})
                                    if isinstance(unit, Market):
                                          self.parameters['ENERGY_AVERAGE_PRICE'].list_content.append({'markets': unit_name, 'layersOfUnit': layer, 'ENERGY_AVERAGE_PRICE': unit.energy_price[layer]})
                                          if unit.energy_price_variation[layer]:
                                                temp = pd.DataFrame(index = unit.energy_price_variation[layer].index, columns = self.parameters['ENERGY_PRICE_VARIATION'].content.columns)
                                                temp.loc[:, 'ENERGY_PRICE_VARIATION'] = unit.energy_price_variation[layer]
                                                temp.loc[:, 'nonStorageUtilities'] = unit_name
                                                temp.loc[:, 'layersOfUnit'] = layer
                                                temp.loc[:, 'timeSteps'] = temp.index
                                                self.parameters['ENERGY_PRICE_VARIATION'].list_content.append(temp)
                        elif isinstance(unit, StorageUnit):
                              self.parameters['ENERGY_MAX'].list_content.append({'storageUnits': unit_name, 'ENERGY_MAX': unit.max_energy})
                              self.parameters['CRATE'].list_content.append({'storageUnits': unit_name, 'CRATE': unit.c_rate})
                              self.parameters['ERATE'].list_content.append({'storageUnits': unit_name, 'ERATE': unit.e_rate})
                  else:
                        raise TypeError(f'Unit {unit_name} has wrong unit type: should be either Process, Utility, StorageUnit or Market')
            # Finally doing the conversion from lists to Dataframes
            for param_name, parameter in self.parameters.items():
                  if parameter.indexing_level > 0 and parameter.list_content != []:
                        if param_name in {'ENERGY_PRICE_VARIATION', 'POWER_MAX_REL', 'POWER'}:
                              parameter.content = pd.concat(parameter.list_content)
                        else:
                              parameter.content = pd.DataFrame(parameter.list_content)
                        parameter.content = parameter.content.set_index([x for x in parameter.content.columns if x != param_name])

      
      def create_ampl_model(self):
            # Based on the available information, create the mod file
            self.ampl_problem.temp_folder = os.path.join(self.problem_folder,'Temporary files', f'Run {datetime.now().strftime("%Y-%m-%d %H:%M").replace(":", ".")}')
            os.mkdir(self.ampl_problem.temp_folder)
            self.ampl_problem.parse_problem_settings()
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