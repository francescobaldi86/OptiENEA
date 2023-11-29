from OptiENEA.classes.layer import Layer
from OptiENEA.helpers.helpers import read_data_file
import pandas as pd


class Unit:
    """
    Units are the basic obejct in OptiENEA. Every unit has a number of attributes
    """
    def __init__(self, name, info):
        self.name: str = name
        self.type = info['Type']
        self.layers: list = info['Layers'] if isinstance(info['Layers'], list) else [info['Layers']]
        self.mainLayer: str = info['Main layer'] if 'Main layer' in info.keys() else None
        self.check_main_layer()
    
    @staticmethod
    def load_unit(name: str, info: dict):
        match info['type']:
            case 'Process':
                return Process(name, info)
            case 'Utility':
                match info['subtype']:
                    case 'Standard':
                        return Utility(name, info)
                    case 'StorageUnit':
                        return StorageUnit(name, info)
                    case 'Market':
                        return Market(name, info)

    def check_main_layer(self):
        # Checks that the main layer is one of the layers
        if self.mainLayer:  # If an input value for the "main layer" field was provided, we make sure that it is also one of the layers
            if self.mainLayer not in self.layers:
                raise NameError(f"The main layer provided for unit {self.name} is {self.mainLayer} and it is not one of the unit's layers {self.layers}. Please fix this!")
        else:
            if len(self.layers) > 1:
                Warning(f"The main layer for unit {self.name} was not provided. The first layer in the list {self.layers[0]} was used as main layer")
            self.mainLayer = self.layers[0]

    def parse_layers(self):
        # This method parses the unit's layers and assigns them to a set of "Layer" objects
        output = set()
        for layer_name in self.layers:
            output.add(Layer(layer_name))
        return output



class Process(Unit):
    """
    The process is a subclass of Unit. It models a unit for which the power is fixed
    """
    def __init__(self, name, info):
        super().__init__(name, info)
        self.power: dict | str = {}
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

    def check_power_input(self, problem_folder = None, has_typical_days = False):
        # Checks the input field for the process power. If it's a dictionary it leaves it as it is, if it's a string it tries to read the file
        if isinstance(self.power, str):
            if has_typical_days:  # If the problem has typical days, we read one file for each layer. Files should be named "unit_layer.csv"
                data = {}
                for layer in self.layers:
                    data[layer] = read_data_file(input = self.power, 
                                                entity_name = f'power_{self.name}_{layer}', 
                                                problem_folder = problem_folder)
            else:  # If the problem does not have typical days, we expect a pd.DataFrame with one column per layer, one row per time step
                data = read_data_file(input = self.power, 
                                    entity_name = f'power_{self.name}', 
                                    problem_folder = problem_folder)
            self.power = data
        elif isinstance(self.power, dict):  # If the value is a dictionary, we keep it as it is
            pass
        else:
            return TypeError(f'The input provided for entity {self.name} is {self.power} and \
                         it appears not valid. Please check it! It should be either \
                         a list of values, or a string')


class Utility(Unit):
    """
    Differently from Processes, utilities are not necessarily installed. They can be,
    or not be, installed
    """
    def __init__(self, name, info):
        super().__init__(name, info)
        self.specific_capex: float | int | list = info['Investment cost'] if 'Investment cost' in info.keys() else 0
        self.lifetime: int | list = info['Lifetime'] if 'Lifetime' in info.keys() else 20
        self.specific_annualized_capex: float | int = 0.0
        self.specific_opex: float | int = 0.0
        self.power_max: dict = {}
        # Reading power max
        if isinstance(info['Max power'], list): # If Max power is a list, we assume it has one value per layer, ordered as the layers
            if len(info['Max power']) == len(self.layers):
                for id, layer in enumerate(self.layers):
                    self.power_max[layer] = info['Max power'][id]
            else:  # Issue an error if the number of values in the list is different from the number of layers
                raise ValueError(f'The input for the max power of unit {self.name} should be a list of \
                                 {len(self.layers)} elements based on the layers provided. A list of \
                                 {len(info["Max power"])} was provided instead')
        else:  # If only one value is provided, we assume it's because there is only one layer
            if len(self.layers) == 1:
                self.power_max[self.layers[0]] = [info['Max power']]
            else:  # If one value is provided but there are two or more errors, we raise a ValueError
                raise ValueError(f'The input for the max power of unit {self.name} should be a list of \
                                 {len(self.layers)} elements based on the layers provided. A single value was \
                                 provided instead')
    
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
    def __init__(self, name, info):
        super().__init__(name, info)

