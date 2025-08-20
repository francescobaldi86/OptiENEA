from OptiENEA.classes.layer import Layer
from OptiENEA.helpers.helpers import read_data_file, attribute_name_converter, safe_to_list
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
    info: {}
    
    def __init__(self, name, info):
        # Assigning attribute values based on input
        self.name = name
        self.layers = info['Layers'] if isinstance(info['Layers'], list) else [info['Layers']]
        self.main_layer = info['Main layer'] if 'Main layer' in info.keys() else None
        # Checks that the main layer is one of the layers
        self.info = info
        self.check_main_layer()
    
    @staticmethod
    def load_unit(name: str, info: dict):
        match info['Type']:
            case 'Process':
                return Process(name, info)
            case 'Utility':
                return StandardUtility(name, info)
            case 'StorageUnit':
                return StorageUnit(name, info)
            case 'Market':
                return Market(name, info)
            case 'ChargingUnit': 
                return ChargingUnit(name, info)
            case 'DischargingUnit':
                return DischargingUnit(name, info)
    
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
    time_dependent_power_profile: bool = True
    power: dict = {}

    def __init__(self, name, info):
        super().__init__(name, info)    
        # Assigining values to attributes
        self.check_default_values('Process')
        if isinstance(info['Power'], float|int):  # One single value is acceptable only if the process only has one layer
            if len(self.layers) > 1:
                raise ValueError(f'Only one value was provided for the input of process {name}, \
                                 while based on the unit layers {len(self.layers)} were required')
            else:
                self.power[self.layers[0]] = [info['Power']]
        elif isinstance(info['Power'], list):  # If the Power field is a list of values, we interpret them as the fixed power values for each layer
            if len(self.layers) != len(info['Power']):
                raise ValueError(f'Only {len(info['Power'])} values were provided for the input of process {name}, \
                                 while based on the unit layers {len(self.layers)} were required')
            else:
                for id, layer in enumerate(self.layers):
                    self.power[layer] = [info['Power'][id]]
        elif isinstance(info['Power'], str):  # We can also provide a string, it will be interpreted later. If it is 'file' we read the file based on a standard naming
            self.power = info['Power']

    def check_power_input(self, data: pd.DataFrame):
        # Checks the input field for the process power. If it's a dictionary it leaves it as it is, if it's a string it tries to read the file
        if isinstance(self.power, str):
            self.power = {}
            for layer in self.layers:
                self.power[layer] = data.loc[:, (self.name, layer)].to_dict()
        elif isinstance(self.power, dict):  # If the value is a dictionary, we keep it as it is
            pass
        else:
            return TypeError(f'The input provided for entity {self.name} is {self.power} and \
                         it appears not valid. Please check it! It should be either \
                         a list of values, or a string')
        for layer in self.layers:
            if any([isinstance(self.power[layer], float), isinstance(self.power[layer], int)]):
                pass  # If it's a float or an integer, don't do anything
            elif isinstance(self.power[layer], dict):
                self.time_dependent_power_profile = True
                


class Utility(Unit):
    """
    Differently from Processes, utilities are not necessarily installed. They can be,
    or not be, installed
    """
    specific_capex: float | int | list
    lifetime: int | list
    specific_annualized_capex: float
    specific_opex: float
    
    def __init__(self, name, info):
        super().__init__(name, info)
        # Assigning values to class-specific attributes
        self.check_default_values('Utility')
        self.specific_capex = self.info['Specific CAPEX']
        self.specific_opex = self.info['Specific OPEX']
        self.lifetime = self.info['Lifetime']

    @staticmethod
    def calculate_annualization_factor(lifetime, interest_rate):
        # Calculates the annualization factor
        return ((interest_rate + 1)**lifetime - 1) / (interest_rate * (1 + interest_rate)**lifetime)

    def calculate_annualized_capex(self, interest_rate):
        # Calculates the annualized capital cost (specific) for each unit
        if isinstance(self.specific_capex, list):
            # If the data about the specific capex is a list, the calculation is done differently
            self.specific_annualized_capex = sum([self.specific_capex[i] / Utility.calculate_annualization_factor(self.lifetime[i], interest_rate) for i in range(len(self.lifetime))])
        else:
            self.specific_annualized_capex = self.specific_capex / Utility.calculate_annualization_factor(self.lifetime, interest_rate)


class StandardUtility(Utility):
    # This class does not add anything to a Utility, it is only used for classification purposes
    max_power: float | int
    def __init__(self, name, info):
        super().__init__(name, info)
        # We never really define standard utilities as such. 
        info['Type'] = 'StandardUtility' if info['Type'] == 'Utility' else info['Type']        
        self.max_power = self.info['Max power']

