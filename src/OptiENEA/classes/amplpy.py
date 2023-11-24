from OptiENEA.classes.problem_parameters import ProblemParameters
from OptiENEA.classes.unit import Utility, Process, StorageUnit, Market, StandardUtility
from OptiENEA.classes.objective_function import ObjectiveFunction
import pandas as pd
import amplpy

class AmplMod():
    def __init__(self):
        self.mod_string = ""
        self.has_storage = False
        self.has_capex = False
        self.units_with_time_dependent_maximum_power = []
        self.layers_with_time_dependent_price = []
        self.units_prased = False
        self.objective_parsed = False
    
    def get_mod_file(self):
        return self.mod_string

    def parse_problem_units(self, units: list):
        # Parses the problem for finding the key information required to determine 
        # what is needed for the definition of the mod file
        for unit in units:
            if isinstance(unit, Utility):
                if unit.specific_capex > 0.0:
                    self.has_capex = True  # Checks if the problem should calculate the CAPEX
                if isinstance(unit, StorageUnit):
                    self.has_storage = True  # Checks if there is any storage unit
                if isinstance(unit.power_max, pd.DataFrame):
                    self.units_with_time_dependent_maximum_power.append(unit.name)
                if isinstance(unit, Market):
                    if isinstance(unit.energy_price, pd.DataFrame):
                        for layer in unit.layers:
                            self.layers_with_time_dependent_price.append(layer.name)
                            
        self.units_parsed = True
    
    def parse_problem_objective(self, objective: ObjectiveFunction):
        # Parses the problem objective from the "objective" object
        self.objective_string = objective.objective
        self.objective_related_constraints = objective.constraints
        self.objective_parsed = True

    def write_mod_file(self):
        if self.units_parsed and self.objective_parsed:
            self.write_sets()
            self.write_parameters()
            self.write_variables()
            self.write_objective()
            self.write_constraints()
        else:
            raise ValueError('You should first parse the problem data, only then you can write the mod file')

    def write_sets(self):
        # Adds the problem sets to the mod file string
        self.mod_string += """
            set timeSteps;\n
            set processes;\n
            set standardUtilities;\n
            set utilities := standardUtilities union markets;
            set units := utilities union processes;\n
            set layers;\n
            set layersOfUnit{u in units};\n
            set mainLayerOfUnit{u in units};\n
            set unitsOfLayer{l in layers} := setof{u in units : l in layersOfUnit[u]} u;\n
            set marketLayers := setof{u in markets, l in layersOfUnit[u]} l;\n
            set nonmarketUtilities := utilities diff markets;\n
        """
        if self.has_storage:
            self.mod_string += """
                set storageUnits
                set chargingUtilitiesOfStorageUnit{u in storageUnits} within utilities;\n
                set dischargingUtilitiesOfStorageUnit{u in storageUnits} within utilities;\n
                set nonstorageUtilities within utilities := utilities diff storageUnits;\n
            """
            self.mod_string.replace(
                "set utilities := standardUtilities union markets;\n",
                "set utilities := standardUtilities union markets union storageUnits;\n",
            )
        if len(self.units_with_time_dependent_maximum_power) > 0:
            self.mod_string += "utilitiesWithTimeDependentMaxPower within utilities;\n"
            self.mod_string += "utilitiesWithFixedMaxPower: utilities diff utilitiesWithTimeDependentMaxPower;\n"
        if len(self.layers_with_time_dependent_price) > 0:
            self.mod_string += "layersWithTimeDependentPrice within layers;\n" 
            self.mod_string += "layersWithFixedPrice: layers diff layersWithTimeDependentPrice;\n"

    def write_parameters(self):
        # Adds the problem parameters to the mod file string
        self.mod_string += """
            param POWER_MAX{u in utilities, l in layersOfUnit[u]} default 0;\n
            param POWER{p in processes, l in layersOfUnit[p], t in timeSteps};\n
            param TIME_STEP_DURATION;\n
            param OCCURRANCE;\n
            param SPECIFIC_INVESTMENT_COST_ANNUALIZED{u in utilities} default 0;\n
            param ENERGY_PRICE{l in layers} default 0;\n
        """
        if len(self.layers_with_time_dependent_price) > 0:
            self.mod_string += "param ENERGY_PRICE_VARIATION{l in layersWithTimeDependentPrice, t in timeSteps} default 1;\n"
        if len(self.units_with_time_dependent_maximum_power):
            self.mod_string += "param POWER_MAX_REL{u in utilitiesWithTimeDependentMaxPower, l in layersOfUnit[u], t in timeSteps} default 1;\n"
        if self.has_storage:
            self.mod_string += """
                param ENERGY_MAX{u in storageUnits} default 0;\n
                param CRATE{u in storageUnits} default 1;\n
                param ERATE{u in storageUnits} default 1;\n
                param STORAGE_CYCLIC_ACTIVE default 1;\n
            """
            self.mod_string.replace(
                "param POWER_MAX{u in utilities, l in layersOfUnit[u]} default 0;\n",
                "param POWER_MAX{u in nonStorageUtilities, l in layersOfUnit[u]} default 0;\n"
            )
            self.mod_string.replace(
                "param POWER_MAX_REL{u in utilities, l in layersOfUnit[u], t in timeSteps} default 1;\n",
                "param POWER_MAX_REL{u in nonStorageUtilities, l in layersOfUnit[u], t in timeSteps} default 1;\n"
            )
        
    def write_variables(self):
        # Adds the problem sets to the mod file string
        self.mod_string += """
            var power{u in units, l in layersOfUnit[u], t in timeSteps};\n
            var layer_operating_cost{u in markets, l in layersOfUnit[u]};\n
            var ics{u in nonmarketUtilities, t in timeSteps} >= 0, <= 1;\n
            var OPEX;\n
        """
        if self.has_storage:
            self.mod_string += "var energyStorageLevel{u in storageUnits, l in layersOfUnit[u], t in timeSteps} >=0;\n"
            self.mod_string += "var energyStorageLevel0{u in storageUnits, l in layersOfUnit[u]} >=0;\n"
        
        if self.has_capex:
            self.mod_string += "var unitAnnualizedInvestmentCost{u in units} >= 0;"
            self.mod_string += "var size{u in nonmarketUtilities} >= 0;"
            self.mod_string += "var CAPEX"

    def write_objective(self):
        # Adds the problem objective to the mod file string
        self.mod_string += self.objective_string
        for constraint in self.objective_related_constraints:
            self.mod_string += constraint


    def write_constraints(self):
        # Adds the problem constraints to the mod file string
        self.mod_string += """
            s.t. calculate_opex: OPEX = sum{u in markets, l in layersOfUnit[u]} layer_operating_cost[l] ;
            s.t. layer_balance{l in layers, t in timeSteps}: sum{u in unitsOfLayer[l]} (power[u,l,t]) = 0;
            s.t. process_power{p in processes, l in layersOfUnit[p], t in timeSteps}: power[p,l,t] = POWER[p,l,t];
        """
        # Constraints to be added depending on whether we are calculating the cost of the investment or not
        if self.has_capex:
            self.mod_string += """
                s.t. componentSizing{u in standardUtilities, l in mainLayerOfUnit[u], t in timeSteps}: size[u] >= ics[u,t] * abs(POWER_MAX[u,l]); 
                s.t. calculate_capex: CAPEX = sum{u in utilities} unitAnnualizedInvestmentCost[u];\n 
                s.t. calculate_investment_cost{u in nonmarketUtilities}: unitAnnualizedInvestmentCost[u] = size[u] * SPECIFIC_INVESTMENT_COST_ANNUALIZED[u];
           """
        # Constraints to be added depending on whether energy prices depend on the time step or not
        if len(self.layers_with_time_dependent_price) > 0:
            self.mod_string += "s.t. calculate_operating_cost_standard{u in markets, l in layersOfUnit[u]: l in layersWithFixedPrice}: layer_operating_cost[l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_PRICE[l]) * TIME_STEP_DURATION * OCCURRANCE;\n"
            self.mod_string += "s.t. calculate_operating_cost_time_dependent{u in markets, l in layersOfUnit[u]: l in layersWithTimeDependentPrice}: layer_operating_cost[l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_PRICE[l] * ENERGY_PRICE_VARIATION[l,t]) * TIME_STEP_DURATION * OCCURRANCE;\n"
        else: 
            self.mod_string += "s.t. calculate_operating_cost_standard{u in markets, l in layersOfUnit[u]}: layer_operating_cost[l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_PRICE[l]) * TIME_STEP_DURATION * OCCURRANCE;\n"
        # Constraints to be added depending on whether the maximum power output of the utilities depends on the time step or not
        if len(self.units_with_time_dependent_maximum_power) > 0:
            self.mod_string += "s.t. component_load_standard{u in standardUtilities, l in layersOfUnit[u], t in timeSteps: u in utilitiesWithFixedMaxPower}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l];"
            self.mod_string += "s.t. component_load_time_dependent{u in utilitiesWithTimeDependentMaxPower, l in layersOfUnit[u], t in timeSteps}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l] * POWER_MAX_REL[u,l,t];"
            self.mod_string += "s.t. market_limits_standard{u in markets, l in layersOfUnit[u], t in timeSteps: u in utilitiesWithFixedMaxPower}: POWER_MAX[u,l] <= power[u,l,t] <= 0;"
            self.mod_string += "s.t. market_limits_time_dependent{u in utilitiesWithTimeDependentMaxPower, l in layersOfUnit[u], t in timeSteps}: POWER_MAX[u,l] * POWER_MAX_REL[u,l,t] <= power[u,l,t] <= 0;"
        else:
            self.mod_string += "s.t. component_load{u in standardUtilities, l in layersOfUnit[u], t in timeSteps}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l];"
            self.mod_string += "s.t. market_limits{u in markets, l in layersOfUnit[u], t in timeSteps}: POWER_MAX[u,l] <= power[u,l,t] <= 0;"
        # Constraints to be added depending on whether there are storage units in the problem
        if self.has_storage:
            self.mod_string += """
                s.t. storage_balance{u in storageUnits, l in layersOfUnit[u], t in timeSteps}: energyStorageLevel[u,l,t] = (if t == 1 \n
                    then \n
                        energyStorageLevel0[u,l] - power[u,l,t]*TIME_STEP_DURATION \n
                    else 
                        energyStorageLevel[u,l,t-1] - power[u,l,t]*TIME_STEP_DURATION \n
                    );\n

                s.t. storage_cyclic_constraint{u in storageUnits, l in layersOfUnit[u]}: \n
                    energyStorageLevel0[u,l] >= (if STORAGE_CYCLIC_ACTIVE = 1\n
                    then \n
                        energyStorageLevel[u,l,card(timeSteps)] \n
                    else\n
                        0\n
                    );\n
                s.t. storage_max_energy{u in storageUnits, l in layersOfUnit[u], t in timeSteps}:\n
                    energyStorageLevel[u,l,t] <= size[u];\n
                s.t. storage_max_energy2{u in storageUnits}:\n
                    size[u] <= ENERGY_MAX[u];\n
                s.t. storage_max_ch_power{u in storageUnits, l in layersOfUnit[u], t in timeSteps}: \n
                    power[u,l,t] >= -size[u] * CRATE[u];\n
                s.t. storage_max_dis_power{u in storageUnits, l in layersOfUnit[u], t in timeSteps}: \n
                    power[u,l,t] <= size[u] * ERATE[u];\n
                s.t. storage_ch_power_cost{u in storageUnits, l in layersOfUnit[u], ch in chargingUtilitiesOfStorageUnit[u], t in timeSteps}:\n
                    power[ch,l,t] <= size[u] * CRATE[u];\n
                s.t. storage_dis_power_cost{u in storageUnits, l in layersOfUnit[u], dis in dischargingUtilitiesOfStorageUnit[u], t in timeSteps}:\n
                    power[dis,l,t] >= -size[u] * ERATE[u];\n
                s.t. charging_power_only_positive{u in storageUnits, l in layersOfUnit[u], ch in chargingUtilitiesOfStorageUnit[u], t in timeSteps}:\n
                    power[ch,l,t] >= 0;\n
                s.t. discharging_power_only_negative{u in storageUnits, l in layersOfUnit[u], dis in dischargingUtilitiesOfStorageUnit[u], t in timeSteps}:\n
                    power[dis,l,t] <= 0;\n
            """
        
