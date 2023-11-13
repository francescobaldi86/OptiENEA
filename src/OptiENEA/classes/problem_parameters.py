

class ProblemParameters:
    # Class containing the problem parameters

    def __init__(self, general_data):
        self.interest_rate: float = general_data['InterestRate'] | 0.06
        self.simulation_horizon: int = general_data['NT'] | 8760
        self.interpreter: str = general_data['Interpreter'] | 'ampl'
        self.solver: str = general_data['Solver'] | 'highs'
        self.occurrence: list[int] = general_data['Occurrance'] if isinstance(general_data['Occurrance'], list) else [general_data['Occurrance'] | [1]
        self.time_step_duration: general_data['Occurrance'] if isinstance(general_data['Occurrance'], list) else [general_data['Occurrance'] | [1]
    
     