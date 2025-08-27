from OptiENEA.classes.layer import Layer
from OptiENEA.helpers.helpers import safe_to_list
import pandas as pd
import os
import yaml

with open(f'{os.path.dirname(os.path.realpath(__file__))}\\..\\lib\\units_default_values.yml') as stream:
    UNITS_DEFAULT_DATA = yaml.safe_load(stream)


class Unit:
    """
    Units are the basic obejct in OptiENEA. Every unit has a number of attributes
    """
    name: str
    layers: list
    main_layer: str
    info: dict
    ts_data: pd.DataFrame | None
    
    def __init__(self, name:str, info: dict, problem):
        # Assigning attribute values based on input
        self.name = name
        self.layers = info['Layers'] if isinstance(info['Layers'], list) else [info['Layers']]
        self.main_layer = info['Main layer'] if 'Main layer' in info.keys() else None
        # Checks that the main layer is one of the layers
        self.info = info
        self.problem = problem
        self.check_main_layer()
        self.ts_data = problem.raw_timeseries_data.loc[:, (name)] if name in problem.raw_timeseries_data.columns else None   
    
    def check_default_values(self, unit_type):
        # Assigns default values for the specific unit type to the related fields
        data = UNITS_DEFAULT_DATA[unit_type]
        for attribute_name, default_value in data.items():
            if attribute_name not in self.info.keys():
                self.info[attribute_name] = default_value
            elif self.info[attribute_name] == None:
                self.info[attribute_name] = default_value
            else:
                pass

    def check_main_layer(self):
        # Checks that the main layer is one of the layers
        if self.main_layer:  # If an input value for the "main layer" field was provided, we make sure that it is also one of the layers
            if self.main_layer not in self.layers:
                raise NameError(f"The main layer provided for unit {self.name} is {self.main_layer} and it is not one of the unit's layers {self.layers}. Please fix this!")
        else:
            if len(self.layers) > 1:
                Warning(f"The main layer for unit {self.name} was not provided. The first layer in the list {self.layers[0]} was used as main layer")
            self.main_layer = self.layers[0]

    def parse_layers(self):
        # This method parses the unit's layers and assigns them to a set of "Layer" objects
        output = set()
        for layer_name in self.layers:
            output.add(Layer(name = layer_name))
        return output
    
    def check_time_dependent_values(self, info, attribute_name: str):
        output = {}
        if isinstance(info[attribute_name], float|int):  # One single value is acceptable only if the process only has one layer
            if len(self.layers) > 1:
                raise ValueError(f'Only one value was provided for the input of process {self.name}, \
                                 while based on the unit layers {len(self.layers)} were required')
            else:
                output[self.layers[0]] = [info[attribute_name]]
        elif isinstance(info[attribute_name], list):  # If the Power field is a list of values, we interpret them as the fixed power values for each layer
            if len(self.layers) != len(info[attribute_name]):
                raise ValueError(f'Only {len(info[attribute_name])} values were provided for the input of process {self.name}, \
                                 while based on the unit layers {len(self.layers)} were required')
            else:
                for id, layer in enumerate(self.layers):
                    output[layer] = [info[attribute_name][id]]
        elif isinstance(info[attribute_name], str):  # We can also provide a string, it will be interpreted later. If it is 'file' we read the file based on a standard naming
            output = info[attribute_name]
        return output



class Process(Unit):
    """
    The process is a subclass of Unit. It models a unit for which the power is fixed
    """
    has_time_dependent_power: bool
    power: dict

    def __init__(self, name, info, problem):
        super().__init__(name, info, problem)  
        self.power = {}
        self.has_time_dependent_power = False
        # Assigining values to attributes
        self.check_default_values('Process')
        # If the process has only one layer, the input can be a single float
        self.read_power_input()
        if self.info['Type'] == 'Process (producer)':
            for layer, power in self.power.items():
                self.power[layer] = -power
                
    def read_power_input(self):
        if len(self.layers) == 1:  # One single value is acceptable only if the process only has one layer
            if isinstance(self.info['Power'], float|int):
                self.power[self.layers[0]] = self.info['Power']
            elif isinstance(self.info['Power'], list):
                if len(self.info['Power']) == 1:
                    self.power[self.layers[0]] = self.info['Power'][0]
                else:
                    raise ValueError(f'The unit {self.name} only has one layer, so the input must be either a single value or the "file" string')
            elif self.info['Power'] == 'file':
                self.power[self.layers[0]] = self.ts_data.loc[:, ('Power', self.layers[0])]
                self.has_time_dependent_power = True
            else:
                raise ValueError(f'The unit {self.name} only has one layer, so the input must be either a single value or the "file" string')
        elif isinstance(self.info['Power'], list):
            if len(self.info['Power']) == len(self.layers):
                for id, layer in enumerate(self.layers):
                    if isinstance(self.info['Power'][id], float|int):
                        self.power[layer] = self.info['Power'][id]
                    elif self.info['Power'][id] == 'file':
                        self.power[layer] = self.ts_data.loc[:, ('Power', layer)]
                        self.has_time_dependent_power = True
                    else:
                        raise ValueError(f'The power input for unit {self.name} should be a list of either single values or the string "file"')
        else:
            raise ValueError(f'The unit {self.name} has more than one layer, so the power input must be a list')
                

