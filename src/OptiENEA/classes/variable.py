import os, yaml

with open(f'{os.path.dirname(os.path.realpath(__file__))}\\..\\lib\\default_entities.yml') as stream:
    DEFAULT_DATA = yaml.safe_load(stream)['VARIABLES']

class Variable():
    name: str
    indexed_over: list | None

    def __init__(self, name, indexed_over):
        self.name = name
        self.indexed_over = indexed_over

    @staticmethod
    def load_variables_indexing_data(variables):
        output = {}
        for var_name in variables:
            output[var_name] = Variable(var_name, DEFAULT_DATA[var_name])
        return output