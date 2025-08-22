import OptiENEA.helpers.helpers as helpers
from collections import defaultdict
import os, yaml
from pandas import DataFrame

with open(f'{os.path.dirname(os.path.realpath(__file__))}\\..\\lib\\default_entities.yml') as stream:
    DEFAULT_ENTITIES = yaml.safe_load(stream)

class Parameter:
    # Class containing the problem parameters
    def __init__(self, name, indexing_sets):
        self.name = name
        self.list_content = []
        self.indexing_level = len(indexing_sets) if indexing_sets else 0
        if indexing_sets == None:
            self.content = 0.0
        else:
            self.content = DataFrame(columns = indexing_sets + [name])
    
    def __call__(self):
        return self.content
    
    @staticmethod
    def create_empty_parameters():
        """
        Intializes the full list of problem parameters
        """
        problem_parameters = {}
        for param_name, indexing_sets in DEFAULT_ENTITIES['PARAMETERS'].items():
            problem_parameters[param_name] = Parameter(param_name, indexing_sets)
        return problem_parameters
