from OptiENEA.classes.unit import *
from OptiENEA.classes.problem import Problem
import os, math
from pandas import read_csv
from pytest import fixture

__HERE__ = os.path.dirname(os.path.realpath(__file__))
INTEREST_RATE = 0.07

def test_init_market(market_info):
    # Tests the creation of a market
    problem = Problem('')
    test_market = Market('TestMarket', market_info, problem)
    problem.raw_timeseries_data = pd.DataFrame()
    assert test_market.energy_price['Electricity'] == 0.25
    assert test_market.energy_price['Natural gas'] == 0.09

def test_market_max_power_rel(problem, market_info):
    # Tests the creation of a market with time-dependent capacity factor (same function as Utility, but checking just in case)
    test_market = Market('TestMarket', market_info, problem)
    assert test_market.time_dependent_capacity_factor['Electricity'].loc[16] == 0.921

def test_market_variable_price_1(problem, market_info):
    # Case 1: one value time-dependent, the other not
    market_info['Price'] = ['file', 0.09]
    test_market = Market('TestMarket', market_info, problem)
    assert test_market.has_time_dependent_energy_prices['Electricity'] == True
    assert test_market.has_time_dependent_energy_prices['Natural gas'] == False
    assert math.isclose(test_market.energy_price_variation['Electricity'].loc[10], 0.2155, abs_tol = 0.01)
    assert math.isclose(test_market.energy_price['Electricity'], 45.0, abs_tol = 1)
    assert test_market.energy_price['Natural gas'] == 0.09
    assert test_market.energy_price_variation['Natural gas'] == None

def test_market_variable_price_2(problem, market_info):
    # Case 2: both time series are price dependent, with price provided
    # 2.1: The "Price" field has "file" explicitly provided
    market_info['Price'] = ['file', 'file']
    problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price', 'Natural gas')] = problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price', 'Electricity')] / 2
    test_market = Market('TestMarket', market_info, problem)
    assert test_market.has_time_dependent_energy_prices['Electricity'] == True
    assert test_market.has_time_dependent_energy_prices['Natural gas'] == True
    assert math.isclose(test_market.energy_price_variation['Natural gas'].loc[10], 0.2155, abs_tol = 0.01)
    assert math.isclose(test_market.energy_price['Natural gas'], 23.0, abs_tol = 1)
    # 2.2: There is no "Price" field
    market_info.pop('Price')
    test_market = Market('TestMarket', market_info, problem)
    assert test_market.has_time_dependent_energy_prices['Electricity'] == True
    assert test_market.has_time_dependent_energy_prices['Natural gas'] == True
    assert math.isclose(test_market.energy_price_variation['Natural gas'].loc[10], 0.2155, abs_tol = 0.01)
    assert math.isclose(test_market.energy_price['Natural gas'], 23.0, abs_tol = 1)
    # 2.3: The "Price" field is given, but the values do not match with time-dependent ones. 
    market_info['Price'] = [42.1, 12.1]
    test_market = Market('TestMarket', market_info, problem)
    assert test_market.has_time_dependent_energy_prices['Electricity'] == True
    assert test_market.has_time_dependent_energy_prices['Natural gas'] == True
    assert math.isclose(test_market.energy_price_variation['Natural gas'].loc[10], 0.2155, abs_tol = 0.01)
    assert math.isclose(test_market.energy_price['Natural gas'], 23.0, abs_tol = 1)

def test_market_variable_price_3(problem, market_info):
    # Case 3: both are time-dependent, but with relative values provided
    problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price variation', 'Electricity')] = problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price', 'Electricity')] / problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price', 'Electricity')].mean()
    problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price variation', 'Natural gas')] = problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price variation', 'Electricity')]
    problem.raw_timeseries_data = problem.raw_timeseries_data.drop([('TestMarket', 'Price', 'Electricity')], axis=1)
    test_market = Market('TestMarket', market_info, problem)
    assert test_market.has_time_dependent_energy_prices['Electricity'] == True
    assert test_market.has_time_dependent_energy_prices['Natural gas'] == True
    assert math.isclose(test_market.energy_price_variation['Natural gas'].loc[10], 0.215, abs_tol = 0.01)
    assert math.isclose(test_market.energy_price['Natural gas'], 0.09, abs_tol = 1)

def test_market_variable_price_4(problem, market_info):
    # Case 4: both are time-dependent, but with relative values provided (with wrong indication "Price")
    problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price', 'Electricity')] = problem.raw_timeseries_data.loc[:, ('TestMarket', 'Capacity factor', 'All layers')] / problem.raw_timeseries_data.loc[:, ('TestMarket', 'Capacity factor', 'All layers')].mean()
    problem.raw_timeseries_data.loc[:, ('TestMarket', 'Price', 'Natural gas')] = problem.raw_timeseries_data.loc[:, ('TestMarket', 'Capacity factor', 'All layers')] / problem.raw_timeseries_data.loc[:, ('TestMarket', 'Capacity factor', 'All layers')].mean()
    test_market = Market('TestMarket', market_info, problem)
    assert test_market.has_time_dependent_energy_prices['Electricity'] == True
    assert test_market.has_time_dependent_energy_prices['Natural gas'] == True
    assert math.isclose(test_market.energy_price_variation['Natural gas'].loc[10], 0.878, abs_tol = 0.01)
    assert math.isclose(test_market.energy_price['Natural gas'], 0.09, abs_tol = 1)


@fixture
def problem():
    problem = Problem('')
    problem.interest_rate = INTEREST_RATE
    problem.raw_timeseries_data = read_csv(os.path.join(__HERE__,"..","..","DATA","test_unit","test_market_tsdata.csv"), sep=";", index_col=0, header=[0,1,2])
    return problem

@fixture
def market_info():
    return {'Type': 'Market', 'Specific CAPEX': 0, 'Lifetime': 40, 'Layers': ['Electricity', 'Natural gas'], 
                     'Max installed power': [1400, 900], 'Price': [0.25, 0.09]}
