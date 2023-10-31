from unit import Unit


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