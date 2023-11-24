from OptiENEA.classes.problem import Problem
import os
CWD = os.getcwd()

def test_create_empty_problem():
    # Tests the creation of an empty problem
    problem = Problem(name = 'test_problem', 
                      check_input_data=False, 
                      create_problem_folders=False)
    assert problem.name == 'test_problem'

def test_create_problem_folders():
    # Once the problem has been created, it tests the creation of the related folders
    problem = Problem(name = 'test_problem', 
                      problem_folder = f'{CWD}\\OptiENEA\\test\\DATA\\test_problem',
                      check_input_data=False, 
                      create_problem_folders=True)
    assert os.path.isdir(f'{CWD}\\OptiENEA\\test\\DATA\\test_problem')
    os.rmdir(f'{CWD}\\OptiENEA\\test\\DATA\\test_problem\\Results')
    os.rmdir(f'{CWD}\\OptiENEA\\test\\DATA\\test_problem\\Latest AMPL files')