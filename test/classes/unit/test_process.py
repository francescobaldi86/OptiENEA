from OptiENEA.classes.unit import Process
from OptiENEA.classes.problem import Problem
import os
from pandas import read_csv
from pytest import fixture

TEST_INFO_PROCESS = {'Type': 'Process', 'Layers': ['Electricity', 'Heat'], 'Main layer': 'Electricity', 'Power': [10, 6]}

__HERE__ = os.path.dirname(os.path.realpath(__file__))

def test_init_process_SLSV():
    # Tests the creation of a process
    # 1 - Single layer, value provided as single value
    TEST_INFO_PROCESS['Layers'] = 'Electricity'
    TEST_INFO_PROCESS['Power'] = 10
    process = Process('TestProcess', TEST_INFO_PROCESS, Problem(''))
    assert process.name == 'TestProcess'
    assert process.power['Electricity'] == 10
    assert process.power[process.main_layer] == 10
def test_init_process_SLLV():
    # Tests the creation of a process
    # 2 - Single layer, values provided as a list
    TEST_INFO_PROCESS['Layers'] = ['Electricity']
    TEST_INFO_PROCESS['Power'] = [10]
    process = Process('TestProcess', TEST_INFO_PROCESS, Problem(''))
    assert process.power['Electricity'] == 10
def test_init_process_SLTS(problem_with_ts_data):
    # Tests the creation of a process
    # 3 - Single layer, values provided as a time series
    TEST_INFO_PROCESS['Layers'] = 'Electricity'
    TEST_INFO_PROCESS['Power'] = "file"
    process = Process('TestProcess', TEST_INFO_PROCESS, problem_with_ts_data)
    assert process.power['Electricity'].loc[0] == 90.7
def test_init_process_MLSV():
    # Tests the creation of a process
    # 4 - Double layer, two contsant values
    TEST_INFO_PROCESS['Layers'] = ['Electricity', 'Heat']
    TEST_INFO_PROCESS['Power'] = [10, 7]
    process = Process('TestProcess', TEST_INFO_PROCESS, Problem(''))
    assert process.power['Electricity'] == 10
    assert process.power['Heat'] == 7
def test_init_process_MLTS1(problem_with_ts_data):
    # Tests the creation of a process
    # 5 - Double layer, one constant one time series
    TEST_INFO_PROCESS['Layers'] = ['Electricity', 'Heat']
    TEST_INFO_PROCESS['Power'] = [10, 'file']
    process = Process('TestProcess', TEST_INFO_PROCESS, problem_with_ts_data)
    assert process.power['Electricity'] == 10
    assert process.power['Heat'].loc[0] == 10.4
def test_init_process_MLTS(problem_with_ts_data):
    # Tests the creation of a process
    # 6 - Double layer, both as columns in the ts_data file
    TEST_INFO_PROCESS['Power'] = ['file', 'file']
    process = Process('TestProcess', TEST_INFO_PROCESS, problem_with_ts_data)
    assert process.power['Electricity'].loc[0] == 90.7
    assert process.power['Heat'].loc[0] == 10.4

@fixture
def problem_with_ts_data():
    problem = Problem('')
    problem.raw_timeseries_data = read_csv(os.path.join(__HERE__,"..","..","DATA","test_unit","data","power_test_process.csv"), sep=";", index_col=0, header=[0,1,2])
    return problem