class StorageUnit(Utility):
    max_energy: float | int
    c_rate: float
    e_rate: float
    
    def __init__(self, name, info):
        super().__init__(name, info)
        self.check_default_values('StorageUnit')     
        # Reading class-speficif values
        self.stored_energy_layer = info['Stored energy layer'] if info['Stored energy layer'] else f'Stored{self.layers[0]}'
        self.max_energy = self.info['Max energy']
        self.c_rate = self.info['C-rate']
        self.e_rate = self.info['E-rate']

    def create_auxiliary_units(self) -> list:
        # Creates the auxiliary (charging and discharging) units
        charging_unit_info = self.create_charging_unit_info()
        discharging_unit_info = self.create_discharging_unit_info()
        return [Unit.load_unit(charging_unit_info['Name'], charging_unit_info), Unit.load_unit(discharging_unit_info['Name'], discharging_unit_info)]

    def create_charging_unit_info(self) -> dict:
        # Creates the dictionary containing the unit info for the storage charging unit
        info = self.info['Charging unit info']
        output = {}
        output['Name'] = info['Name'] if 'Name' in info.keys() else f'{self.name}Charger'
        output['Layers'] = [self.stored_energy_layer] + self.layers
        if 'Energy requirement layer' in info.keys():
            output['Energy requirement layer'] = info['Energy requirement layer']
            output['Layers'].append(info['Energy requirement layer'])
        output['Main layer'] = info['Main layer'] if 'Main layer' in info.keys() else self.stored_energy_layer
        output['Type'] = 'ChargingUnit'
        output['Specific CAPEX'] = info['Specific CAPEX'] if 'Specific CAPEX' in info.keys() else None
        output['Lifetime'] = info['Lifetime'] if 'Lifetime' in info.keys() else None
        output['Efficiency'] = info['Efficiency'] if 'Efficiency' in info.keys() else None
        output['Max charging power'] = self.max_energy * self.c_rate
        output['Storage unit'] = self.name
        return output

    def create_discharging_unit_info(self) -> dict:
        # Creates the dictionary containing the unit info for the storage charging unit
        info = self.info['Discharging unit info']
        output = {}
        output['Name'] = info['Name'] if 'Name' in info.keys() else f'{self.name}Discharger'
        output['Layers'] = [self.stored_energy_layer] + self.layers
        if 'Energy requirement layer' in info.keys():
            output['Layers'].append(info['Energy requirement layer'])
        output['Main layer'] = info['Main layer'] if 'Main layer' in info.keys() else self.stored_energy_layer
        output['Type'] = 'DischargingUnit'
        output['Specific CAPEX'] = info['Specific CAPEX'] if 'Specific CAPEX' in info.keys() else None
        output['Lifetime'] = info['Lifetime'] if 'Lifetime' in info.keys() else None
        output['Efficiency'] = info['Efficiency'] if 'Efficiency' in info.keys() else None
        output['Max discharging power'] = self.max_energy * self.e_rate
        output['Storage unit'] = self.name
        return output


class ChargingUnit(Utility):
    efficiency: float 
    max_charging_power: float
    
    def __init__(self, name, info):
        super().__init__(name, info)
        # Defining class-specific attributes
        self.storage_unit = info['Storage unit']
        # Checking default values
        self.check_default_values('ChargingUnit')
        # Assigning values
        self.max_charging_power = self.info['Max charging power']
        self.efficiency = self.info['Efficiency']
        if 'Energy requirement layer' in info.keys():
            self.max_power = {key: value for key in self.layers for value in [self.max_charging_power, -self.max_charging_power, -self.max_charging_power * (1 - self.efficiency)]}
        else:
            self.max_power = {key: value for key in self.layers for value in [self.max_charging_power * self.efficiency, -self.max_charging_power]}

class DischargingUnit(Utility):
    efficiency: float
    max_discharging_power: float
    
    def __init__(self, name, info):
        super().__init__(name, info)
        # Defining class-specific attributes
        self.storage_unit = info['Storage unit']
        # Checking default values
        self.check_default_values('DischargingUnit')
        # Assigning values
        self.max_discharging_power = self.info['Max discharging power']
        self.efficiency = self.info['Efficiency']
        if 'Energy requirement layer' in info.keys():
            self.max_power = {key: value for key in self.layers for value in [-self.max_discharging_power, self.max_discharging_power, -self.max_discharging_power * (1 - self.efficiency)]}
        else:
            self.max_power = {key: value for key in self.layers for value in [-self.max_discharging_power, self.max_discharging_power * self.efficiency]}



class Market(Utility):
    energy_price: dict
    activation_frequency: dict
    
    def __init__(self, name, info):
        super().__init__(name, info)
        self.energy_price = {}
        self.activation_frequency = safe_to_list(info['Activation frequency'])
        
    def read_energy_prices(self, data: pd.DataFrame):
        # We assume the following possible scenarios:
        # 1. Prices are not time-dependent: in this case, we read the value provided as the constant value
        # 2. Prices are time-dependent, and they are provided by the user
        # 3. Prices are time-dependent, the user provides average price and price variation
        if "Time dependent price" not in self.info.keys():
            for id, layer in enumerate(self.layers):
                self.energy_price[layer] = safe_to_list(self.info['Price'])[id]
        else:
            self.energy_price_variation = {}
            if 'Price' not in self.info.keys():
                for id, layer in enumerate(self.layers):
                    self.energy_price[layer] = data.loc[:, ('Market', layer)].mean().to_dict()
                    self.energy_price_variation[layer] = (data.loc[:, ('Market', layer)]/self.energy_price[layer]).to_dict()
            else:
                for id, layer in enumerate(self.layers):
                    self.energy_price[layer] = safe_to_list(self.info['Price'])[id]
                    self.energy_price_variation[layer] = (data.loc[:, ('Market', layer)]).to_dict()


    def check_data_consistency(self):
        assert len(self.layers) == len(self.activation_frequency)
        assert len(self.layers) == len(self.energy_price)
        # Da finire