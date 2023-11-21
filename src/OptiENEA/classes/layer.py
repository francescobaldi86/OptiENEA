
class Layer:
    def __init__(self, name):
        self.name: str = name
        self.unit: str = ''
    
    def parse_layer_info(self, info):
        # Loads layer info from a data structure
        for key, value in info.items():
            setattr(self, key, value)