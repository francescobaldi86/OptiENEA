from OptiENEA.classes.problem import Problem
from OptiENEA.classes.typical_periods import *
import os, shutil, math, pytest, copy, yaml
import pandas as pd
import time

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

def test_clustering(data_raw, feature_config, typical_period_config):
    builder = TypicalPeriodBuilder(feature_config, typical_period_config)
    tp = builder.build(data_raw)
    assert all([i <= 0.01 for _, i in tp.meta["energy_errors"].items()])
    assert True

def test_evaluation_metrics(data_raw, feature_config, typical_period_config):
    # First example: energy correction cluster-wise
    typical_period_clusterwise = copy.copy(typical_period_config)
    builder = TypicalPeriodBuilder(feature_config, typical_period_clusterwise)
    tp = builder.build(data_raw)
    evaluator = TypicalPeriodEvaluator()
    evaluation_clusterwise = evaluator.evaluate(tp, data_raw)
    typical_period_global = copy.copy(typical_period_config)
    typical_period_global.energy_correction = 'global'
    builder = TypicalPeriodBuilder(feature_config, typical_period_global)
    tp = builder.build(data_raw)
    evaluation_global = evaluator.evaluate(tp, data_raw)
    assert True

def test_evaluation_metrics_for_different_K(data_raw, feature_config, typical_period_config):
    # First example: energy correction cluster-wise
    output = pd.DataFrame(index = [x+1 for x in range(10)], columns = data_raw.columns)
    for n_clusters in output.index:
        typical_period_config.K = n_clusters
        builder = TypicalPeriodBuilder(feature_config, typical_period_config)
        tp = builder.build(data_raw)
        evaluator = TypicalPeriodEvaluator()
        temp = evaluator.evaluate(typical_periods=tp, original_data=data_raw)
        for var in output.columns:
            output.loc[n_clusters, var] = temp.metrics[var]['rmse']
    assert all([output.iloc[0, id] > output.iloc[-1, id] for id in range(len(output.columns))])

def test_export_to_ampl(data_raw, feature_config, typical_period_config):
    builder = TypicalPeriodBuilder(feature_config, typical_period_config)
    tp = builder.build(data_raw)
    ampl_param = tp.to_ampl_params()
    assert True

def test_example_problem(tmp_path):
    problem_folder = os.path.join(tmp_path, f'test_problem_typical_periods')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_3', 'units.yml'), 
                    os.path.join(input_data_folder, 'units.yml'))
    shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_3', 'timeseries_data_full.csv'), 
                    os.path.join(input_data_folder, 'timeseries_data.csv'))
    shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_typical_periods', 'test_typical_periods_day.yml'), 
                     os.path.join(input_data_folder, 'general.yml'))
    problem = Problem(name = f'test_problem_typical_periods', 
                      problem_folder = problem_folder)
    problem.run()

def test_example_problem_comparison(tmp_path):
    # This test runs both the original problem and the one with typical days, and compare results and speed
    # 1 - "Standard" problem
    problem_folder = os.path.join(tmp_path, f'test_problem_base')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_3', 'units.yml'), 
                    os.path.join(input_data_folder, 'units.yml'))
    shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_3', 'timeseries_data_full.csv'), 
                    os.path.join(input_data_folder, 'timeseries_data.csv'))
    shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', f'test_problem_3', 'general.yml'), 
                     os.path.join(input_data_folder, 'general.yml'))
    # Changing the required settings in general.yml
    with open(os.path.join(input_data_folder,'general.yml'), "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["Standard parameters"]["NT"] = 8760
    data["Standard parameters"]["Occurrance"] = 1
    with open(os.path.join(input_data_folder,'general.yml'), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False),  # keep key order
    # Start simulation
    start = time.time()
    problem_standard = Problem(name = f'test_problem_standard', 
                      problem_folder = problem_folder)
    problem_standard.run()
    elapsed_time_standard = time.time() - start
    # 2 - "Typical periods" problem
    
    shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_typical_periods', 'test_typical_periods_day.yml'), 
                     os.path.join(input_data_folder, 'general.yml'))
    start = time.time()
    problem_typical_periods = Problem(name = f'test_problem_typical_periods', 
                      problem_folder = problem_folder)
    problem_typical_periods.run()
    elapsed_time_typical_periods = time.time() - start
    assert elapsed_time_standard > elapsed_time_typical_periods
    assert math.isclose(problem_standard.output.output_units.loc['PV', 'size'], problem_typical_periods.output.output_units.loc['PV', 'size'])
    assert math.isclose(problem_standard.output.output_units.loc['battery', 'size'], problem_typical_periods.output.output_units.loc['battery', 'size'])


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
        var_weights={('Household', 'Power', 'Electricity'): 2.0, ('Household', 'Power', 'DHW'): 1.0, ('PV', 'Capacity factor', 'Electricity'): 1.5},
        standardize=True
    )

@pytest.fixture
def typical_period_config(extreme_days_configuration):
    return TypicalPeriodConfig(
        K=3,
        period="day",
        energy_correction="clusterwise",
        extreme_selector=extreme_days_configuration,
        extreme_weight_mode="deduct",
        random_state=1
    )