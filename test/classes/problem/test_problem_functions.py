from OptiENEA.classes.problem import Problem
from OptiENEA.classes.set import Set
from OptiENEA.classes.parameter import Parameter
from OptiENEA.classes.amplpy import AmplProblem
from OptiENEA.classes.unit import *
import os, pytest, shutil, math

__HERE__ = os.path.dirname(os.path.realpath(__file__))
__PARENT__ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def test_problem_with_min_installed_power():
    problem_folder = os.path.join(__PARENT__, 'PLAYGROUND', f'test_problem_minimum_capacity')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_3', filename), 
                     os.path.join(input_data_folder, filename))
    # First run with the "standard" file, we make sure that the CHPEngine is not installed
    problem = Problem(name = f'test_problem_minimum_capacity', 
                      problem_folder = problem_folder)
    problem.run()
    assert math.isclose(problem.ampl_problem.get_variable('size')['CHPEngine'].value(),0,abs_tol = 0.1)
    shutil.rmtree(os.path.join(problem_folder, 'Temporary files'))
    shutil.rmtree(os.path.join(problem_folder, 'Results'))
    # Then, Modify the YAML file to add the "minimum installed power" input
    with open(os.path.join(input_data_folder,'units.yml'), "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["CHPEngine"]["Min installed power"] = 4
    with open(os.path.join(input_data_folder,'units.yml'), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False),  # keep key order
    # Second run: now we use the new yml file, with the minimum power of the CHPEngine set to 4
    problem = Problem(name = f'test_problem_minimum_capacity', 
                      problem_folder = problem_folder)
    problem.run()
    assert math.isclose(problem.ampl_problem.get_variable('size')['CHPEngine'].value(),4,abs_tol = 0.1)
    shutil.rmtree(problem_folder)

def test_problem_with_min_installed_power_if_installed():
    problem_folder = os.path.join(__PARENT__, 'PLAYGROUND', f'test_problem_minimum_size_if_installed')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_3', filename), 
                     os.path.join(input_data_folder, filename))
    # First run with the "standard" file, we make sure that the CHPEngine is not installed
    # Then, Modify the YAML file to add the "minimum installed power" input
    with open(os.path.join(input_data_folder,'units.yml'), "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["AnaerobicDigester"]["Specific CAPEX"] = 6200
    with open(os.path.join(input_data_folder,'units.yml'), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False),  # keep key order
    problem = Problem(name = f'test_problem_minimum_size_if_installed', 
                      problem_folder = problem_folder)
    problem.run()
    assert math.isclose(problem.ampl_problem.get_variable('size')['AnaerobicDigester'].value(),0.0286,abs_tol = 0.01)
    shutil.rmtree(os.path.join(problem_folder, 'Temporary files'))
    shutil.rmtree(os.path.join(problem_folder, 'Results'))
    # Then, Modify the YAML file to add the "minimum installed power" input
    with open(os.path.join(input_data_folder,'units.yml'), "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["AnaerobicDigester"]["Min size if installed"] = 0.1
    with open(os.path.join(input_data_folder,'units.yml'), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False),  # keep key order
    # Second run: now we use the new yml file, with the minimum power of the CHPEngine set to 4
    problem = Problem(name = f'test_problem_minimum_size_if_installed', 
                      problem_folder = problem_folder)
    problem.run()
    assert math.isclose(problem.ampl_problem.get_variable('size')['AnaerobicDigester'].value(),0.0,abs_tol = 0.01)
    shutil.rmtree(problem_folder)