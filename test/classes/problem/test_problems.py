# from OptiENEA.classes.problem import Problem

from OptiENEA.classes.problem import Problem
import os, shutil, math

__HERE__ = os.path.dirname(os.path.realpath(__file__))
__PARENT__ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

def test_problem_1():
    problem_folder = os.path.join(__PARENT__, 'PLAYGROUND', 'test_problem_1')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', 'test_problem_1', filename), 
                     os.path.join(input_data_folder, filename))
    problem = Problem(name = 'test_problem_1', 
                      problem_folder = problem_folder)
    problem.run()
    assert problem.ampl_problem.solve_result == "solved"
    assert math.isclose(problem.ampl_problem.get_variable('OPEX').value(), -160780, abs_tol = 10)
    assert math.isclose(problem.ampl_problem.get_variable('CAPEX').value(), 98796, abs_tol = 10)
    assert math.isclose(problem.ampl_problem.get_variable('TOTEX').value(),-61983,abs_tol = 10)
    shutil.rmtree(problem_folder)
    assert True