

class ObjectiveFunction():
    def __init__(self, name: str, info = {}):
        self.name = name
        match name:
            case "TOTEX":
                self.objective = "minimize TOTEX;\n"
                self.constraints = [
                    "s.t. TOTEX = CAPEX + OPEX;\n"
                ]
            case "CAPEX":
                self.objective = "minimize CAPEX;\n"
                self.constraints = []
            case "OPEX":
                self.objective = "minimize CAPEX;\n"
                self.constraints = []
            case _:
                self.objective = info['objective']
                self.constraints = info['constraints']


        


"""
TOTEX, minimize TOTEX;
s.t. calculate_totex: TOTEX = CAPEX + OPEX

minimize CAPEX;

minimize OPEX;
"""