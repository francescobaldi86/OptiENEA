from OptiENEA.classes.problem import Problem
from OptiENEA.classes.set import Set
from OptiENEA.classes.parameter import Parameter
from OptiENEA.classes.amplpy import AmplProblem
from OptiENEA.classes.unit import *
import os, pytest, shutil, math

__HERE__ = os.path.dirname(os.path.realpath(__file__))
__PARENT__ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def test_create_empty_problem():
    # Tests the creation of an empty problem
    problem = Problem(name = 'test_problem')
    assert problem.name == 'test_problem'
    assert isinstance(problem.sets, dict)
    assert isinstance(problem.sets['timeSteps'], Set)
    assert isinstance(problem.parameters, dict)
    assert isinstance(problem.parameters['POWER'], Parameter)


def test_create_problem_folders():
    # Once the problem has been created, it tests the creation of the related folders
    os.mkdir(os.path.join(__PARENT__,'PLAYGROUND','test_problem'))  
    problem = Problem(name = 'test_problem', 
                      problem_folder = os.path.join(__PARENT__,'PLAYGROUND','test_problem'))
    problem.create_folders()
    
    assert os.path.isdir(os.path.join(__PARENT__,'PLAYGROUND','test_problem'))
    assert os.path.isdir(os.path.join(__PARENT__,'PLAYGROUND','test_problem', 'Results'))
    assert os.path.isdir(os.path.join(__PARENT__,'PLAYGROUND','test_problem', 'Temporary files'))

    os.rmdir(os.path.join(__PARENT__,'PLAYGROUND','test_problem', 'Results'))
    os.rmdir(os.path.join(__PARENT__,'PLAYGROUND','test_problem', 'Temporary files'))
    os.rmdir(os.path.join(__PARENT__,'PLAYGROUND','test_problem'))
    

def test_read_problem_data(problem_with_data):
    # Tests the reading of problem data
    problem = problem_with_data

    assert isinstance(problem.raw_general_data, dict)
    assert isinstance(problem.raw_unit_data, dict)
    assert problem.raw_general_data['Settings']['Problem type'] == 'LP'
    assert problem.raw_general_data['Settings']['Objective'] == 'TOTEX'
    assert isinstance(problem.raw_general_data['Standard parameters'], dict)
    assert problem.raw_unit_data['WindFarm']['Type'] == 'Process (producer)'
    assert problem.raw_unit_data['WindFarm']['Power'] == 'file'
    assert problem.raw_unit_data['Market']['Type'] == 'SellingMarket'
    assert problem.raw_unit_data['Market']['Max installed power'] == [10000]


def test_read_problem_parameters(problem_with_general_parameters):
    problem = problem_with_general_parameters

    assert problem.interpreter == 'ampl'
    assert problem.solver == 'highs'
    assert problem.interest_rate == 0.07
    assert problem.simulation_horizon == 8760
    assert problem.parameters["OCCURRANCE"].content == 1
    assert problem.parameters["TIME_STEP_DURATION"].content == 1


def test_read_units_data(problem_with_unit_data):
    units = problem_with_unit_data.units
    layers = problem_with_unit_data.layers

    assert isinstance(units, dict)
    assert isinstance(units['WindFarm'], Unit)
    assert isinstance(units['WindFarm'], Process)
    assert isinstance(units['Market'], Market) 
    assert units['Battery'].c_rate == 1.0
    assert isinstance(units['WindFarm'].power, dict)  # Only one layer
    assert isinstance(units['WindFarm'].power['Electricity'], pd.Series)
    assert len(units['WindFarm'].power['Electricity']) == 8760  # Only one typical day

def test_parse_sets(problem_with_unit_data):
    # Tests the "process_problem_data" function
    problem_with_unit_data.parse_sets()
    assert problem_with_unit_data.sets['processes'].content == {'WindFarm'}
    assert problem_with_unit_data.sets['layersOfUnit'].content['BatteryCharger'] == {'Electricity', 'StoredElectricity'}
    assert problem_with_unit_data.sets['chargingUtilitiesOfStorageUnit'].content['Battery'] == {'BatteryCharger'}
    assert problem_with_unit_data.sets['mainLayerOfUnit'].content['Market'] == {'Electricity'}
    assert problem_with_unit_data.sets['layers'].content == {'Electricity', 'StoredElectricity'}

