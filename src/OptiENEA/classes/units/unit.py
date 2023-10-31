class Unit:
    """
    Units are the basic obejct in OptiENEA. Every unit has a number of attributes
    """
    def __init__(self, name):
        self.name = name
        self.layers = []
        self.mainLayer = None


