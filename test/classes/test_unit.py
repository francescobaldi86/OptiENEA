from OptiENEA.classes.unit import *
import os

TEST_INFO_UNIT = {'Type': 'no type', 'Layers': ['test_layer_1', 'test_layer_2'], 'Main layer': 'test_layer_1'}
TEST_INFO_PROCESS = {'Type': 'Process', 'Layers': ['Electricity', 'Heat'], 'Main layer': 'Electricity', 'Power': [10, 6]}
TEST_INFO_UTILITY = {'Type': 'Utility', 'Specific CAPEX': 140, 'Lifetime': 20, 'Layers': ['Electricity', 'Heat'], 
                     'Main layer': 'Electricity', 'Max power': [1400, 900]}
TEST_INFO_BATTERY = {'Type': 'StorageUnit', 'Specific CAPEX': 140, 'Lifetime': 25, 'Layers': ['Electricity'], 'Main layer': 'Electricity',
                      'C-rate': 1.0, 'E-rate': 1.5, 'Capacity': 8000, 
                      'Charging unit info': {'Efficiency': 0.94}, 
                      'Discharging unit info': {'Efficiency': 0.96}}
TEST_INFO_LHS = {'Type': 'StorageUnit', 'Specific CAPEX': 40, 'Lifetime': 25, 'Layers': ['Hydrogen'], 'Main layer': 'Hydrogen',
                      'Max energy': 8000, 'Stored energy layer': 'LiquidHydrogen', 
                      'Charging unit info': {'Name': 'HydrogenLiquefactionUnit', 'Efficiency': 0.84, 'Main layer': 'Electricity', 'Energy requirement layer': 'Electricity'}, 
                      'Discharging unit info': {'Name': 'HydrogenRegasificationUnit'}}
TEST_INFO_MARKET = {}
INTEREST_RATE = 0.07

__HERE__ = os.path.dirname(os.path.realpath(__file__))

def test_init_unit():
    # Tests the creation of a generic unit
    unit = Unit('test_unit', TEST_INFO_UNIT)
    assert unit.layers == ['test_layer_1', 'test_layer_2']
    assert unit.name == 'test_unit'
    assert unit.main_layer == 'test_layer_1'


def test_init_process_power_dict():
    # Tests the creation of a process
    # First with power specified as a single value
    process = Process('test_process', TEST_INFO_PROCESS)
    assert process.name == 'test_process'
    assert process.power[process.main_layer] == [10]
    process.check_power_input()
    assert process.power[process.main_layer] == [10]

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
    assert utility.lifetime == 25
    assert utility.specific_capex == 0.01

def test_init_utility_base():
    # Tests the creation of a utility with no additional information
    utility = Utility('test_utility', TEST_INFO_UTILITY)
    assert utility.lifetime == 20
    assert utility.specific_capex == 140

def test_init_standard_utility():
    # The standard utility has nothing different from a utility, only used for classification
    # The test basically checks that a StandardUtility is also a Utility, but that a Utility is not also a StandardUtility
    test_utility = Utility('test_utility', TEST_INFO_UTILITY)
    test_standard_utility = StandardUtility('test_utility', TEST_INFO_UTILITY)
    assert isinstance(test_utility, Utility)
    assert isinstance(test_standard_utility, Utility)
    assert not isinstance(test_utility, StandardUtility)
    assert isinstance(test_standard_utility, StandardUtility)
    assert test_standard_utility.max_power == {'Electricity': [1400], 'Heat': [900]}

def test_calculate_annualized_capex():
    # Tests the function that calculates the annualized capex
    utility = StandardUtility('test_utility', TEST_INFO_UTILITY)
    assert round(StandardUtility.calculate_annualization_factor(utility.lifetime, INTEREST_RATE),1) == 10.6
    # Tests the calculation of the annualized capex
    utility.calculate_annualized_capex(INTEREST_RATE)
    assert round(utility.specific_annualized_capex, 1) == 13.2

def test_init_storage_unit_base():
    # Tests the creation of a storage unit. It's a battery
    test_storage_unit = StorageUnit('Battery', TEST_INFO_BATTERY)
    assert isinstance(test_storage_unit, StorageUnit)
    assert test_storage_unit.c_rate == 1.0
    assert test_storage_unit.e_rate == 1.5
    assert test_storage_unit.charging_unit_info['Efficiency'] == 0.94
    assert test_storage_unit.discharging_unit_info['Efficiency'] == 0.96
    assert test_storage_unit.stored_energy_layer == 'StoredElectricity'
    assert test_storage_unit.max_energy == 8000

def test_init_storage_unit_advanced():
    # Tests the creation of a more advanced storage unit, based on hydrogen storage
    test_storage_unit = StorageUnit('LHS', TEST_INFO_LHS)
    assert isinstance(test_storage_unit, StorageUnit)
    assert test_storage_unit.c_rate == 100.0
    assert test_storage_unit.e_rate == 100.0
    assert test_storage_unit.charging_unit_info['Efficiency'] == 0.84
    assert test_storage_unit.stored_energy_layer == 'LiquidHydrogen'

def test_create_info_charging_unit():
    # Tests the creation of the charging unit of the hydrogen storage
    test_storage_unit = StorageUnit('LHS', TEST_INFO_LHS)
    info = test_storage_unit.create_charging_unit_info()
    assert info['Efficiency'] == 0.84
    assert info['Main layer'] == 'Electricity'
    assert info['Layers'] == ['LiquidHydrogen', 'Hydrogen', 'Electricity']


def test_create_info_discharging_unit():
    # Tests the creation of the discharging unit of the hydrogen storage
    test_storage_unit = StorageUnit('LHS', TEST_INFO_LHS)
    info = test_storage_unit.create_discharging_unit_info()
    assert info['Efficiency'] is None
    assert info['Main layer'] is 'LiquidHydrogen'
    assert info['Layers'] == ['LiquidHydrogen', 'Hydrogen']
    assert True

def test_create_auxiliary_units():
    # Tests the creation of both auxiliary units
    test_storage_unit = StorageUnit('LHS', TEST_INFO_LHS)
    [test_charging_unit, test_discharging_unit] = test_storage_unit.create_auxiliary_units()
    temp_power = TEST_INFO_LHS['Max energy']*100.0
    assert test_charging_unit.max_power == {'LiquidHydrogen': temp_power, 'Hydrogen': -temp_power, 'Electricity': -temp_power*TEST_INFO_LHS['Charging unit info']['Efficiency']}
    assert test_charging_unit.name == TEST_INFO_LHS['Charging unit info']['Name']
    assert test_charging_unit.main_layer == 'Electricity'
    assert test_discharging_unit.max_power == {'LiquidHydrogen': -temp_power, 'Hydrogen': temp_power}
    assert test_discharging_unit.name ==TEST_INFO_LHS['Discharging unit info']['Name']
    assert test_discharging_unit.main_layer == 'LiquidHydrogen'

def test_init_market():
    # Tests the creation of a market
    assert True