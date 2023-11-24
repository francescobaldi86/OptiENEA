from OptiENEA.classes.problem import Problem

class Project:
    def __init__(self, name: str, folder):
        # Creates class instance
        self.name = name
        self.scenarios: [Problem] | None = None
        self.folder: str 