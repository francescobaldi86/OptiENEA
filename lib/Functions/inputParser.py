from lib.Functions.helpers import read_input_from_file
from lib.Functions.helpers import addToSet
from lib.Functions.simulationManager import calculateAnnualizedInvestmentCost
from lib.Functions.simulationManager import setRelativeMaxPower

import pandas as pd



def parse_sets(sets, units):
    """
    This function parses the input file where problem units are summarized
    """
    layers, market_utilities, utilities, processes, storage_units = set(), set(), set(), set(), set()
    layers_of_unit, main_layer_of_unit, charging_utilities_of_unit, discharging_utilities_of_unit = dict(), dict(), dict(), dict()
    for name, unit in units.items():
        # Layers are read for each unit
        layers = addToSet(layers, unit["Layers"])
        if isinstance(unit["Layers"], str):
            layers_of_unit[name] = [unit["Layers"]]
            main_layer_of_unit[name] = {unit["Layers"]}
        else:
            layers_of_unit[name] = unit["Layers"]
            main_layer_of_unit[name] = {unit["MainLayer"]}
        # Other input information is read differently for different unit types
        if "Utility" in unit["Type"]:
            utilities.add(name)
            # This is only for charging utilities related to storage units
            if unit["Type"] == "ChargingUtility":
                charging_utilities_of_unit[unit["StorageUnit"]] = {name}
            # This is only for discharging utilities related to storage unit
            elif unit["Type"] == "DischargingUtility":
                discharging_utilities_of_unit[unit["StorageUnit"]] = {name}
        elif unit["Type"] == "Storage":
                storage_units.add(name)
        elif unit["Type"] == "Market":
                market_utilities.add(name)
        if unit["Type"] == "Process":
            processes.add(name)
            temp = unit["Power"]
    # Finally storing the problem sets in appropriate format
    sets["0"].update({"layers": layers, "standardUtilities": utilities, "processes": processes, "storageUnits": storage_units, "markets": market_utilities})
    sets["1"].update(
        {"layersOfUnit": layers_of_unit, 'mainLayerOfUnit': main_layer_of_unit,
         "chargingUtilitiesOfStorageUnit": charging_utilities_of_unit, "dischargingUtilitiesOfStorageUnit": discharging_utilities_of_unit}
         )
    return sets

