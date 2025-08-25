from OptiENEA.classes.unit import Utility, Process, StorageUnit, Market, StandardUtility
from OptiENEA.classes.objective_function import ObjectiveFunction
import pandas as pd
import amplpy

class AmplProblem(amplpy.AMPL):
    has_storage: bool
    has_capex: bool
    has_time_dependent_power: bool
    has_time_dependent_max_power: bool
    has_time_dependent_energy_prices: bool
    units_with_time_dependent_maximum_power: list
    layers_with_time_dependent_price: list

    def __init__(self, problem):
        super().__init__()
        self.has_storage = False
        self.has_capex = False
        self.has_time_dependent_power = False
        self.has_time_dependent_max_power = False
        self.has_time_dependent_energy_prices = False
        self.units_with_time_dependent_maximum_power = []
        self.layers_with_time_dependent_price = []
        self.problem = problem
        self.mod_string = f'/* MOD FILE */\n\n/* Problem name: {problem.name} */\n\n'

    def get_mod_file(self):
        return self.mod_string

    def load_sets_data(self, sets_data):
        # Writes the problem data to amplpy
        for s in sets_data:
            if sets_data.indexed_over:
                for subset_name, subset_data in s.items():
                    self.set[s.name][subset_name] = subset_data
            else:
                self.set[s.name] = list(s.content)

    def parse_problem_settings(self):
        for _, unit in self.problem.units.items():
            if isinstance(unit, Process):
                if unit.has_time_dependent_power:
                    self.has_time_dependent_power = True
            if isinstance(unit, Utility):
                if unit.specific_capex >= 1:
                    self.has_capex = True
                if isinstance(unit, StandardUtility):
                    if unit.has_time_dependent_max_power:
                        self.has_time_dependent_max_power = True
                elif isinstance(unit, StorageUnit):
                    self.has_storage = True
                elif isinstance(unit, Market):
                    if unit.has_time_dependent_energy_prices:
                        self.has_time_dependent_energy_prices = True
                

    def write_mod_file(self):
        self.write_sets()
        self.write_parameters()
        self.write_variables()
        self.write_objective()
        self.write_constraints()
        self.eval(self.mod_string)

    def write_sets(self):
        temp_sets = []
        # Adds the problem sets to the mod file string
        temp_sets.append("/* PROBLEM SETS */\n")
        temp_sets.append("set timeSteps;")
        temp_sets.append("set processes;")
        temp_sets.append("set markets;")
        temp_sets.append("set standardUtilities;")
        temp_sets.append("set utilities := standardUtilities union markets;")
        temp_sets.append("set units := utilities union processes;")
        temp_sets.append("set layers;")
        temp_sets.append("set layersOfUnit{u in units};")
        temp_sets.append("set mainLayerOfUnit{u in units};")
        temp_sets.append("set unitsOfLayer{l in layers} := setof{u in units : l in layersOfUnit[u]} u;")
        temp_sets.append("set outputMarketLayers := setof{u in markets, l in layersOfUnit[u]} (u, l);")
        temp_sets.append("set nonmarketUtilities := utilities diff markets;")
        if self.has_storage:
            temp_sets.append("set chargingUtilitiesOfStorageUnit{u in storageUnits} within utilities;")
            temp_sets.append("set dischargingUtilitiesOfStorageUnit{u in storageUnits} within utilities;")
            temp_sets.append("set nonStorageUtilities within utilities := utilities diff storageUnits;")
            idx = temp_sets.index("set utilities := standardUtilities union markets;")
            temp_sets[idx] = "set utilities := standardUtilities union markets union storageUnits;"
            temp_sets.insert(idx-1, "set storageUnits;")
        if self.has_time_dependent_max_power:
            temp_sets.append("utilitiesWithTimeDependentMaxPower within utilities;")
            temp_sets.append("utilitiesWithFixedMaxPower: utilities diff utilitiesWithTimeDependentMaxPower;")
        if self.has_time_dependent_energy_prices:
            temp_sets.append("layersWithTimeDependentPrice within layers;")
            temp_sets.append("layersWithFixedPrice: layers diff layersWithTimeDependentPrice;")
        self.mod_string += "\n".join(temp_sets) + "\n\n\n"

    def write_parameters(self):
        temp_params = []
        # Adds the problem parameters to the mod file string
        temp_params.append("/* PROBLEM PARAMETERS */\n")
        temp_params.append("param POWER_MAX{u in utilities, l in layersOfUnit[u]} default 0;")
        temp_params.append("param POWER{p in processes, l in layersOfUnit[p], t in timeSteps};")
        temp_params.append("param TIME_STEP_DURATION;")
        temp_params.append("param OCCURRANCE;")
        temp_params.append("param SPECIFIC_INVESTMENT_COST_ANNUALIZED{u in utilities} default 0;")
        temp_params.append("param ENERGY_AVERAGE_PRICE{m in markets, l in layersOfUnit[m]} default 0;")
        temp_params.append("param POWER_MAX_REL{u in utilities, l in layersOfUnit[u], t in timeSteps} default 1;")
        if self.has_time_dependent_energy_prices:
            temp_params.append("param ENERGY_PRICE_VARIATION{m in markets, l in layersOfUnit[m], t in timeSteps} default 1;")
        if self.has_storage:
            temp_params.append("param ENERGY_MAX{u in storageUnits} default 0;")
            temp_params.append("param CRATE{u in storageUnits} default 1;")
            temp_params.append("param ERATE{u in storageUnits} default 1;")
            temp_params.append("param STORAGE_CYCLIC_ACTIVE default 1;")
            idx = temp_params.index("param POWER_MAX{u in utilities, l in layersOfUnit[u]} default 0;")
            temp_params[idx] = "param POWER_MAX{u in nonStorageUtilities, l in layersOfUnit[u]} default 0;"
            idy = temp_params.index("param POWER_MAX_REL{u in utilities, l in layersOfUnit[u], t in timeSteps} default 1;")
            temp_params[idy] = "param POWER_MAX_REL{u in nonStorageUtilities, l in layersOfUnit[u], t in timeSteps} default 1;"
        self.mod_string += "\n".join(temp_params) + "\n\n\n"
        
    def write_variables(self):
        # Adds the problem sets to the mod file string
        temp_vars = []
        temp_vars.append("/* PROBLEM VARIABLES */\n")
        temp_vars.append("var power{u in units, l in layersOfUnit[u], t in timeSteps};")
        temp_vars.append("var layer_operating_cost{(u,l) in outputMarketLayers};")
        temp_vars.append("var ics{u in nonmarketUtilities, t in timeSteps} >= 0, <= 1;")
        temp_vars.append("var OPEX;")
        if self.has_storage:
            temp_vars.append("var energyStorageLevel{u in storageUnits, l in layersOfUnit[u], t in timeSteps} >=0;")
            temp_vars.append("var energyStorageLevel0{u in storageUnits, l in layersOfUnit[u]} >=0;")
        if self.has_capex:
            temp_vars.append("var unitAnnualizedInvestmentCost{u in nonmarketUtilities} >= 0;")
            temp_vars.append("var size{u in nonmarketUtilities} >= 0;")
            temp_vars.append("var CAPEX;")
            temp_vars.append("var TOTEX;")
        self.mod_string += "\n".join(temp_vars) + "\n\n\n"

    def write_objective(self):
        # Adds the problem objective to the mod file string
        self.mod_string += "/* OBJECTIVE FUNCTION */\n\n"
        self.mod_string += self.problem.objective.objective
        for constraint in self.problem.objective.constraints:
            self.mod_string += constraint
        self.mod_string += "\n\n"


    def write_constraints(self):
        # Adds the problem constraints to the mod file string
        temp_constraints = []
        temp_constraints.append("/* CONSTRAINTS */\n")
        temp_constraints.append("s.t. calculate_opex: OPEX = sum{(u,l) in outputMarketLayers} layer_operating_cost[u,l];")
        temp_constraints.append("s.t. layer_balance{l in layers, t in timeSteps}: sum{u in unitsOfLayer[l]} (power[u,l,t]) = 0;")
        temp_constraints.append("s.t. process_power{p in processes, l in layersOfUnit[p], t in timeSteps}: power[p,l,t] = POWER[p,l,t];")
        # Constraints to be added depending on whether we are calculating the cost of the investment or not
        if self.has_capex:
            temp_constraints.append("s.t. componentSizing{u in standardUtilities, l in mainLayerOfUnit[u], t in timeSteps}: size[u] >= ics[u,t] * abs(POWER_MAX[u,l]);")
            temp_constraints.append("s.t. calculate_capex: CAPEX = sum{u in nonmarketUtilities} unitAnnualizedInvestmentCost[u];")
            temp_constraints.append("s.t. calculate_investment_cost{u in nonmarketUtilities}: unitAnnualizedInvestmentCost[u] = size[u] * SPECIFIC_INVESTMENT_COST_ANNUALIZED[u];")
            temp_constraints.append("s.t. calculate_totex: TOTEX = CAPEX + OPEX;")
        # Constraints to be added depending on whether energy prices depend on the time step or not
        if self.has_time_dependent_energy_prices > 0:
            temp_constraints.append("s.t. calculate_operating_cost_time_dependent{u in markets, l in layersOfUnit[u]}: layer_operating_cost[u,l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_AVERAGE_PRICE[u,l] * ENERGY_PRICE_VARIATION[l,t]) * TIME_STEP_DURATION * OCCURRANCE;\n")
        else: 
            temp_constraints.append("s.t. calculate_operating_cost_standard{u in markets, l in layersOfUnit[u]}: layer_operating_cost[u,l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_AVERAGE_PRICE[u,l]) * TIME_STEP_DURATION * OCCURRANCE;")
        # Constraints to be added depending on whether the maximum power output of the utilities depends on the time step or not
        if self.has_time_dependent_max_power > 0:
            temp_constraints.append("s.t. component_load_standard{u in standardUtilities, l in layersOfUnit[u], t in timeSteps: u in utilitiesWithFixedMaxPower}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l];")
            temp_constraints.append("s.t. component_load_time_dependent{u in utilitiesWithTimeDependentMaxPower, l in layersOfUnit[u], t in timeSteps}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l] * POWER_MAX_REL[u,l,t];")
            temp_constraints.append("s.t. market_limits_standard{u in markets, l in layersOfUnit[u], t in timeSteps: u in utilitiesWithFixedMaxPower}: POWER_MAX[u,l] <= power[u,l,t] <= 0;")
            temp_constraints.append("s.t. market_limits_time_dependent{u in utilitiesWithTimeDependentMaxPower, l in layersOfUnit[u], t in timeSteps}: POWER_MAX[u,l] * POWER_MAX_REL[u,l,t] <= power[u,l,t] <= 0;")
        else:
            temp_constraints.append("s.t. component_load{u in standardUtilities, l in layersOfUnit[u], t in timeSteps}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l];")
            temp_constraints.append("s.t. market_limits{u in markets, l in layersOfUnit[u], t in timeSteps}: POWER_MAX[u,l] <= power[u,l,t] <= 0;")
        # Constraints to be added depending on whether there are storage units in the problem
        if self.has_storage:
            temp_constraints.append("s.t. storage_balance{u in storageUnits, l in layersOfUnit[u], t in timeSteps}:")
            temp_constraints.append("\tenergyStorageLevel[u,l,t] = (if t == 0")
            temp_constraints.append("\t\tthen")
            temp_constraints.append("\t\t\tenergyStorageLevel0[u,l] - power[u,l,t]*TIME_STEP_DURATION")
            temp_constraints.append("\t\telse")
            temp_constraints.append("\t\t\tenergyStorageLevel[u,l,t-1] - power[u,l,t]*TIME_STEP_DURATION")
            temp_constraints.append("\t);")
            temp_constraints.append("s.t. storage_cyclic_constraint{u in storageUnits, l in layersOfUnit[u]}:")
            temp_constraints.append("\tenergyStorageLevel0[u,l] >= (if STORAGE_CYCLIC_ACTIVE == 1")
            temp_constraints.append("\t\tthen")
            temp_constraints.append("\t\t\tenergyStorageLevel[u,l,card(timeSteps)-1] ")
            temp_constraints.append("\t\telse")
            temp_constraints.append("\t\t\t0")
            temp_constraints.append("\t);")
            temp_constraints.append("s.t. storage_max_energy{u in storageUnits, l in layersOfUnit[u], t in timeSteps}:")
            temp_constraints.append("\tenergyStorageLevel[u,l,t] <= size[u];")
            temp_constraints.append("s.t. storage_max_energy2{u in storageUnits}:")
            temp_constraints.append("\tsize[u] <= ENERGY_MAX[u];")
            temp_constraints.append("s.t. storage_max_ch_power{u in storageUnits, l in layersOfUnit[u], t in timeSteps}: ")
            temp_constraints.append("\tpower[u,l,t] >= -size[u] * CRATE[u];")
            temp_constraints.append("s.t. storage_max_dis_power{u in storageUnits, l in layersOfUnit[u], t in timeSteps}:")
            temp_constraints.append("\tpower[u,l,t] <= size[u] * ERATE[u];")
            temp_constraints.append("s.t. storage_ch_power_cost{u in storageUnits, l in layersOfUnit[u], ch in chargingUtilitiesOfStorageUnit[u], t in timeSteps}:")
            temp_constraints.append("\tpower[ch,l,t] <= size[u] * CRATE[u];")
            temp_constraints.append("s.t. storage_dis_power_cost{u in storageUnits, l in layersOfUnit[u], dis in dischargingUtilitiesOfStorageUnit[u], t in timeSteps}:")
            temp_constraints.append("\tpower[dis,l,t] >= -size[u] * ERATE[u];")
            temp_constraints.append("s.t. charging_power_only_positive{u in storageUnits, l in layersOfUnit[u], ch in chargingUtilitiesOfStorageUnit[u], t in timeSteps}:")
            temp_constraints.append("\tpower[ch,l,t] >= 0;")
            temp_constraints.append("s.t. discharging_power_only_negative{u in storageUnits, l in layersOfUnit[u], dis in dischargingUtilitiesOfStorageUnit[u], t in timeSteps}:")
            temp_constraints.append("\tpower[dis,l,t] <= 0;")
        self.mod_string += "\n".join(temp_constraints) + "\n\n\n"
        
    def write_sets_to_amplpy(self):
        # Writes problem data about sets to amplpy
        for name, problem_set in self.problem.sets.items():
            if all([problem_set != set(), problem_set != dict()]):
                self.set[name] = problem_set.content

    def write_parameters_to_amplpy(self):
        # Writes the problem data to amplpy
        for parameter_name, parameter in self.problem.parameters.items():
            if not parameter.is_empty(): 
                self.param[parameter_name] = parameter.content    




"""
class AmplDat():
    # Class used to handle data for ampl problem
    def __init__(self, ampl_problem: amplpy.AMPL, mod: AmplMod):
        # Initialize general data
        self.ampl: amplpy.AMPL = ampl_problem
        self.mod: AmplMod = mod
        self.general_parameters: list = []
        self.sets = {}
        # Initialize sets
        for set_name in PROBLEM_SETS['BASE_SETS']:
            self.sets[set_name] = Set(set_name)
        for set_name, indexed_over in PROBLEM_SETS['INDEXED_SETS']:
            self.sets[set_name] = Set(set_name, indexed_over)
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
"""