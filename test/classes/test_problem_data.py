from OptiENEA.classes.problem_data import ProblemData
import os

__HERE__ = os.path.dirname(os.path.realpath(__file__))

def test_empty_problem_data_creation():
    # Simply tests that creating an empty class works.
    problem_data = ProblemData()
    assert problem_data.general_data == None
    assert problem_data.unit_data == None

def test_read_data():
    # Tries reading the data from some example files
    test_problem_folder = f'{__HERE__}\\..\\DATA\\test_problem_data'
    problem_data = ProblemData()
    problem_data.read_unit_data(test_problem_folder)
    assert isinstance(problem_data.general_data, dict)
    assert isinstance(problem_data.unit_data, dict)
    assert problem_data.general_data['main']['problem_type'] == 'LP'
    assert problem_data.general_data['main']['objective'] == 'OPEX'
    assert isinstance(problem_data.general_data['main']['general_parameters'], dict)
    assert problem_data.unit_data['WindFarm']['Type'] == 'Process'
    assert problem_data.unit_data['WindFarm']['Power'] == 'file'
    assert problem_data.unit_data['Market']['Type'] == 'Market'
    assert problem_data.unit_data['Market']['MaxPower'] == [-10000]
                      