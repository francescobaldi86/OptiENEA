from collections import defaultdict
import os, yaml

with open(f'{os.path.dirname(os.path.realpath(__file__))}\\..\\lib\\default_entities.yml') as stream:
    DEFAULT_ENTITIES = yaml.safe_load(stream)

class Set:
    name: str
    indexing: list
    
    def __init__(self, name: str, indexing: list | None):
        self.name = name
        if indexing:
            self.content = defaultdict(set)
            self.indexing = indexing
        else:
            self.content = set()
            self.indexing = []
            

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
    def create_empty_sets():
        """
        Intializes the full list of problem parameters
        """
        problem_sets = {}
        for set_name, indexing in DEFAULT_ENTITIES['SETS'].items():
            problem_sets[set_name] = Set(set_name, indexing)
        return problem_sets