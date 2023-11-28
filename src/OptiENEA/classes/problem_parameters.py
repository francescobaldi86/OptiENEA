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
        self.interpreter: str = general_data['settings']['Interpreter']
        self.solver: str = general_data['settings']['Solver']
        # Addiing ampl parameters
        self.interest_rate: float = general_data['standard parameters']['Interest rate']
        self.simulation_horizon: int = general_data['standard parameters']['NT']
        self.ampl_parameters["OCCURRENCE"]: list[int] = general_data['standard parameters']['Occurrence'] if isinstance(general_data['standard parameters']['Occurrence'], list) else [general_data['standard parameters']['Occurrence']]
        self.ampl_parameters["TIME_STEP_DURATION"]: general_data['standard parameters']['Time step duration'] if isinstance(general_data['standard parameters']['Time step duration'], list) else [general_data['standard parameters']['Time step duration']]
            
     