def test_parse_parameters(problem_with_unit_data):
    # Tests the "process_problem_data" function
    problem_with_unit_data.parse_parameters()
    assert problem_with_unit_data.parameters['POWER']().loc[('WindFarm','Electricity', 3), 'POWER'] == -43.688
    assert problem_with_unit_data.parameters['OCCURRANCE']() == 1
    assert problem_with_unit_data.parameters['CRATE']().loc['Battery', 'CRATE'] == 1.0
    assert problem_with_unit_data.parameters['ENERGY_AVERAGE_PRICE']().loc[('Market', 'Electricity'), 'ENERGY_AVERAGE_PRICE'] == 0.0478

def test_create_ampl_problem(problem_with_all_data):
    problem_with_all_data.create_ampl_model()
    ampl_sets = problem_with_all_data.ampl_problem.get_sets()
    ampl_parameters = problem_with_all_data.ampl_problem.get_parameters()
    assert ampl_parameters['OCCURRANCE'].value() == 1
    ampl_parameters['POWER'][('WindFarm', 'Electricity', 3)] == 43.688

def test_solve_ampl_problem(problem_with_all_data):
    problem_with_all_data.create_ampl_model()
    problem_with_all_data.solve_ampl_problem()
    
    assert problem_with_all_data.ampl_problem.solve_result == "solved"
    assert math.isclose(problem_with_all_data.ampl_problem.get_variable('OPEX').value(), -12415, abs_tol = 1)
    assert math.isclose(problem_with_all_data.ampl_problem.get_variable('CAPEX').value(), 0, abs_tol = 1)
    assert math.isclose(problem_with_all_data.ampl_problem.get_variable('OPEX').value(),
                        problem_with_all_data.ampl_problem.get_variable('TOTEX').value(), 
                        abs_tol = 1)
    
def test_write_problem_output(solved_problem):
    solved_problem.save_output()
    # Here we check that the file was generated, and that it contains the right sheets
    for sheet in ['kpis', 'units', 'timeseries']:
        _ = pd.read_excel(
            os.path.join(solved_problem.problem_folder, 'Results', 'Results.xlsx'),
            sheet_name = sheet
        )
    assert True


@pytest.fixture
def problem_base():
    problem_folder = os.path.join(__PARENT__, 'PLAYGROUND', 'test_problem')
    input_data_folder = os.path.join(problem_folder, 'Input')
    os.mkdir(problem_folder)
    os.mkdir(input_data_folder)
    for filename in ('units.yml', 'general.yml', 'timeseries_data.csv'):
        shutil.copy2(os.path.join(__PARENT__, 'DATA', 'test_problem', filename), 
                     os.path.join(input_data_folder, filename))

    problem = Problem(name = 'test_problem', 
                      problem_folder = problem_folder)
    problem.create_folders()
    # Problem setup this way is what we want to give to tests
    yield problem
    # Then we clean up
    shutil.rmtree(problem_folder)



@pytest.fixture
def problem_with_data(problem_base):
    problem_base.read_problem_data()
    return problem_base

@pytest.fixture
def problem_with_general_parameters(problem_with_data):
    problem_with_data.read_problem_parameters()
    return problem_with_data

@pytest.fixture
def problem_with_unit_data(problem_with_general_parameters):
    problem_with_general_parameters.read_units_data()
    return problem_with_general_parameters

@pytest.fixture
def problem_with_all_data(problem_with_general_parameters):
    problem_with_general_parameters.read_units_data()
    problem_with_general_parameters.parse_sets()
    problem_with_general_parameters.parse_parameters()
    return problem_with_general_parameters

@pytest.fixture
def solved_problem(problem_with_all_data):
    problem_with_all_data.create_ampl_model()
    problem_with_all_data.solve_ampl_problem()
    return problem_with_all_data