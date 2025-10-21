# from OptiENEA.classes.problem import Problem

from OptiENEA.classes.problem import Problem
from OptiENEA.helpers.helpers import safe_rmtree
import os, shutil, math

__HERE__ = os.path.dirname(os.path.realpath(__file__))
__PARENT__ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

def test_problem_1():
    """
    Test problem 1 represents a simple case with a wind farm and a PV field that can either sell electricity to the market, or 
    power a factor that requires both electricity and heat. The factory itself can install an electric boiler to use the 
    renewable electricity to produce heat
    """
    problem_number = 1
    problem_folder = os.path.join(__PARENT__, 'PLAYGROUND', f'test_problem_{problem_number}')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_{problem_number}', filename), 
                     os.path.join(input_data_folder, filename))
    problem = Problem(name = f'test_problem_{problem_number}', 
                      problem_folder = problem_folder)
    problem.run()
    assert problem.ampl_problem.solve_result == "solved"
    assert math.isclose(problem.ampl_problem.get_variable('OPEX').value(), -160780, abs_tol = 10)
    assert math.isclose(problem.ampl_problem.get_variable('CAPEX').value(), 98796, abs_tol = 10)
    assert math.isclose(problem.ampl_problem.get_variable('TOTEX').value(),-61983,abs_tol = 10)
    shutil.rmtree(problem_folder)
    assert True

def test_problem_2():
    """
    Test problem 2 represents the simple case of a household, where the residents can install PV and a battery to fulfill local demand. 
    In addition, the hot water demand can be fulfilled either with a boiler or with a heat pump. In both cases, it is possible to install
    a heat storage unit. 
    """
    problem_number = 2
    problem_folder = os.path.join(__PARENT__, 'PLAYGROUND', f'test_problem_{problem_number}')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_{problem_number}', filename), 
                     os.path.join(input_data_folder, filename))
    problem = Problem(name = f'test_problem_{problem_number}', 
                      problem_folder = problem_folder)
    problem.run()
    assert problem.ampl_problem.solve_result == "solved"
    assert math.isclose(problem.ampl_problem.get_variable('OPEX').value(), -755, abs_tol = 10)
    assert math.isclose(problem.ampl_problem.get_variable('CAPEX').value(), 1000, abs_tol = 10)
    assert math.isclose(problem.ampl_problem.get_variable('TOTEX').value(),244,abs_tol = 10)
    safe_rmtree(problem_folder)
    assert True

def test_problem_3():
    """
    Test problem 3 is the same as test problem 2, but with the addition of an anaerobic digester that can be used to generate biogas
    The biogas can be used either in a gas boiler, or in a CHP unit. The production profile of the digester is time-dependent
    """
    problem_number = 3
    problem_folder = os.path.join(__PARENT__, 'PLAYGROUND', f'test_problem_{problem_number}')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_{problem_number}', filename), 
                     os.path.join(input_data_folder, filename))
    problem = Problem(name = f'test_problem_{problem_number}', 
                      problem_folder = problem_folder)
    problem.run()
    assert problem.ampl_problem.solve_result == "solved"
    assert math.isclose(problem.ampl_problem.get_variable('OPEX').value(), -755, abs_tol = 10)
    assert math.isclose(problem.ampl_problem.get_variable('CAPEX').value(), 1000, abs_tol = 10)
    assert math.isclose(problem.ampl_problem.get_variable('TOTEX').value(),244,abs_tol = 10)
    safe_rmtree(problem_folder)
    assert True