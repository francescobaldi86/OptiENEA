
from OptiENEA.classes.problem import Problem

def test_create_empty_problem():
    # Tests the creation of an empty problem
    problem = Problem(name = 'test problem', check_input_data=False, create_problem_folders=False)
    assert problem.name == 'test problem'



def test_create_problem_folders():
    # Once the problem has been created, it tests the creation of the related folders
    problem = Problem(name = 'test problem', check_input_data=False, create_problem_folders=True)