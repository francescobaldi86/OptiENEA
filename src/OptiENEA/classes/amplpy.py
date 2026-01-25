import OptiENEA.classes.unit as ut
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
    has_minimum_installed_power: bool
    has_units_with_minimum_size_if_installed: bool

    def __init__(self, problem):
        super().__init__()
        self.has_storage = False
        self.has_capex = False
        self.has_time_dependent_power = False
        self.has_time_dependent_max_power = False
        self.has_time_dependent_energy_prices = False
        self.has_minimum_installed_power = False
        self.has_units_with_minimum_size_if_installed = False
        self.has_units_operated_only_on_off = False
        self.has_typical_periods = False
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
        # Check if problem has time-dependent power input
        for _, unit in self.problem.units.items():
            if unit.has_time_dependent_power:
                self.has_time_dependent_power = True
            if self.has_time_dependent_power:
                break
        # Check if problem has capex
        if not self.problem.parameters['SPECIFIC_INVESTMENT_COST_ANNUALIZED'].content.empty:
            self.has_capex = True
        # Check if problem has minimum installed power
        if not self.problem.parameters['POWER_MIN'].content.empty:
            self.has_minimum_installed_power = True
        # Check if problem has time-dependent max power
        if not self.problem.parameters['POWER_MAX_REL'].content.empty:
            self.has_time_dependent_max_power = True
        # Check if problem has storage units
        if not self.problem.parameters['ENERGY_MAX'].content.empty:
            self.has_storage = True
        # Check if problem has time-dependent energy prices
        if not self.problem.parameters['ENERGY_PRICE_VARIATION'].content.empty:
            self.has_time_dependent_energy_prices = True
        # Check if problem has units that can only be installed with a minmium size:
        if len(self.problem.sets['unitsWithMinimumSizeIfInstalled'].content) > 0:
            self.has_units_with_minimum_size_if_installed = True
        # Check if the problem has units that can only be operated on an on/off basis
        if len(self.problem.sets['unitsOnOff'].content) > 0:
            self.has_units_operated_only_on_off = True
        # Check if problem has typical periods
        if self.problem.has_typical_periods:
            self.has_typical_periods = True

    def write_mod_file(self):
        self.write_sets()
        self.write_parameters()
        self.write_variables()
        self.write_objective()
        self.write_base_constraints()
        self.write_additional_constraints()
        if self.has_typical_periods:
            self.typical_periods_transformation()
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
        if self.has_units_with_minimum_size_if_installed:
            temp_sets.append("set unitsWithMinimumSizeIfInstalled within nonmarketUtilities;")
        if self.has_units_operated_only_on_off:
            temp_sets.append("set unitsOnOff within nonmarketUtilities;")
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
        temp_params.append("param ENERGY_PRICE_VARIATION{m in markets, l in layersOfUnit[m], t in timeSteps} default 1;")
        temp_params.append("param BIG_M default 100;")
        if self.has_minimum_installed_power:
            temp_params.append("param POWER_MIN{u in nonmarketUtilities} default 0;")
        if self.has_storage:
            temp_params.append("param ENERGY_MAX{u in storageUnits} default 0;")
            temp_params.append("param CRATE{u in storageUnits} default 1;")
            temp_params.append("param ERATE{u in storageUnits} default 1;")
            temp_params.append("param ERROR_MARGIN_ON_CYCLIC_SOC default 0.1;")
            idx = temp_params.index("param POWER_MAX{u in utilities, l in layersOfUnit[u]} default 0;")
            temp_params[idx] = "param POWER_MAX{u in nonStorageUtilities, l in layersOfUnit[u]} default 0;"
            idy = temp_params.index("param POWER_MAX_REL{u in utilities, l in layersOfUnit[u], t in timeSteps} default 1;")
            temp_params[idy] = "param POWER_MAX_REL{u in nonStorageUtilities, l in layersOfUnit[u], t in timeSteps} default 1;"
        if self.has_units_with_minimum_size_if_installed:
            temp_params.append("param SIZE_MIN_IF_INSTALLED{u in unitsWithMinimumSizeIfInstalled} default 0;")
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
        if self.has_units_with_minimum_size_if_installed:
            temp_vars.append("var ips{u in unitsWithMinimumSizeIfInstalled} binary;")
        if self.has_units_operated_only_on_off:
            temp_vars.append("var ips_t{u in unitsOnOff, t in timeSteps} binary;")
        self.mod_string += "\n".join(temp_vars) + "\n\n\n"

    def write_objective(self):
        # Adds the problem objective to the mod file string
        self.mod_string += "/* OBJECTIVE FUNCTION */\n\n"
        self.mod_string += self.problem.objective.objective
        for constraint in self.problem.objective.constraints:
            self.mod_string += constraint
        self.mod_string += "\n\n"

    def write_base_constraints(self):
        # Adds the problem constraints to the mod file string
        temp_constraints = []
        temp_constraints.append("/* CONSTRAINTS */\n")
        temp_constraints.append("s.t. calculate_opex: OPEX = sum{(u,l) in outputMarketLayers} layer_operating_cost[u,l];")
        temp_constraints.append("s.t. layer_balance{l in layers, t in timeSteps}: sum{u in unitsOfLayer[l]} (power[u,l,t]) = 0;")
        temp_constraints.append("s.t. process_power{p in processes, l in layersOfUnit[p], t in timeSteps}: power[p,l,t] = -POWER[p,l,t];")
        # Constraints to be added depending on whether we are calculating the cost of the investment or not
        if self.has_capex:
            temp_constraints.append("s.t. component_sizing{u in standardUtilities, l in mainLayerOfUnit[u], t in timeSteps}: size[u] >= ics[u,t] * abs(POWER_MAX[u,l]);")
            temp_constraints.append("s.t. calculate_capex: CAPEX = sum{u in nonmarketUtilities} unitAnnualizedInvestmentCost[u];")
            temp_constraints.append("s.t. calculate_investment_cost{u in nonmarketUtilities}: unitAnnualizedInvestmentCost[u] = size[u] * SPECIFIC_INVESTMENT_COST_ANNUALIZED[u];")
            temp_constraints.append("s.t. calculate_totex: TOTEX = CAPEX + OPEX;")
        # Constraints added only if the problem has units with a minimum installed size
        if self.has_minimum_installed_power:
            temp_constraints.append("s.t. minimum_installed_power{u in nonmarketUtilities}: size[u] >= POWER_MIN[u];")
        # Constraints to be added depending on whether energy prices depend on the time step or not
        temp_constraints.append("s.t. calculate_operating_cost_time_dependent{u in markets, l in layersOfUnit[u]}: layer_operating_cost[u,l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_AVERAGE_PRICE[u,l] * ENERGY_PRICE_VARIATION[u,l,t]) * TIME_STEP_DURATION * OCCURRANCE;")        
        # Constraints to be added depending on whether the maximum power output of the utilities depends on the time step or not
        temp_constraints.append("s.t. component_load{u in standardUtilities, l in layersOfUnit[u], t in timeSteps}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l] * POWER_MAX_REL[u,l,t];")
        # temp_constraints.append("s.t. market_limits{u in markets, l in layersOfUnit[u], t in timeSteps}: POWER_MAX[u,l] * POWER_MAX_REL[u,l,t] <= power[u,l,t] <= 0;")
        temp_constraints.append("s.t. purchase_market_limits{u in markets, l in layersOfUnit[u], t in timeSteps: POWER_MAX[u,l] >= 0}: 0 <= power[u,l,t] <= POWER_MAX[u,l] * POWER_MAX_REL[u,l,t];")
        temp_constraints.append("s.t. selling_market_limits{u in markets, l in layersOfUnit[u], t in timeSteps: POWER_MAX[u,l] <= 0}: POWER_MAX[u,l] * POWER_MAX_REL[u,l,t] <= power[u,l,t] <= 0;")
        # Constraints to be added if problem has units with a minimum size if installed
        if self.has_units_with_minimum_size_if_installed:
            temp_constraints.append("s.t. component_sizing_with_minimum_size_if_installed{u in unitsWithMinimumSizeIfInstalled, l in mainLayerOfUnit[u]} : size[u] >= SIZE_MIN_IF_INSTALLED[u] * ips[u];")
            temp_constraints.append("s.t. constraint_on_ips{u in unitsWithMinimumSizeIfInstalled, t in timeSteps}: ics[u,t] <= ips[u];")
        if self.has_units_operated_only_on_off:
            temp_constraints.append("s.t. component_load_onoff{u in unitsOnOff, t in timeSteps}: ics[u,t] == ips_t[u,t];")
        # Constraints to be added depending on whether there are storage units in the problem
        if self.has_storage:
            temp_constraints.append("s.t. storage_balance{u in storageUnits, l in layersOfUnit[u], t in timeSteps}:")
            temp_constraints.append("\tenergyStorageLevel[u,l,t] = (if t == 0")
            temp_constraints.append("\t\tthen")
            temp_constraints.append("\t\t\tenergyStorageLevel0[u,l] - power[u,l,t]*TIME_STEP_DURATION")
            temp_constraints.append("\t\telse")
            temp_constraints.append("\t\t\tenergyStorageLevel[u,l,t-1] - power[u,l,t]*TIME_STEP_DURATION")
            temp_constraints.append("\t);")
            temp_constraints.append("s.t. storage_cyclic_constraint_high{u in storageUnits, l in layersOfUnit[u]}:")
            temp_constraints.append("\tenergyStorageLevel[u,l,1] - energyStorageLevel[u,l,card(timeSteps)-1] >= 0;")
            temp_constraints.append("s.t. storage_cyclic_constraint_low{u in storageUnits, l in layersOfUnit[u]}:")
            temp_constraints.append("\tenergyStorageLevel[u,l,1] - energyStorageLevel[u,l,card(timeSteps)-1] <= ERROR_MARGIN_ON_CYCLIC_SOC * size[u];")
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
        

    def write_additional_constraints(self):
        additional_constraints = []
        for constraint_type, constraint in self.problem.additional_constraints_data.items():
            additional_constraints.append(f"param {constraint['parameter name']};")
            additional_constraints.append(f"s.t. {constraint['name']}")
            additional_constraints.append(f"{{u in units, l in layersOfUnit[u]: u == '{constraint['unit name']}' && l == '{constraint['layer name']}'}}:")
            additional_constraints.append(f"\tabs(sum{{t in timeSteps}} power[u,l,t] * TIME_STEP_DURATION * OCCURRANCE) <= {constraint['parameter name']};")
        self.mod_string += "\n".join(additional_constraints) + "\n\n\n"

    def typical_periods_transformation(self):
        self.mod_string = self.mod_string.replace("set timeSteps;", "set typicalPeriods;\nset timeStepsOfPeriod{tp in typicalPeriods};")
        self.mod_string = self.mod_string.replace("param OCCURRANCE;", "param OCCURRANCE{tp in typicalPeriods};")
        self.mod_string = self.mod_string.replace("* OCCURRANCE;", "* OCCURRANCE[tp];")
        self.mod_string = self.mod_string.replace('t in timeSteps', 'tp in typicalPeriods, t in timeStepsOfPeriod[tp]')
        self.mod_string = self.mod_string.replace('t]','tp,t]')
        self.mod_string = self.mod_string.replace('l,t-1]','l,tp,t-1]')
        self.mod_string = self.mod_string.replace("energyStorageLevel[u,l,", "energyStorageLevel[u,l,tp,")        
        self.mod_string = self.mod_string.replace("{u in storageUnits, l in layersOfUnit[u]}",
                                                  "{u in storageUnits, l in layersOfUnit[u], tp in typicalPeriods}")
        self.mod_string = self.mod_string.replace("energyStorageLevel0[u,l]", "energyStorageLevel0[u,l,tp]")
        self.mod_string = self.mod_string.replace("tp,tp,", 'tp,')
        self.mod_string = self.mod_string.replace("(timeSteps)", "(timeStepsOfPeriod[tp])")

    def write_sets_to_amplpy(self):
        # Writes problem data about sets to amplpy
        for name, problem_set in self.problem.sets.items():
            if all([problem_set.content != set(), problem_set.content != dict()]):
                self.set[name] = problem_set.content

    def write_parameters_to_amplpy(self):
        # Writes the problem data to amplpy
        for parameter_name, parameter in self.problem.parameters.items():
            if not parameter.is_empty(): 
                self.param[parameter_name] = parameter.content    
