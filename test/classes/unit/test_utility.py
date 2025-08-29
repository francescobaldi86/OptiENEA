from OptiENEA.classes.unit import *
from OptiENEA.classes.problem import Problem
import os
from pandas import read_csv
from pytest import fixture

__HERE__ = os.path.dirname(os.path.realpath(__file__))
TEST_INFO_UTILITY = {'Type': 'Utility', 'Specific CAPEX': 140, 'Lifetime': 20, 'Layers': ['Electricity', 'Heat'], 
                     'Main layer': 'Electricity', 'Max installed power': [1400, 900]}
INTEREST_RATE = 0.07



def test_init_utility(problem):
    # Tests the creation of a utility
    # 1 - Utility with default data
    TEST_INFO_UTILITY = {'Type': 'Utility', 'Layers': ['Electricity', 'Heat'], 
                     'Main layer': 'Electricity', 'Max installed power': [1400, 900]}
    utility = Utility('test_utility', TEST_INFO_UTILITY, problem)
    assert utility.lifetime == 25
    assert utility.specific_capex == 0.01

def test_init_utility_base(problem):
    # Tests the creation of a utility with basic information
    utility = Utility('test_utility', TEST_INFO_UTILITY, problem)
    assert utility.lifetime == 20
    assert utility.specific_capex == 140

def test_init_utility_SL(problem):
    TEST_INFO_UTILITY = {'Type': 'Utility', 'Layers': ['Heat'], 
                     'Main layer': 'Heat', 'Max installed power': 1400}
    utility = Utility('test_utility', TEST_INFO_UTILITY, problem)
    assert utility.max_installed_power['Heat'] == 1400
    TEST_INFO_UTILITY['Max installed power'] = [1400]
    utility = Utility('test_utility', TEST_INFO_UTILITY, problem)
    assert utility.max_installed_power['Heat'] == 1400
    TEST_INFO_UTILITY['Layers'] = 'Heat'
    utility = Utility('test_utility', TEST_INFO_UTILITY, problem)
    assert utility.max_installed_power['Heat'] == 1400

def test_calculate_annualized_capex(problem):
    # Tests the function that calculates the annualized capex
    utility = Utility('test_utility', TEST_INFO_UTILITY, problem)
    assert round(Utility.calculate_annualization_factor(utility.lifetime, INTEREST_RATE),1) == 10.6
    # Tests the calculation of the annualized capex
    utility.calculate_annualized_capex(INTEREST_RATE)
    assert round(utility.specific_annualized_capex, 1) == 13.2

def test_init_standard_utility(problem):
    # The standard utility has nothing different from a utility, only used for classification
    # The test basically checks that a StandardUtility is also a Utility, but that a Utility is not also a StandardUtility
    test_utility = Utility('test_utility', TEST_INFO_UTILITY, problem)
    test_standard_utility = StandardUtility('test_utility', TEST_INFO_UTILITY, problem)
    assert isinstance(test_utility, Utility)
    assert isinstance(test_standard_utility, Utility)
    assert not isinstance(test_utility, StandardUtility)
    assert isinstance(test_standard_utility, StandardUtility)
    assert test_standard_utility.max_installed_power == {'Electricity': 1400, 'Heat': 900}

def test_utility_with_time_dependent_capacity_factor(problem):
    # Testing reading time-dependent capacity factor from csv file
    test_utility = Utility('TestUtility', TEST_INFO_UTILITY, problem)
    assert test_utility.time_dependent_capacity_factor['Electricity'].loc[5] == 0.601
    assert test_utility.time_dependent_capacity_factor['Heat'].loc[5] == 0.601

@fixture
def problem():
    problem = Problem('')
    problem.interest_rate = INTEREST_RATE
    problem.raw_timeseries_data = read_csv(os.path.join(__HERE__,"..","..","DATA","test_unit","test_utility_tsdata.csv"), sep=";", index_col=0, header=[0,1,2])
    return problem