class Utility(Unit):
    """
    Differently from Processes, utilities are not necessarily installed. They can be,
    or not be, installed
    """
    specific_capex: float | int | list
    lifetime: int | list
    specific_annualized_capex: float
    specific_opex: float
    max_installed_power: dict
    time_dependent_capacity_factor: pd.Series | None
    has_time_dependent_max_power: bool
    
    def __init__(self, name, info, problem):
        super().__init__(name, info, problem)
        self.has_time_dependent_max_power = False
        self.check_default_values('Utility')
        self.specific_capex = self.info['Specific CAPEX']
        self.specific_opex = self.info['Specific OPEX']
        self.lifetime = self.info['Lifetime']
        self.max_power = {l: 0 for l in self.layers}
        self.time_dependent_capacity_factor = None
        self.calculate_annualized_capex(self.problem.interest_rate)
        self.read_max_installed_power()
        self.read_time_dependent_capacity_factor()

    def calculate_annualized_capex(self, interest_rate):
        # Calculates the annualized capital cost (specific) for each unit
        if isinstance(self.specific_capex, list):
            # If the data about the specific capex is a list, the calculation is done differently
            self.specific_annualized_capex = sum([self.specific_capex[i] / Utility.calculate_annualization_factor(self.lifetime[i], interest_rate) for i in range(len(self.lifetime))])
        else:
            self.specific_annualized_capex = self.specific_capex / Utility.calculate_annualization_factor(self.lifetime, interest_rate)
    
    def read_max_installed_power(self):
        if self.info['Type'] not in {'StorageUnit', 'ChargingUnit', 'DischargingUnit'}:
            if isinstance(self.info['Max installed power'], float) | isinstance(self.info['Max installed power'], int):
                if len(self.layers) == 1:
                    self.max_power[layer] = self.info['Max installed power']
                else:
                    raise ValueError(f'The maximum installed power for unit {self.name} should be a list of {len(self.layers)} elements. A single value was provided')
            else:
                for id, layer in enumerate(self.layers):
                    self.max_power[layer] = self.info['Max installed power'][id]

    def read_time_dependent_capacity_factor(self):
        if self.ts_data:
            if "Capacity factor" in self.ts_data.columns.levels[0]:
                self.time_dependent_capacity_factor = self.ts_data.loc[:, ('Capacity factor', '')]



    @staticmethod
    def calculate_annualization_factor(lifetime, interest_rate):
        # Calculates the annualization factor
        return ((interest_rate + 1)**lifetime - 1) / (interest_rate * (1 + interest_rate)**lifetime)

class StandardUtility(Utility):
    # This class does not add anything to a Utility, it is only used for classification purposes
    
    def __init__(self, name, info, interest_rate):
        super().__init__(name, info, interest_rate)
        # We never really define standard utilities as such. 
        info['Type'] = 'StandardUtility' if info['Type'] == 'Utility' else info['Type']


class StorageUnit(Utility):
    max_energy: float | int
    c_rate: float
    e_rate: float
    
    def __init__(self, name, info, problem):
        super().__init__(name, info, problem)
        self.check_default_values('StorageUnit')     
        # Reading class-speficif values
        self.stored_energy_layer = info['Stored energy layer'] if info['Stored energy layer'] else f'Stored{self.layers[0]}'
        self.layers.append(self.stored_energy_layer)
        self.max_energy = self.info['Max energy']
        self.c_rate = self.info['C-rate']
        self.e_rate = self.info['E-rate']

    @staticmethod
    def create_auxiliary_unit_info(storage_unit_name, storage_unit_info, aux_type: str) -> dict:
        # Creates the dictionary containing the unit info for the storage charging unit
        aux_unit_info = storage_unit_info[f'{aux_type} unit info']
        stored_energy_layer = storage_unit_info['Stored energy layer'] if 'Stored energy layer' in storage_unit_info.keys() else f'Stored{storage_unit_info['Layers']}'
        output = {}
        output['Name'] = aux_unit_info['Name'] if 'Name' in aux_unit_info.keys() else f'{storage_unit_name}{aux_type.replace('ing','er')}'
        output['Layers'] = [stored_energy_layer] + [storage_unit_info['Layers']]
        if 'Energy requirement layer' in aux_unit_info.keys():
            output['Energy requirement layer'] = aux_unit_info['Energy requirement layer']
            output['Layers'].append(aux_unit_info['Energy requirement layer'])
        output['Main layer'] = aux_unit_info['Main layer'] if 'Main layer' in aux_unit_info.keys() else stored_energy_layer
        output['Type'] = f'{aux_type}Unit'
        output['Specific CAPEX'] = aux_unit_info['Specific CAPEX'] if 'Specific CAPEX' in aux_unit_info.keys() else None
        output['Lifetime'] = aux_unit_info['Lifetime'] if 'Lifetime' in aux_unit_info.keys() else None
        output['Efficiency'] = aux_unit_info['Efficiency'] if 'Efficiency' in aux_unit_info.keys() else None
        match aux_type:
            case 'Charging':
                output[f'Max charging power'] = storage_unit_info['Max energy'] * storage_unit_info['C-rate']
            case 'Discharging':
                output[f'Max discharging power'] = storage_unit_info['Max energy'] * storage_unit_info['E-rate']
        output['Storage unit'] = storage_unit_name
        return output


