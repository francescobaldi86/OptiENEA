from OptiENEA.classes.problem import Problem
from OptiENEA.classes.parametric_runs import ParametricRuns
import os, shutil, math, pytest
import pandas as pd

__HERE__ = os.path.dirname(os.path.realpath(__file__))
__PARENT__ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def test_read_parametric_problem_data(empty_problem):
    parametric_runs = ParametricRuns('test', empty_problem)
    assert parametric_runs.name == 'test'
    assert parametric_runs.problem == empty_problem
    assert parametric_runs.problem_folder == empty_problem.problem_folder
    assert parametric_runs.filename_scenario_description == 'Scenarios.xlsx'
    # Checking data about scenarios
    assert parametric_runs.scenarios_description.loc[0, ('Problem', 'POWER_MAX', 'PV', 'Electricity')] == 100
    assert pd.isna(parametric_runs.scenarios_description.loc[1, ('Problem', 'POWER_MAX', 'PV', 'Electricity')])
    assert parametric_runs.scenarios_description.loc[2, ('Problem', 'OCCURRANCE', '-','-')] == 2
    assert pd.isna(parametric_runs.scenarios_description.loc[1, ('Problem', 'OCCURRANCE', '-','-')])
    assert parametric_runs.scenarios_description.loc[1, ('Problem', 'POWER_MIN', 'AnaerobicDigester','-')] == 1
    assert pd.isna(parametric_runs.scenarios_description.loc[0, ('Problem', 'POWER_MIN', 'AnaerobicDigester','-')])
    assert parametric_runs.scenarios_description.loc[2, ('units.yaml', 'HeatPump', 'Specific CAPEX','-')] == 500
    assert pd.isna(parametric_runs.scenarios_description.loc[1, ('units.yaml', 'HeatPump', 'Specific CAPEX','-')])
    # Checking data about KPIs
    assert parametric_runs.kpis.loc[0, 'Name'] == 'TOTEX'
    assert parametric_runs.kpis.loc[3, 'Indexing'] == 'PV'  
    
def test_write_parametric_data_results(empty_problem):
    parametric_runs = ParametricRuns('test', empty_problem)
    parametric_runs.load_scenario_file()
    parametric_runs.run()
    parametric_runs.generate_summary_output_file()
    test_output = pd.read_excel(
        os.path.join(parametric_runs.problem_folder, f'{parametric_runs.name}_parametric_results.xlsx'),
        skiprows=[2],
        header = [0,1],
        index_col = 0
    )
    assert test_output.loc[:, ('Output', 'size:PV')].sum() == 0
    assert (test_output.loc[:, ('Output', 'size:HeatPump')] > 0).sum() == 2
    assert math.isclose(test_output.loc[2, ('Output', 'TOTEX')], 60, abs_tol=1)
    assert math.isclose(test_output.loc[3, ('Output', 'CAPEX')], 19, abs_tol=1)

@pytest.fixture
def empty_problem():
    problem_folder = os.path.join(__PARENT__, 'PLAYGROUND', 'test_parametric_runs')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv', 'Scenarios.xlsx'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_parametric_runs', filename), 
                     os.path.join(input_data_folder, filename))
    problem = Problem(name = 'test_problem', 
                      problem_folder = problem_folder)
    yield problem
    # Then we clean up
    shutil.rmtree(problem_folder)