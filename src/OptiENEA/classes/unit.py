class Unit:
    """
    Units are the basic obejct in OptiENEA. Every unit has a number of attributes
    """
    def __init__(self, name):
        self.name = name
        self.layers = []
        self.mainLayer = None
    
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



class Process(Unit):
    """
    The process is a subclass of Unit. It models a unit for which the power is fixed
    """
    def __init__(self, name):
        super().__init__(name)
        self.power = []

class Utility(Unit):
    """
    Differently from Processes, utilities are not necessarily installed. They can be,
    or not be, installed
    """
    def __init__(self, name, info):
        super().__init__(name)
        self.specific_capex: float | list = info['InvestmentCost'] | 0.01
        self.lifetime: int | list = info['Lifetime'] | 20
        self.specific_annualized_capex = 0
        self.specific_opex = 0
        self.power_max = []
    
    def calculate_annualized_capex(self, interest_rate):
        # Calculates the annualized capital cost (specific) for each unit
        if isinstance(self.specific_capex, list):
            # If the data about the specific capex is a list, the calculation is done differently
            self.specific_annualized_capex = sum([Utility.calculate_annualization_factor(self.lifetime[i], interest_rate) * self.specific_capex[i] for i in range(len(self.lifetime))])
        else:
            self.specific_annualized_capex = Utility.calculate_annualization_factor(self.lifetime, interest_rate) * self.specific_capex
    
    @staticmethod
    def calculate_annualization_factor(lifetime, interest_rate):
        # Calculates the annualization factor
        return ((interest_rate + 1)**lifetime - 1) / (interest_rate * (1 + interest_rate)**lifetime)

class StorageUnit(Utility):
    def __init__(self, name, info):
        super().__init__(name)
        self.capacity = info['Capacity']
        self.charging_efficiency: float = info['ChargingEfficiency'] | 1.0
        self.discharging_efficiency: float = info['DischargingEfficiency'] | 1.0
        self.c_rate = 1
        self.e_rate = 1
        self.charging_energy_layer: str | None = None
        self.main_layer: str | None = None
        self.charging_unit: str | None = f'{name}Charger'
        self.discharging_unit: str | None = f'{name}Disharger'
    
    def create_auxiliary_units(self) -> list:
        # Creates the auxiliary (charging and discharging) units
        charging_unit_info = self.create_charging_unit_info()
        discharging_unit_info = self.create_discharging_unit_info()
        return [Unit.load_unit(charging_unit_info['Name'], charging_unit_info), Unit.load_unit(discharging_unit_info['Name'], discharging_unit_info)]

    def create_charging_unit_info(self) -> dict:
        info = {}
        info['Name'] = f'{self.name}Charger'
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
        info['Name'] = f'{self.name}Charger'
        max_power = self.capacity * self.e_rate
        info['MaxPower'] = [-max_power, max_power]
        info['Layers'] = self.layers
        main_layer = self.main_layer | self.layers[0].replace('Stored', '')
        info['Layers'].append(main_layer)
        info['Type'] = 'Utility'
        info['Subtype'] = 'DischargingUtility'
        return info

class Market(Utility):
    def __init__(self, name):
        super().__init__(name)
        self.activation_delay = []