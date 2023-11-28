from OptiENEA.classes.problem import Problem
import os

__HERE__ = os.path.dirname(os.path.realpath(__file__))

def test_create_empty_problem():
    # Tests the creation of an empty problem
    problem = Problem(name = 'test_problem', 
                      check_input_data=False, 
                      create_problem_folders=False)
    assert problem.name == 'test_problem'

def test_create_problem_folders():
    # Once the problem has been created, it tests the creation of the related folders
    problem = Problem(name = 'test_problem', 
                      problem_folder = f'{__HERE__}\\..\\PLAYGROUND\\test_problem',
                      check_input_data=False, 
                      create_problem_folders=True)
    assert os.path.isdir(f'{__HERE__}\\..\\PLAYGROUND\\test_problem')
    os.rmdir(f'{__HERE__}\\..\\PLAYGROUND\\test_problem\\Results')
    os.rmdir(f'{__HERE__}\\..\\PLAYGROUND\\test_problem\\Latest AMPL files')
    
def test_read_problem_data():
    # Tests the reading of problem data
    problem = Problem(name = 'test_problem', 
                      problem_folder = f'{__HERE__}\\..\\DATA\\test_problem_data',
                      check_input_data=False, 
                      create_problem_folders=False)
    problem.read_problem_data()
    assert isinstance(problem.problem_data.general_data, dict)
    assert isinstance(problem.problem_data.unit_data, dict)
    assert problem.problem_data.general_data['main']['problem_type'] == 'LP'
    assert problem.problem_data.general_data['main']['objective'] == 'OPEX'
    assert isinstance(problem.problem_data.general_data['main']['general_parameters'], dict)
    assert problem.problem_data.unit_data['WindFarm']['Type'] == 'Process'
    assert problem.problem_data.unit_data['WindFarm']['Power'] == 'file'
    assert problem.problem_data.unit_data['Market']['Type'] == 'Market'
    assert problem.problem_data.unit_data['Market']['MaxPower'] == [-10000]

def test_process_problem_data():
    # Tests the "process_problem_data" function
    assert True