
from problem import Problem
from unit import Utility, Process, StorageUnit, Market
from objective_function import ObjectiveFunction


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
        for unit in problem.units:
            if isinstance(unit, Utility):
                if unit.specific_capex > 0.0:
                    self.has_capex = True  # Checks if the problem should calculate the CAPEX
                if isinstance(unit, StorageUnit):
                    self.has_storage = True  # Checks if there is any storage unit
                if len(unit.power_max) > 1:
                    self.units_with_time_dependent_maximum_power.append(unit.name)
                if isinstance(unit, Market):
                    for layer in unit.layers:
                        if len(unit.prices[layer]) > 1:
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
        if len(self.layers_with_time_dependent_price) > 0:
            self.mod_string += "layersWithTimeDependentPrice within layers;\n" 

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
            self.mod_string += "s.t. calculate_operating_cost_standard{u in markets, l in layersOfUnit[u]: l not in layersWithTimeDependentPrice}: layer_operating_cost[l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_PRICE[l]) * TIME_STEP_DURATION * OCCURRANCE;\n"
            self.mod_string += "s.t. calculate_operating_cost_time_dependent{u in markets, l in layersOfUnit[u]: l in layersWithTimeDependentPrice}: layer_operating_cost[l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_PRICE[l] * ENERGY_PRICE_VARIATION[l,t]) * TIME_STEP_DURATION * OCCURRANCE;\n"
        else: 
            self.mod_string += "s.t. calculate_operating_cost_standard{u in markets, l in layersOfUnit[u]}: layer_operating_cost[l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_PRICE[l]) * TIME_STEP_DURATION * OCCURRANCE;\n"
        # Constraints to be added depending on whether the maximum power output of the utilities depends on the time step or not
        if len(self.units_with_time_dependent_maximum_power) > 0:
            self.mod_string += "s.t. component_load_standard{u in standardUtilities, l in layersOfUnit[u], t in timeSteps: u not in utilitiesWithTimeDependentMaxPower}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l];"
            self.mod_string += "s.t. component_load_time_dependent{u in utilitiesWithTimeDependentMaxPower, l in layersOfUnit[u], t in timeSteps}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l] * POWER_MAX_REL[u,l,t];"
            self.mod_string += "s.t. market_limits_standard{u in markets, l in layersOfUnit[u], t in timeSteps: u not in utilitiesWithTimeDependentMaxPower}: POWER_MAX[u,l] <= power[u,l,t] <= 0;"
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
    def __init__(self, problem: Problem):
        self.units = [unit.name for unit in problem.units]
        self.layers = [layer.name for layer in problem.layers]
        self.time_steps = [t for t in range(0,problem.parameters.simulation_horizon)]
        self.

    def parse_data_from_units(units):
        # Reads data from the units of the problem
        
        for unit in units: