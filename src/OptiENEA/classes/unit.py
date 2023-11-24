from OptiENEA.classes.layer import Layer
import pandas as pd

class Unit:
    """
    Units are the basic obejct in OptiENEA. Every unit has a number of attributes
    """
    def __init__(self, name, info):
        self.name: str = name
        self.type = info['type']
        self.layers: list = info['Layers'] if isinstance(info['Layers'], list) else [info['Layers']]
        self.mainLayer: str = info['MainLayer'] | self.layers[0]
    
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
        if isinstance(info.power, float):
            if len(self.layers) > 1:
                raise ValueError(f'Only one value was provided for the input of process {name}, \
                                 while based on the unit layers {len(self.layers)} were required')
            else:
                self.power[self.layers[0]] = [info.power]
        elif isinstance(info.power, list):
            if len(self.layers) != len(info.power):
                raise ValueError(f'Only {len(info.power)} values were provided for the input of process {name}, \
                                 while based on the unit layers {len(self.layers)} were required')
            else:
                for id, layer in enumerate(self.layers):
                    self.power[layer] = [info.power[id]]
        elif isinstance(info.power, str):
            self.power = info.power


class Utility(Unit):
    """
    Differently from Processes, utilities are not necessarily installed. They can be,
    or not be, installed
    """
    def __init__(self, name, info):
        super().__init__(name, info)
        self.specific_capex: float | list = info['InvestmentCost'] | 0.0
        self.lifetime: int | list = info['Lifetime'] | 20
        self.specific_annualized_capex: float = 0.0
        self.specific_opex: float = 0.0
        self.power_max = {}
        if isinstance(info['MaxPower'], list):
            if len(info['MaxPower']) == len(self.layers):
                for id, layer in self.layers:
                    self.power_max[layer] = info['MaxPower'][id]
            else:
                raise ValueError(f'The input for the max power of unit {self.name} should be a list of \
                                 {len(self.layers)} elements based on the layers provided. A list of \
                                 {len(info["MaxPower"])} was provided instead')
        else:
            if len(self.layers) == 1:
                self.power_max[self.layers[0]] = [info['MaxPower']]
            else:
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
            self.specific_annualized_capex = sum([Utility.calculate_annualization_factor(self.lifetime[i], interest_rate) * self.specific_capex[i] for i in range(len(self.lifetime))])
        else:
            self.specific_annualized_capex = Utility.calculate_annualization_factor(self.lifetime, interest_rate) * self.specific_capex


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