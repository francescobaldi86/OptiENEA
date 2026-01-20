from OptiENEA.classes.problem import Problem
from OptiENEA.classes.typical_periods import *
import os, shutil, math, pytest
import pandas as pd

__HERE__ = os.path.dirname(os.path.realpath(__file__))
__PARENT__ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def test_period_segmenter(data_raw):
    # The periods segmenter, in principle, takes a time series and segments it into periods of a given size
    # First, let's read test data
    series = data_raw[('Household', 'Power', 'Electricity')]
    test_segmenter = PeriodSegmenter(period = 'day')
    assert True
    segmented_data, index_periods = test_segmenter.segment(series)
    assert segmented_data.shape == (365, 24)
    assert len(index_periods) == 365

def test_period_segmenter_multivariable(data_raw):
    # This tests the application of a segmenter to a multi-dimensional dataset
    test_segmenter = PeriodSegmenter(period = 'day')
    test_multi_segmenter = MultiSeriesSegmenter(test_segmenter)
    segmented_data, period_index = test_multi_segmenter.segment(data_raw)
    assert len(segmented_data.keys()) == len(data_raw.columns)
    assert data_raw.columns[0] in segmented_data.keys()
    assert segmented_data[data_raw.columns[0]].shape == (365, 24)

def test_feature_builder(feature_config, segmented_data):
    # Tests the class that creates the features object
    fb = FeatureBuilder(feature_config)
    X = fb.fit_transform(segmented_data)
    assert X.shape == (365, (24+2) * 3)

def test_extreme_selector(segmented_data, extreme_days_configuration):
    # Test the feature that selects the extreme pèriods, to be included forcefully among the selected typical periods
    forced = extreme_days_configuration.select(segmented_data)
    assert forced[0] == np.unravel_index(segmented_data[('Household', 'Power', 'Electricity')].argmax(), segmented_data[('Household', 'Power', 'Electricity')].shape)[0]
    assert forced[1] == segmented_data[('PV', 'Capacity factor', 'Electricity')].sum(axis=1).argmin()

def test_full_function(data_raw, feature_config, typical_period_config):
    builder = TypicalPeriodBuilder(feature_config, typical_period_config)
    tp = builder.build(data_raw)
    print(tp.meta["energy_errors"])     # should be ~0 per var
    ampl_payload = tp.to_ampl_params()
    assert True

def test_evaluation_metrics(data_raw, feature_config, typical_period_config):
    builder = TypicalPeriodBuilder(feature_config, typical_period_config)
    tp = builder.build(data_raw)
    evaluator = TypicalPeriodEvaluator()
    evaluator.evaluate(tp, data_raw)
    assert True





@pytest.fixture
def data_raw():
    data_raw = pd.read_csv(
                        os.path.join(__PARENT__, 'DATA', 'test_problem', 'test_problem_3', 'timeseries_data_full.csv'), 
                        header = [0,1,2], 
                        index_col = 0, 
                        sep = ";")
    return data_raw

@pytest.fixture
def segmented_data(data_raw):
    test_segmenter = PeriodSegmenter(period = 'day')
    test_multi_segmenter = MultiSeriesSegmenter(test_segmenter)
    segmented_data, period_index = test_multi_segmenter.segment(data_raw)
    return segmented_data

@pytest.fixture
def extreme_days_configuration():
    return ExtremeSelector([
        extreme_peak(('Household', 'Power', 'Electricity'), take=1),
        extreme_min_sum(('PV', 'Capacity factor', 'Electricity'), take=1),
        extreme_peak(('Household', 'Power', 'DHW'), take=1)
    ])

@pytest.fixture
def feature_config():
    return FeatureConfig(
        include_shape=True,
        include_level_mean=True,
        include_level_max=True,
        var_weights={"demand_el": 2.0, "pv": 1.0, "wind": 1.0},
        standardize=True
    )

@pytest.fixture
def typical_period_config(extreme_days_configuration):
    return TypicalPeriodConfig(
        K=10,
        period="day",
        energy_correction="clusterwise",
        extreme_selector=extreme_days_configuration,
        extreme_weight_mode="deduct",
        random_state=1
    )