from collections import defaultdict
import os, yaml

with open(f'{os.path.dirname(os.path.realpath(__file__))}\\..\\lib\\default_entities.yml') as stream:
    DEFAULT_ENTITIES = yaml.safe_load(stream)

class Set:
    def __init__(self, name: str, number_of_indeces: int = 0):
        self.name = name
        if number_of_indeces == 0:
            self.content = set()
        elif number_of_indeces == 1:
            self.content = defaultdict(set)
        else:
            raise(ValueError, f'The value for "number of indeces" of a set should be an integer between 0 and 1. {number_of_indeces} was provided for set {self.name}')
            

    def append(self, value, subset: str | None = None):
        if not subset:
            self.content.add(value)
        else:
            self.content[subset].add(value)

    def write(self, output_string):
        if isinstance(self.content, set):
            output_string += f'set {self.name} := {self.content};\n'
        elif isinstance(self.content, list):
            for slice in self.content:
                slice.name = f'{self.name}["{slice.name}"]'
                slice.write()
    
    @staticmethod
    def create_empty_sets(problem_sets):
        """
        Intializes the full list of problem parameters
        """
        for level, sets in DEFAULT_ENTITIES['SETS'].items():
            for set in sets:
                problem_sets[set] = Set(set, level)