def parse_parameters(problem):
    """
    This function prepares the "reference" parameters set based on reference values
    """
    sets = problem.sets
    parameters = problem.parameters
    POWER_MAX, POWER, POWER_MAX_REL = dict(), dict(), dict()
    ENERGY_AVERAGE_PRICE, ENERGY_PRICE_VARIATION, SPECIFIC_INVESTMENT_COST_ANNUALIZED = dict(), dict(), dict()  # parameters
    CRATE, ERATE, ENERGY_MAX = dict(), dict(), dict()
    for name, unit in problem.units.items():
        if "Utility" in unit["Type"]:
            POWER_MAX[name] = dict()
            POWER_MAX_REL[name] = dict()
            if "InvestmentCost" in unit.keys():
                SPECIFIC_INVESTMENT_COST_ANNUALIZED[name] = calculateAnnualizedInvestmentCost(
                    unit["InvestmentCost"], unit["Lifetime"], problem.general_parameters["InterestRate"])
            else:
                SPECIFIC_INVESTMENT_COST_ANNUALIZED[name] = 0
            for idx in range(len(sets["1"]["layersOfUnit"][name])):
                POWER_MAX[name][sets["1"]["layersOfUnit"][name][idx]] = unit["MaxPower"][idx]
                if "ActivationFrequency" in unit.keys():
                    POWER_MAX_REL[name][sets["1"]["layersOfUnit"][name][idx]] = setRelativeMaxPower(
                        unit["ActivationFrequency"][idx], problem.general_parameters["NT"])
                if "TimeDependentAvailability" in unit.keys():
                    if unit["TimeDependentAvailability"] == "file":
                        temp = pd.read_csv(problem.problem_folder + name + ".csv", index_col=0)
                        for lay in temp.keys():
                            POWER_MAX_REL[name][lay] = temp[lay].to_dict()   # Useful, for instance, in the case of solar panels and wind turbines. The input file must contain a vector representing the ratio between the maximum power generation at time step t over the reference output.     


        if unit["Type"] == "Market": # This is only for units of type "Market"
            POWER_MAX[name] = dict()
            POWER_MAX_REL[name] = dict()
            ENERGY_AVERAGE_PRICE[name] = dict()
            for idx in range(len(sets["1"]["layersOfUnit"][name])):
                POWER_MAX[name][sets["1"]["layersOfUnit"][name][idx]] = unit["MaxPower"][idx]
                ENERGY_AVERAGE_PRICE[name][sets["1"]["layersOfUnit"][name][idx]] = float(unit["AveragePrice"][idx])
            if unit["TimeDependentPrice"] == "file":
                ENERGY_PRICE_VARIATION[name] = dict()
                temp = pd.read_csv(problem.problem_folder + name + ".csv", index_col=0)
                for col in temp.keys():
                    ENERGY_PRICE_VARIATION[name][col] = temp[col].to_dict()
					
        if unit["Type"] == "Storage":
            CRATE[name], ERATE[name], = float(unit["Rates"][0]), float(unit["Rates"][1])
            ENERGY_MAX[name] = float(unit["MaxEnergy"])
            SPECIFIC_INVESTMENT_COST_ANNUALIZED[name] = calculateAnnualizedInvestmentCost(
                unit["InvestmentCost"], unit["Lifetime"], problem.general_parameters["InterestRate"])
				
        if unit["Type"] == "Process":
            temp = unit["Power"]
            if temp == "file":
                POWER[name] = dict()
                temp = pd.read_csv(problem.problem_folder + name + ".csv", index_col=0)
                for lay in temp.keys():
                    if "ProcessType" in unit.keys():
                        if unit["ProcessType"] == "Demand":
                            # If the process is of type "demand", we must ensure that all its values are <= 0
                            if all(temp[lay] <= 0):
                                POWER[name][lay] = temp[lay].to_dict()  # Just a check: if all values are negative, we do nothing 
                            elif all(temp[lay] >= 0):
                                POWER[name][lay] = (-temp[lay]).to_dict()  # If all values are positive, we simply multiply all of them by -1
                            else:
                                raise Exception("There is a problem with process unit " + name + " that should be of type 'Demand', but has both positive and negative input values")
                        elif unit["ProcessType"] == "Generation":
                            # If the process is of type "generation", we must ensure that all its values are >= 0
                            if all(temp[lay] >= 0):
                                POWER[name][lay] = temp[lay].to_dict()  # Just a check: if all values are positive, we do nothing 
                            elif all(temp[lay] <= 0):
                                POWER[name][lay] = (-temp[lay]).to_dict()  # If all values are negative, we simply multiply all of them by -1
                            else:
                                raise Exception("There is a problem with process unit " + name + " that should be of type 'Generation', but has both positive and negative input values")
            else:
                POWER[name] = temp

    parameters["1"].update({
        "CRATE": CRATE, "ERATE": ERATE, "ENERGY_MAX": ENERGY_MAX, "SPECIFIC_INVESTMENT_COST_ANNUALIZED": SPECIFIC_INVESTMENT_COST_ANNUALIZED})
    parameters["2"].update({"POWER_MAX": POWER_MAX, "ENERGY_AVERAGE_PRICE": ENERGY_AVERAGE_PRICE})
    parameters["3"].update({"POWER": POWER, "POWER_MAX_REL": POWER_MAX_REL, "ENERGY_PRICE_VARIATION": ENERGY_PRICE_VARIATION})
    return parameters