class AmplDat():
    # Class used to handle data for ampl problem
    def __init__(self, ampl_problem: amplpy.AMPL, mod: AmplMod):
        # Initialize general data
        self.ampl: amplpy.AMPL = ampl_problem
        self.mod: AmplMod = mod
        self.general_parameters: list = []
        # Initialize sets
        self.units: list = []
        self.layers: list = []
        self.timeSteps: list = []
        self.processes: list = []
        self.markets: list = []
        self.standardUtilities: list = []
        self.layersOfUnit: dict = {}
        self.storageUnits: list = []
        self.chargingUtilitiesOfStorageUnit: dict[list] = {}
        self.dischargingUtilitiesOfStorageUnit: dict[list] = {}
        # Initialize parameters
        self.POWER_MAX = {}
        self.POWER = {}
        self.TIME_STEP_DURATION = None
        self.OCCURRANCE = None
        self.SPECIFIC_INVESTMENT_COST_ANNUALIZED = {}
        self.ENERGY_PRICE = {}
        if len(self.mod.units_with_time_dependent_maximum_power) > 0:
            self.POWER_MAX_REL = {}
        if len(self.mod.layers_with_time_dependent_price) > 0:
            self.ENERGY_PRICE_VARIATION = {}
        if self.mod.has_storage:
            self.ENERGY_MAX, self.CRATE, self.ERATE = {}, {}, {}
            self.STORAGE_CYCLIC_ACTIVE = None
    
    def parse_sets_data(self, units: list, layers: list, parameters: ProblemParameters):
        self.units = [unit.name for unit in units]
        self.layers = [layer.name for layer in layers]
        self.timeSteps = [t for t in range(0,parameters.simulation_horizon)]
        self.processes = [unit.name for unit in units if isinstance(unit, Process)]
        self.markets = [unit.name for unit in units if isinstance(unit, Market)]
        self.standardUtilities = [unit.name for unit in units if isinstance(unit, StandardUtility)]
        self.layersOfUnit = {unit.name: unit.layers for unit in units}
        # Parsing sets that only exist if there are storage units
        if self.mod.has_storage:
            self.storageUnits = [unit.name for unit in units if isinstance(unit, StorageUnit)]
            self.chargingUtilitiesOfStorageUnit = {unit.name: [unit.chargingUnit] for unit in units if isinstance(unit, StorageUnit)}
            self.dischargingUtilitiesOfStorageUnit = {unit.name: [unit.dischargingUnit] for unit in units if isinstance(unit, StorageUnit)}

    def write_sets_data_to_amplpy(self):
        # Writes the problem data to amplpy
        SETS = ['layers', 'timeSteps', 'processes', 'markets', 'standardUtilities']
        for s in SETS:
            self.ampl.set[s] = self.getattr(s)
        for unit in self.units:
            self.ampl.set[unit] = self.layersOfUnit[unit]
        # Writes the storage-related set
        if self.mod.has_storage:
            self.ampl['storageUnits'] = self.storageUnits
            for unit in self.storageUnits:
                self.ampl['chargingUtilitiesOfStorageUnit'][unit] = self.chargingUtilitiesOfStorageUnit[unit]
                self.ampl['dischargingUtilitiesOfStorageUnit'][unit] = self.dischargingUtilitiesOfStorageUnit[unit]

    def pars_parameters_data(self, units: list, parameters: ProblemParameters):
        # Parses data for the parameters
        # First, general parameters
        for param_name, param_value in parameters.ampl_parameters.items():
            self.general_parameters.append(param_name)
            self.setattr(param_name, param_value)
        for unit in units:
            if isinstance(unit, Process):
                for layer in unit.layers:
                    self.POWER[unit.name][layer] = list(unit.power[layer])
            elif isinstance(unit, Utility):
                self.SPECIFIC_INVESTMENT_COST_ANNUALIZED[unit.name] = unit.specific_annualized_capex
                self.POWER_MAX[unit.name] = {}
                for layer in unit.layers:
                    if unit in self.mod.units_with_time_dependent_maximum_power:
                        self.POWER_MAX[unit.name][layer] = max(unit.power_max[layer])
                        self.POWER_MAX_REL[unit.name][layer] = [x / self.POWER_MAX[unit.name][layer] for x in unit.power_max[layer]]
                    else:
                        self.POWER_MAX[unit.name][layer] = unit.power_max[layer]
                    if isinstance(unit, Market):
                        if layer in self.mod.layers_with_time_dependent_price:
                            self.ENERGY_PRICE[layer] = sum(unit.energy_price[layer]) / len(unit.energy_price[layer])
                            self.ENERGY_PRICE_VARIATION[layer] = [x / self.ENERGY_PRICE[layer] for x in unit.energy_price[layer]]
                        else:
                            self.ENERGY_PRICE[layer] = unit.energy_price[layer]
                if isinstance(unit, StorageUnit):
                    self.ENERGY_MAX[unit.name] = unit.capacity
                    self.CRATE[unit.name] = unit.c_rate
                    self.ERATE[unit.name] = unit.e_rate
            else:
                raise TypeError(f'Unit {unit.name} has wrong unit type: should be either Process or Utility')

    def write_parameters_to_amplpy(self):
        # Writes the problem data to amplpy
        for param_name in self.general_parameters:
            self.ampl.param[param_name] = self.getattr(param_name)
        # Writing power from processes
        for process in self.processes:
            self.ampl.param['POWER'] = self.POWER[process]
        # Writing specific investment cost data
        self.ampl.param['SPECIFIC_INVESTMENT_COST_ANNUALIZED'] = self.SPECIFIC_INVESTMENT_COST_ANNUALIZED
        # Writing power max for utilities
        for utility in self.standardUtilities:
            self.ampl.param['POWER_MAX'][utility] = self.POWER_MAX[utility]
            if utility in self.mod.units_with_time_dependent_maximum_power:
                self.ampl.param['POWER_MAX_REL'][utility] = self.POWER_MAX_REL[utility]
        # Writing market parameters data
        self.ampl.param['ENERGY_PRICE'] = self.ENERGY_PRICE
        if len(self.mod.layers_with_time_dependent_price) > 0:
            self.ampl.param['ENERGY_PRICE_VARIATION'] = self.ENERGY_PRICE_VARIATION
        if len(self.storageUnits) > 0:
            self.ampl.param['ENERGY_MAX'] = self.ENERGY_MAX
            self.ampl.param['CRATE'] = self.CRATE
            self.ampl.param['ERATE'] = self.ERATE
