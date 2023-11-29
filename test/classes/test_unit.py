from OptiENEA.classes.unit import *
import os

TEST_INFO_UNIT = {'Type': 'no type', 'Layers': ['test_layer_1', 'test_layer_2'], 'Main layer': 'test_layer_1'}
TEST_INFO_PROCESS = {'Type': 'Process', 'Layers': ['Electricity', 'Heat'], 'Main layer': 'Electricity', 'Power': 10}
TEST_INFO_UTILITY = {'Type': 'Utility', 'Investment cost': 140, 'Lifetime': 25, 'Layers': ['Electricity', 'Heat'], 
                     'Main layer': 'Electricity', 'Max power': [1400, 900]}
TEST_INFO_STANDARD_UTILTY = {}
TEST_INFO_STORAGE_UNIT = {}
TEST_INFO_MARKET = {}
INTEREST_RATE = 0.07

__HERE__ = os.path.dirname(os.path.realpath(__file__))

def test_init_unit():
    # Tests the creation of a generic unit
    unit = Unit('test_unit', TEST_INFO_UNIT)
    assert unit.layers == ['test_layer_1', 'test_layer_2']
    assert unit.name == 'test_unit'
    assert unit.type == 'no type'
    assert unit.mainLayer == 'test_layer_1'


def test_init_process_power_dict():
    # Tests the creation of a process
    # First with power specified as a single value
    process = Process('test_process', TEST_INFO_PROCESS)
    assert process.name == 'test_process'
    assert process.power[process.mainLayer] == [10]
    process.check_power_input()
    assert process.power[process.mainLayer] == [10]

def test_init_process_power_file_address():
    # Then we try with a file indication
    TEST_INFO_PROCESS['Power'] = f'{__HERE__}\\..\\DATA\\test_unit\\data\\power_test_process.csv'
    process = Process('test_process', TEST_INFO_PROCESS)
    process.check_power_input()
    assert isinstance(process.power, pd.DataFrame)
    assert process.power.loc[5, 'Electricity'] == 60.1
    assert process.power.loc[15, 'Heat'] == 4.9

def test_init_process_power_file_default():
    # Next we try reading it providing the project folder
    TEST_INFO_PROCESS['Power'] = 'file'
    process = Process('test_process', TEST_INFO_PROCESS)
    process.check_power_input(problem_folder=f'{__HERE__}\\..\\DATA\\test_unit')
    assert isinstance(process.power, pd.DataFrame)
    assert process.power.loc[5, 'Electricity'] == 60.1
    assert process.power.loc[15, 'Heat'] == 4.9

def test_init_process_power_file_TD():
    TEST_INFO_PROCESS['Power'] = 'file'
    process = Process('test_process', TEST_INFO_PROCESS)
    # Finally, we try reading a case with typical days
    process.check_power_input(problem_folder=f'{__HERE__}\\..\\DATA\\test_unit', has_typical_days=True)
    assert isinstance(process.power, dict)
    assert isinstance(process.power['Electricity'], pd.DataFrame)
    assert process.power['Electricity'].loc[5, 'TD1'] == 60.1
    assert process.power['Electricity'].loc[12, 'TD2'] == 122.1
    assert process.power['Heat'].loc[6, 'TD1'] == 6.1
    assert process.power['Heat'].loc[18, 'TD2'] == 7.7


def test_init_utility_default():
    # Tests the creation of a utility with no additional information
    TEST_INFO_UTILITY = {'Type': 'Utility', 'Layers': ['Electricity', 'Heat'], 
                     'Main layer': 'Electricity', 'Max power': [1400, 900]}
    utility = Utility('test_utility', TEST_INFO_UTILITY)
    assert utility.lifetime == 20
    assert utility.specific_capex == 0.0
    assert utility.power_max == {'Electricity': 1400, 'Heat': 900}

def test_init_utility_base():
    # Tests the creation of a utility with no additional information
    utility = Utility('test_utility', TEST_INFO_UTILITY)
    assert utility.lifetime == 25
    assert utility.specific_capex == 140
    assert utility.power_max == {'Electricity': 1400, 'Heat': 900}

def test_calculate_annualized_capex():
    # Tests the function that calculates the annualized capex
    utility = Utility('test_utility', TEST_INFO_UTILITY)
    assert round(Utility.calculate_annualization_factor(utility.lifetime, INTEREST_RATE),1) == 11.7
    # Tests the calculation of the annualized capex
    utility.calculate_annualized_capex(INTEREST_RATE)
    assert round(utility.specific_annualized_capex, 1) == 12.0


    



def test_init_standard_utility():
    # Tests the creation of a standard utility
    assert True

def test_init_storage_unit():
    # Tests the creation of a storage unit
    assert True

def test_init_market():
    # Tests the creation of a market
    assert True