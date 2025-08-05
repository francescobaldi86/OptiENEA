import OptiENEA.helpers.helpers as helpers

class ProblemParameters:
    # Class containing the problem parameters

    def __init__(self):
        self.interpreter = 'ampl'
        self.solver = 'highs'
        # Addiing ampl parameters
        self.interest_rate = 0.06
        self.simulation_horizon = 8760
        self.ampl_parameters = {"OCCURRENCE": [1], "TIME_STEP_DURATION": [1]}
    
    def read_problem_paramters(self, general_data: dict):
        # Reads the problem's general data into the deidcated structure
        self.interpreter: str = general_data['Settings']['Interpreter']
        self.solver: str = general_data['Settings']['Solver']
        # Addiing ampl parameters
        self.interest_rate: float = general_data['Standard parameters']['Interest rate']
        self.simulation_horizon: int = general_data['Standard parameters']['NT']
        self.ampl_parameters["OCCURRENCE"]: list[int] = helpers.safe_to_list(general_data['Standard parameters']['Occurrence'])
        self.ampl_parameters["TIME_STEP_DURATION"]: helpers.safe_to_list(general_data['Standard parameters']['Time step duration'])
     