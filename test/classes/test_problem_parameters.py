from OptiENEA.classes.problem_parameters import ProblemParameters
from OptiENEA.classes.problem_data import ProblemData
import os

__HERE__ = os.path.dirname(os.path.realpath(__file__))

def test_problem_parameters_empty_init():
    # Tests the initialization of a problem parameters instance
    problem_parameters = ProblemParameters()
    assert problem_parameters.interpreter == 'ampl'
    assert problem_parameters.solver == 'highs'
    assert problem_parameters.interest_rate == 0.06
    assert problem_parameters.simulation_horizon == 8760

def test_read_problem_parameters():
    # Tries reading the data from some example files
    test_problem_folder = f'{__HERE__}\\..\\DATA\\test_problem_data'
    problem_data = ProblemData()
    problem_data.read_problem_data(test_problem_folder)
    problem_parameters = ProblemParameters()
    problem_parameters.read_problem_paramters(problem_data.general_data)
    assert problem_parameters.interest_rate == 0.07
    assert problem_parameters.ampl_parameters['OCCURRENCE'] == [1]
    assert problem_parameters.ampl_parameters['TIME_STEP_DURATION'] == [1]