class ChargingUnit(Utility):
    efficiency: float 
    max_charging_power: float
    
    def __init__(self, name, info, problem):
        super().__init__(name, info, problem)
        # Defining class-specific attributes
        self.storage_unit = info['Storage unit']
        # Checking default values
        self.check_default_values('ChargingUnit')
        # Assigning values
        self.max_charging_power = self.info['Max charging power']
        self.efficiency = self.info['Efficiency']
        if info['Energy requirement layer']:
            self.layers.append(info['Energy requirement layer'])
            self.max_power = {
                self.layers[0]: self.max_charging_power,
                self.layers[1]: -self.max_charging_power,
                self.layers[2]: -self.max_charging_power * (1-self.efficiency)}
        else:
            self.max_power = {
                self.layers[0]: self.max_charging_power * self.efficiency,
                self.layers[1]: -self.max_charging_power}

class DischargingUnit(Utility):
    efficiency: float
    max_discharging_power: float
    
    def __init__(self, name, info, interest_rate):
        super().__init__(name, info, interest_rate)
        # Defining class-specific attributes
        self.storage_unit = info['Storage unit']
        # Checking default values
        self.check_default_values('DischargingUnit')
        # Assigning values
        self.max_discharging_power = self.info['Max discharging power']
        self.efficiency = self.info['Efficiency']
        if info['Energy requirement layer']:
            self.layers.append(info['Energy requirement layer'])
            self.max_power = {
                self.layers[0]: self.max_discharging_power,
                self.layers[1]: -self.max_discharging_power,
                self.layers[2]: -self.max_discharging_power * (1-self.efficiency)}
        else:
            self.max_power = {
                self.layers[0]: self.max_discharging_power * self.efficiency,
                self.layers[1]: -self.max_discharging_power}



class Market(Utility):
    energy_price: dict
    activation_frequency: dict
    energy_price_variation: dict | None
    has_time_dependent_energy_prices: bool
    
    def __init__(self, name, info, problem):
        super().__init__(name, info, problem)
        match info['Type']:
            case 'PurchaseMarket' | 'Market':
                pass
            case 'SellingMarket':
                for layer_name, max_power in self.max_power.items():
                    self.max_power[layer_name] = -max_power
        self.energy_price = {layer: 0.0 for layer in self.layers}
        self.energy_price_variation = {layer: None for layer in self.layers}
        self.activation_frequency = safe_to_list(info['Activation frequency'])
        self.has_time_dependent_energy_prices = False
        # We assume the following possible scenarios:
        # 1. Prices are not time-dependent: in this case, we read the value provided as the constant value
        # 2. Prices are time-dependent, and they are provided by the user
        # 3. Prices are time-dependent, the user provides average price and price variation
        if "Time dependent price" not in self.info.keys():
            for id, layer in enumerate(self.layers):
                self.energy_price[layer] = safe_to_list(self.info['Price'])[id]
        else:
            self.has_time_dependent_energy_prices = True
            if 'Price' not in self.info.keys():
                for id, layer in enumerate(self.layers):
                    self.energy_price[layer] = self.ts_data.loc[:, ('Market', layer)].mean()
                    self.energy_price_variation[layer] = (self.ts_data.loc[:, ('Market', layer)]/self.energy_price[layer])
            else:
                for id, layer in enumerate(self.layers):
                    self.energy_price[layer] = safe_to_list(self.info['Price'])[id]
                    self.energy_price_variation[layer] = (self.ts_data.loc[:, ('Market', layer)])

    def check_data_consistency(self):
        assert len(self.layers) == len(self.activation_frequency)
        assert len(self.layers) == len(self.energy_price)
        # Da finire
