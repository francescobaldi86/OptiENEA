from OptiENEA.classes.problem import Problem
from OptiENEA.classes.typical_periods import *
import os, shutil, math, pytest
import pandas as pd

__HERE__ = os.path.dirname(os.path.realpath(__file__))
__PARENT__ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def test_period_segmenter():
    # The periods segmenter, in principle, takes a time series and segments it into periods of a given size
    # First, let's read test data
    data_raw = pd.read_csv(
                        os.path.join(__PARENT__, 'DATA', 'test_problem', 'test_problem_3', 'timeseries_data_full.csv'), 
                        header = [0,1,2], 
                        index_col = 0, 
                        sep = ";")
    series = data_raw[('Household', 'Power', 'Electricity')]
    test_segmenter = PeriodSegmenter(period = 'day')
    assert True
    
    