class StorageUnit(Utility):
    def __init__(self, name, info):
        super().__init__(name, info)
        self.capacity = info['Capacity']
        self.charging_efficiency: float = info['ChargingEfficiency'] | 1.0
        self.discharging_efficiency: float = info['DischargingEfficiency'] | 1.0
        self.c_rate: float = info['Rates'][0] | 1.0
        self.e_rate: float = info['Rates'][1] | 1.0
        self.charging_energy_layer: str = info['Layers']
        self.main_layer: str | None = None
        self.charging_unit: str = info['ChargingUnitName'] | f'{name}Charger'
        self.discharging_unit: str | None = info['DischargingUnitName'] | f'{name}Disharger'
    
    def create_auxiliary_units(self) -> list:
        # Creates the auxiliary (charging and discharging) units
        charging_unit_info = self.create_charging_unit_info()
        discharging_unit_info = self.create_discharging_unit_info()
        return [Unit.load_unit(charging_unit_info['Name'], charging_unit_info), Unit.load_unit(discharging_unit_info['Name'], discharging_unit_info)]

    def create_charging_unit_info(self) -> dict:
        info = {}
        info['Name'] = self.charging_unit
        info['Layers'] = self.layers
        main_layer = self.main_layer | self.layers[0].replace('Stored', '')
        info['Layers'].append(main_layer)
        max_power = self.capacity * self.c_rate
        if self.charging_energy_layer:
            info['Layers'].append(self.charging_energy_layer)
            info['MaxPower'] = [max_power, -max_power, -max_power * (1 - self.charging_efficiency)]
        else:
            info['MaxPower'] = [max_power * self.charging_efficiency, -max_power]
        info['Type'] = 'Utility'
        info['Subtype'] = 'ChargingUtility'
        return info

    def create_discharging_unit_info(self) -> dict:
        info = {}
        info['Name'] = self.discharging_unit
        max_power = self.capacity * self.e_rate
        info['MaxPower'] = [-max_power, max_power]
        info['Layers'] = self.layers
        main_layer = self.main_layer | self.layers[0].replace('Stored', '')
        info['Layers'].append(main_layer)
        info['Type'] = 'Utility'
        info['Subtype'] = 'DischargingUtility'
        return info

class Market(Utility):
    def __init__(self, name, info):
        super().__init__(name, info)
        self.activation_delay = []
        self.energy_price = {}
        if isinstance(info['EnergyPrice'], list):
            if len(info['EnergyPrice']) == len(self.layers):
                for id, layer in self.layers:
                    self.energy_price[layer] = info['EnergyPrice'][id]
            else:
                raise ValueError(f'The input for the energy price of unit {self.name} should be a list of \
                                 {len(self.layers)} elements based on the layers provided. A list of \
                                 {len(info["EnergyPrice"])} was provided instead')
        elif isinstance(info['EnergyPrice'], float) or isinstance(info['EnergyPrice'], int):
            if len(self.layers) == 1:
                self.energy_price[self.layers[0]] = [info['MaxPower']]
            else:
                raise ValueError(f'The input for the energy price of unit {self.name} should be a list of \
                                 {len(self.layers)} elements based on the layers provided. A single value was \
                                 provided instead')
        elif isinstance(info['EnergyPrice'], str):
            self.energy_price = info['EnergyPrice']