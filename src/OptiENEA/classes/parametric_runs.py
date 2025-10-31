from OptiENEA.classes.problem import Problem
from OptiENEA.helpers.helpers import validate_project_structure
import pandas as pd
import os
from datetime import datetime

"""
This class is made to provide support for parametric runs
"""


class ParametricRuns():
    name: str
    problem: Problem
    parametric_runs_folder: str
    filename_scenario_description: str
    scenarios_description: pd.DataFrame
    scenario_results: pd.DataFrame
    kpis: pd.DataFrame

    def __init__(self, name: str, problem: Problem, filename_scenarios: str = 'Scenarios.xlsx'):
        self.name = name
        self.problem = problem
        self.filename_scenario_description = filename_scenarios
        self.parametric_runs_folder = os.path.join(self.problem.problem_folder, f'Parametric run {self.name}')
        self.load_scenario_file()

    def load_scenario_file(self):
        # Loads the file with the scenario description
        self.scenarios_description = pd.read_excel(
            os.path.join(self.problem.problem_folder, "Input", self.filename_scenario_description),
            'Scenarios',
            header = [0, 1, 2, 3], 
            index_col = 0,
            na_values = 'baseline'
        )
        self.kpis = pd.read_excel(
            os.path.join(self.problem.problem_folder, "Input", self.filename_scenario_description),
            'KPIs',
            header = 0, 
            index_col = 0,
            na_values = 'baseline'
        )
        # Makes sure "baseline" data is read as the baseline scenario
        baseline_scenario = self.scenarios_description.index[0]
        for scenario in self.scenarios_description.index:
            for param in self.scenarios_description.columns:
                if pd.isna(self.scenarios_description.loc[scenario, param]):
                    self.scenarios_description.loc[scenario, param] = self.scenarios_description.loc[baseline_scenario, param]

    def run(self):
        # Runs the scenarios loaded
        self.create_folders()
        parameters_to_update = self.check_parameters_to_update()
        self.scenarios_description.insert(0, 'Run name', 'temp')
        for scenario in self.scenarios_description.index:
            problem = Problem(
                name = self.problem.name, 
                problem_folder = self.problem.problem_folder,
                temp_folder = os.path.join(self.parametric_runs_folder, 'Temporary files'),
                results_folder = os.path.join(self.parametric_runs_folder, 'Results')
                )
            validate_project_structure(problem.problem_folder)
            problem.create_folders()  # Creates the project folders
            problem.read_problem_data()  # Reads problem general data and data about units
            # This part updates "raw" values
            self.update_raw_parameters(parameters_to_update['Raw'], problem, scenario)
            problem.read_problem_parameters()
            problem.read_units_data()  # Uses the problem data read before and saves them in the appropriate format
            problem.parse_sets()
            problem.parse_parameters()
            # This part updates "final" parameters
            self.update_problem_parameters(parameters_to_update['Problem'], problem, scenario)
            run_name = f'Scenario {scenario} run {datetime.now().strftime("%Y-%m-%d %H:%M").replace(":", ".")}'
            self.scenarios_description.loc[scenario, ('Run name','-','-','-')] = run_name
            problem.create_ampl_model(run_name = run_name)  # Creates the problem mod file
            problem.solve_ampl_problem()  # Solves the optimization problem
            problem.save_output()  # Saves the output into useful and readable data structures

    def create_folders(self):
        try:
            os.mkdir(self.parametric_runs_folder)
        except FileExistsError:
            pass

    def generate_summary_output_file(self):
        """
        This method creates a summary output file by reading the output
        """
        # 1 - The results include the input
        self.output = self.scenarios_description.copy(deep=True)
        # 2 - Flatte the column index
        column_names = [('Input', ':'.join([x for x in param if x not in ("-", 'Problem', 'units.yml', 'general.yml')])) for param in self.output.columns]
        self.output.columns = pd.MultiIndex.from_tuples(column_names)
        kpi_columns = [('Output', ':'.join([self.kpis.loc[x, 'Name'],self.kpis.loc[x, 'Indexing']])) for x in self.kpis.index if self.kpis.loc[x, 'Indexing'] != '-']
        kpi_columns = kpi_columns + [('Output', self.kpis.loc[x, 'Name']) for x in self.kpis.index if self.kpis.loc[x, 'Indexing'] == '-']
        temp_kpi = pd.DataFrame(index = self.output.index, columns = pd.MultiIndex.from_tuples(kpi_columns))
        for scenario in self.scenarios_description.index:
            temp_output_kpis, temp_output_units = self.read_optimization_output_files(self.output.loc[scenario, ('Input','Run name')])
            for kpi in kpi_columns:
                if len(kpi[1].split(':')) == 1:
                    temp_kpi.loc[scenario, kpi] = temp_output_kpis.loc[kpi[1]].Value
                else:
                    temp_kpi.loc[scenario, kpi] = temp_output_units.loc[kpi[1].split(':')[1], kpi[1].split(':')[0]]
        self.output = self.output.combine_first(temp_kpi)
        self.output.to_excel(os.path.join(self.problem_folder, f'{self.name}_parametric_results.xlsx'))

        
    def scenarios_to_run(self, scenarios_to_run: str = 'all'):
        if scenarios_to_run == 'all': 
            # Run all scenarios
            pass
        else:
            try:
                self.scenarios_description = self.filename_scenario_description.loc[self.scenarios_description[scenarios_to_run] == True, :]
            except KeyError:
                raise(f'Column name "{scenarios_to_run}" was not found in the scenario description database')
            
    def check_parameters_to_update(self):
        parameters_to_update = {'Problem': [], 'Raw': []}
        for par in self.scenarios_description.columns:
            if par[0] == 'Problem':
                parameters_to_update['Problem'].append(par)
            else:
                parameters_to_update['Raw'].append(par)
        return parameters_to_update
    
    def update_raw_parameters(self, raw_parameters_to_update, problem, scenario):
        for param in raw_parameters_to_update:
            for data_type in ('units', 'general'):
                if data_type in param[0]:
                    path = [x for x in param[1:] if x != '-']
                    problem.update_problem_data(data_type, path, self.scenarios_description.loc[scenario, param])
        return problem
    
    def update_problem_parameters(self, problem_parameters_to_update, problem, scenario):
        for param in problem_parameters_to_update:
            param_name = param[1]
            indexing = tuple([x for x in param[2:] if x != '-'])
            problem.update_problem_parameters(param_name, indexing, self.scenarios_description.loc[scenario, param])
        return problem

    def read_optimization_output_files(self, run_name):
        kpis = pd.read_excel(
            os.path.join(self.parametric_runs_folder, "Results", f'Results_{run_name}.xlsx'),
            'kpis',
            header = 0, 
            index_col = 0,
        )
        units = pd.read_excel(
            os.path.join(self.parametric_runs_folder, "Results", f'Results_{run_name}.xlsx'),
            'units',
            header = 0, 
            index_col = 0,
        )
        return kpis, units