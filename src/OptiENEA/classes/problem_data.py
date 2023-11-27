from OptiENEA.helpers.helpers import read_config_file

class ProblemData:
    """
    The class ProblemData is used to read data from the input files
    """
    def __init__(self):
        self.unit_data: dict
        self.general_data: dict
    
    def read_problem_data(self, problem_folder):
        self.unit_data = read_config_file(f'{problem_folder}\\units.txt', {})
        self.general_data = read_config_file(f'{problem_folder}\\general.txt', {})
    
