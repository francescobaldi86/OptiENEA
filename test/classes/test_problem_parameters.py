from OptiENEA.classes.parameter import Parameter
from OptiENEA.classes.problem import Problem
import os, shutil, math

__HERE__ = os.path.dirname(os.path.realpath(__file__))
__PARENT__ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def test_problem_main_settings_default():
    # Tests the initialization of a problem parameters instance
    problem = Problem(name = 'Test')
    assert problem.interpreter == 'ampl'
    assert problem.solver == 'highs'
    assert problem.interest_rate == 0.06
    assert problem.simulation_horizon == 8760

def test_read_problem_main_settings_from_file(tmp_path):
    # Tries reading the data from some example files
    problem_folder = os.path.join(tmp_path, 'test_problem_parameter')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_3', filename), 
                     os.path.join(input_data_folder, filename))
    problem = Problem(name = 'test_problem', 
                      problem_folder = problem_folder)
    problem.read_problem_data()
    problem.read_problem_parameters()
    assert problem.interpreter == 'ampl'
    assert problem.solver == 'highs'
    assert problem.interest_rate == 0.07
    assert problem.simulation_horizon == 168