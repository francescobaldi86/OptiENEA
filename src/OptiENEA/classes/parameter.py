import OptiENEA.helpers.helpers as helpers
from collections import defaultdict
import os, yaml

with open(f'{os.path.dirname(os.path.realpath(__file__))}\\..\\lib\\default_entities.yml') as stream:
    DEFAULT_ENTITIES = yaml.safe_load(stream)

class Parameter:
    # Class containing the problem parameters
    def __init__(self, name, number_of_indeces):
        self.name = name
        if number_of_indeces == 0:
            self.content = 0.0
        elif number_of_indeces == 1:
            self.content = {}
        elif number_of_indeces == 2:
            self.content = defaultdict(dict)
        elif number_of_indeces == 3:
            self.content = defaultdict(lambda: defaultdict(dict))
        elif number_of_indeces == 4:
            self.content = defaultdict(lambda: defaultdict(dict))
        else:
            raise(ValueError, f'The value for "number of indeces" should be an integer between 0 and 4. {number_of_indeces} was provided for parameter {self.name}')
    
    @staticmethod
    def create_empty_parameters():
        """
        Intializes the full list of problem parameters
        """
        problem_parameters = {}
        for level, parameters in DEFAULT_ENTITIES['PARAMETERS'].items():
            for param in parameters:
                problem_parameters[param] = Parameter(param, level)
        return problem_parameters
