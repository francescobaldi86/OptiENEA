from OptiENEA.classes.unit import *
import os

TEST_INFO_UNIT = {'Type': 'no type', 'Layers': ['test_layer_1', 'test_layer_2'], 'Main layer': 'test_layer_1'}
TEST_INFO_PROCESS = {'Type': 'Process', 'Layers': ['Electricity', 'Heat'], 'Main layer': 'Electricity', 'Power': 10}
TEST_INFO_UTILITY = {}
TEST_INFO_STANDARD_UTILTY = {}
TEST_INFO_STORAGE_UNIT = {}
TEST_INFO_MARKET = {}

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



def test_init_utility():
    # Tests the creation of a utility
    assert True

def test_init_standard_utility():
    # Tests the creation of a standard utility
    assert True

def test_init_storage_unit():
    # Tests the creation of a storage unit
    assert True

def test_init_market():
    # Tests the creation of a market
    assert True