
from problem import Problem
from unit import *


class AmplMod():
    def __init__():
        mod_string = ""
        self.has_storage = False
        self.has_capex = False
        self.units_with_time_dependent_maximum_power = []
        self.layers_with_time_dependent_price = []

    def parse_problem_units(self, problem: Problem):
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
    
    def parse_problem_objective(self, objective: str)

            

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
            self.mod_string += "param ENERGY_PRICE_VARIATION{l in layers, t in timeSteps} default 1;\n"
        if len(self.units_with_time_dependent_maximum_power):
            self.mod_string += "param POWER_MAX_REL{u in utilities, l in layersOfUnit[u], t in timeSteps} default 1;\n"
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
            var OPEX;
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


    def write_constraints(self):
        # Adds the problem constraints to the mod file string