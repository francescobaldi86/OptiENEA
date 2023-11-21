from helpers import read_input_from_file

class ProblemData:
    """
    The class ProblemData is used to read data from the input files
    """
    def __init__(self):
        self.unit_data: dict | None = None
        self.general_data: dict | None = None
    
    def read_unit_data(self, problem_folder):
        self.unit_data = read_input_from_file(f'{problem_folder}\\units.txt')
        self.general_data = read_input_from_file(f'{problem_folder}\\general.txt')
    
