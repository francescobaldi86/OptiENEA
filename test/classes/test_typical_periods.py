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
    assert segmented_data.shape() == (365, 24)
    assert len(index_periods) == 365

@pytest.fixture
def test_period_segmenter_multivariable(data_raw):
    # This tests the application of a segmenter to a multi-dimensional dataset
    test_segmenter = PeriodSegmenter(period = 'day')
    test_multi_segmenter = MultiSeriesSegmenter(test_segmenter)
    segmented_data, period_index = test_multi_segmenter.segment(data_raw)
    assert len(segmented_data.keys()) == len(data_raw.columns)
    assert data_raw.columns[0] in segmented_data.keys()
    assert segmented_data[data_raw.columns[0]].shape == (365, 24)
    return segmented_data

@pytest.fixture
def test_feature_builder(test_period_segmenter_multivariable):
    # Tests the class that creates the features object
    feature_config = FeatureConfig(
        include_shape=True,
        include_level_mean=True,
        include_level_max=True,
        var_weights={('Household', 'Power', 'Electricity'): 1.5, ('Household', 'Power', 'DHW'): 1.0, ('PV', 'Capacity factor', 'Electricity'): 1.0},
        standardize=True
    )
    fb = FeatureBuilder(feature_config)
    X = fb.fit_transform(test_period_segmenter_multivariable)
    assert X.shape == (365, (24+2) * 3)
    return X

def test_extreme_selector(test_period_segmenter_multivariable):
    ext = ExtremeSelector([
        extreme_peak(('Household', 'Power', 'Electricity'), take=1),
        extreme_min_sum(('PV', 'Capacity factor', 'Electricity'), take=1),
        extreme_peak(('Household', 'Power', 'DHW'), take=1)
    ])
    forced = ext.select(test_period_segmenter_multivariable)
    assert 307 in forced





@pytest.fixture
def data_raw():
    data_raw = pd.read_csv(
                        os.path.join(__PARENT__, 'DATA', 'test_problem', 'test_problem_3', 'timeseries_data_full.csv'), 
                        header = [0,1,2], 
                        index_col = 0, 
                        sep = ";")
    return data_raw
