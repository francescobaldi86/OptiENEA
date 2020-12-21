


class Unit:
    """
    Units are the basic obejct in OptiENEA. Every unit has a number of attributes
    """
    def __init__(self, name):
        self.name = name
        self.layers = []
        self.mainLayer = None


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
    def __init__(self, name):
        super().__init__(name)
        self.specificInvestmentCost = 0
        self.lifetime = 0
        self.annualizedInvestmentCost = 0

class StandardUtility(Utility):
    def __init__(self, name):
        super().__init__(name)
        self.MaxPower = 0

class StorageUnit(Utility):
    def __init__(self, name):
        super().__init__(name)
        self.MaxEnergy = 0
        self.CRate = 0
        self.Erate = 0