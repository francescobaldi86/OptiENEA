from OptiENEA.classes.unit import *
from OptiENEA.classes.problem import Problem
import os
from pandas import read_csv
from pytest import fixture

__HERE__ = os.path.dirname(os.path.realpath(__file__))
TEST_INFO_BATTERY = {'Type': 'StorageUnit', 'Specific CAPEX': 140, 'Lifetime': 25, 'Layers': ['Electricity'], 'Main layer': 'Electricity',
                      'C-rate': 1.0, 'E-rate': 1.5, 'Max energy': 8000, 
                      'Charging unit info': {'Efficiency': 0.94}, 
                      'Discharging unit info': {'Efficiency': 0.96}}
TEST_INFO_LHS = {'Type': 'StorageUnit', 'Specific CAPEX': 40, 'Lifetime': 25, 'Layers': ['Hydrogen'], 'Main layer': 'Hydrogen',
                      'Max energy': 8000, 'Stored energy layer': 'LiquidHydrogen', 
                      'Charging unit info': {'Name': 'HydrogenLiquefactionUnit', 'Efficiency': 0.84, 'Main layer': 'Electricity', 'Energy requirement layer': 'Electricity'}, 
                      'Discharging unit info': {'Name': 'HydrogenRegasificationUnit'}}
INTEREST_RATE = 0.07

def test_init_storage_unit_base(problem):
    # Tests the creation of a storage unit. It's a battery
    test_storage_unit = StorageUnit('Battery', TEST_INFO_BATTERY, problem)
    assert isinstance(test_storage_unit, StorageUnit)
    assert test_storage_unit.c_rate == 1.0
    assert test_storage_unit.e_rate == 1.5
    assert test_storage_unit.stored_energy_layer == 'StoredElectricity'
    assert test_storage_unit.max_energy == 8000

def test_init_storage_unit_advanced(problem):
    # Tests the creation of a more advanced storage unit, based on hydrogen storage
    test_storage_unit = StorageUnit('LHS', TEST_INFO_LHS, problem)
    assert isinstance(test_storage_unit, StorageUnit)
    assert test_storage_unit.c_rate == 100.0
    assert test_storage_unit.e_rate == 100.0
    assert test_storage_unit.stored_energy_layer == 'LiquidHydrogen'

def test_create_info_charging_unit(problem):
    # Tests the creation of the charging unit of the hydrogen storage
    test_storage_unit = StorageUnit('LHS', TEST_INFO_LHS, problem)
    info = StorageUnit.create_auxiliary_unit_info('LHS', test_storage_unit.info, 'Charging')
    assert info['Name'] == 'HydrogenLiquefactionUnit'
    assert info['Efficiency'] == 0.84
    assert info['Main layer'] == 'Electricity'
    assert info['Layers'] == ['Hydrogen', 'LiquidHydrogen', 'Electricity']


def test_create_info_discharging_unit(problem):
    # Tests the creation of the charging unit of the hydrogen storage
    test_storage_unit = StorageUnit('LHS', TEST_INFO_LHS, problem)
    info = StorageUnit.create_auxiliary_unit_info('LHS', test_storage_unit.info, 'Discharging')
    assert info['Name'] == 'HydrogenRegasificationUnit'
    assert info['Efficiency'] == None
    assert info['Main layer'] == 'LiquidHydrogen'
    assert set(info['Layers']) == set(['LiquidHydrogen', 'Hydrogen'])

def test_create_auxiliary_units(problem):
    # Tests the creation of both auxiliary units
    test_storage_unit = StorageUnit('LHS', TEST_INFO_LHS, problem)
    test_charging_unit_info = test_storage_unit.create_auxiliary_unit_info('LHS', TEST_INFO_LHS, 'Charging')
    test_discharging_unit_info = test_storage_unit.create_auxiliary_unit_info('LHS', TEST_INFO_LHS, 'Discharging')
    test_charging_unit = ChargingUnit(test_charging_unit_info['Name'], test_charging_unit_info, problem)
    test_discharging_unit = DischargingUnit(test_discharging_unit_info['Name'], test_discharging_unit_info, problem)
    temp_power = TEST_INFO_LHS['Max energy']*100.0
    assert test_charging_unit.max_installed_power == {'Hydrogen': -temp_power, 'LiquidHydrogen': temp_power, 'Electricity': -temp_power*(1-TEST_INFO_LHS['Charging unit info']['Efficiency'])}
    assert test_charging_unit.name == TEST_INFO_LHS['Charging unit info']['Name']
    assert test_charging_unit.main_layer == 'Electricity'
    assert test_discharging_unit.max_installed_power == {'LiquidHydrogen': -temp_power, 'Hydrogen': temp_power}
    assert test_discharging_unit.name ==TEST_INFO_LHS['Discharging unit info']['Name']
    assert test_discharging_unit.main_layer == 'LiquidHydrogen'

@fixture
def problem():
    problem = Problem('')
    problem.interest_rate = INTEREST_RATE
    problem.raw_timeseries_data = read_csv(os.path.join(__HERE__,"..","..","DATA","test_unit","test_utility_tsdata.csv"), sep=";", index_col=0, header=[0,1,2])
    return problem