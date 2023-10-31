from unit import Unit


class Process(Unit):
    """
    The process is a subclass of Unit. It models a unit for which the power is fixed
    """
    def __init__(self, name):
        super().__init__(name)
        self.power = []