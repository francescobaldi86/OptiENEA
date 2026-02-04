from OptiENEA.classes.problem import Problem
from OptiENEA.helpers.helpers import validate_project_structure
import pandas as pd
import numpy as np
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

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
        self.run_name = name + " " + datetime.now().strftime("%Y-%m-%d %H:%M").replace(":", ".")
        self.problem = problem
        self.filename_scenario_description = filename_scenarios
        self.parametric_runs_results_folder = os.path.join(self.problem.problem_folder, 'Results', self.run_name)
        self.parametric_runs_temp_folder = os.path.join(self.problem.problem_folder, 'Temporary files', self.run_name)
        self.typical_periods = None
        self.load_scenario_file()

    def load_scenario_file(self):
        # Loads the file with the scenario description
        self.scenarios_description = pd.read_excel(
            os.path.join(self.problem.problem_folder, "Input", self.filename_scenario_description),
            'Scenarios',
            header = [0, 1, 2, 3], 
            index_col = 0,
            na_values = 'baseline',
            dtype = np.float32
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
        self.scenarios_description.insert(0, 'Run name', 'temp')

    def run(self):
        # Runs the scenarios loaded
        print(f'Start running parametric test "{self.name}"')
        self.problem.create_folders()
        self.create_folders()
        parameters_to_update = self.check_parameters_to_update()
        
        for scenario in self.scenarios_description.index:
            problem = Problem(
                name = self.problem.name, 
                problem_folder = self.problem.problem_folder,
                temp_folder = os.path.join(self.parametric_runs_temp_folder),
                results_folder = os.path.join(self.parametric_runs_results_folder)
                )
            validate_project_structure(problem.problem_folder)
            problem.create_folders()  # Creates the project folders
            problem.read_problem_data()  # Reads problem general data and data about units
            # This part updates "raw" values
            self.update_raw_parameters(parameters_to_update['Raw'], problem, scenario)
            problem.read_problem_parameters()
            if self.typical_periods is None:
                problem.generate_typical_periods()  # If needed, generates the data about the typical periods
                self.typical_periods = problem.typical_periods
            else:
                problem.typical_periods = self.typical_periods
            problem.set_occurrance()
            problem.read_units_data()  # Uses the problem data read before and saves them in the appropriate format
            problem.parse_sets()
            problem.parse_parameters()
            # This part updates "final" parameters
            self.update_problem_parameters(parameters_to_update['Problem'], problem, scenario)
            run_name = f'Scenario {scenario}'  # f'Scenario {scenario} run {datetime.now().strftime("%Y-%m-%d %H:%M").replace(":", ".")}'
            self.scenarios_description.loc[scenario, ('Run name','-','-','-')] = run_name
            problem.create_ampl_model(run_name = run_name)  # Creates the problem mod file
            print(f'Starting solving problem {problem.name} in scenario # {scenario}')
            problem.solve_ampl_problem()  # Solves the optimization problem
            print('Solution completed!')
            problem.process_output()  # Saves the output into useful and readable data structures
        self.generate_summary_output_file()

    def create_folders(self):
        try:
            os.mkdir(self.parametric_runs_results_folder)
            os.mkdir(self.parametric_runs_temp_folder)
        except FileExistsError:
            pass

    def generate_summary_output_file(self, results_folder: str | None = None):
        """
        This method creates a summary output file by reading the output
        """
        # 1 - The results include the input
        self.output = self.scenarios_description.copy(deep=True)
        # If a results folder is provided, the base one is overridden (useful if you have already the optimisation results and want to summarize them)
        if results_folder:
            self.parametric_runs_results_folder = results_folder
        # 2 - Flatte the column index
        column_names = [('Input', ':'.join([x for x in param if x not in ("-", 'Problem', 'units.yml', 'general.yml')])) for param in self.output.columns]
        self.output.columns = pd.MultiIndex.from_tuples(column_names)
        kpi_columns = [('Output', ':'.join([self.kpis.loc[x, 'Name'],self.kpis.loc[x, 'Indexing']])) for x in self.kpis.index if self.kpis.loc[x, 'Indexing'] != '-']
        kpi_columns = kpi_columns + [('Output', self.kpis.loc[x, 'Name']) for x in self.kpis.index if self.kpis.loc[x, 'Indexing'] == '-']
        temp_kpi = pd.DataFrame(index = self.output.index, columns = pd.MultiIndex.from_tuples(kpi_columns))
        # Identifying result files
        file_list = [f for f in os.listdir(self.parametric_runs_results_folder) if os.path.isfile(os.path.join(self.parametric_runs_results_folder, f))]
        file_list = [f for f in file_list if (('Results' in f) and ('.xlsx' in f))]
        for scenario, results_filename in enumerate(file_list):
            temp_output_kpis, temp_output_units = self.read_optimization_output_files(results_filename)
            if (temp_output_kpis is not None) and (temp_output_units is not None):
                for kpi in kpi_columns:
                    if len(kpi[1].split(':')) == 1:
                        temp_kpi.loc[scenario, kpi] = temp_output_kpis.loc[kpi[1]].Value
                    else:
                        temp_kpi.loc[scenario, kpi] = temp_output_units.loc[kpi[1].split(':')[1], kpi[1].split(':')[0]]
        self.output = self.output.combine_first(temp_kpi)
        self.output.to_excel(os.path.join(self.parametric_runs_results_folder, f'{self.name}_parametric_results.xlsx'))
        return self.output

        
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

    def read_optimization_output_files(self, results_filename):
        kpis = pd.read_excel(
            os.path.join(self.parametric_runs_results_folder, results_filename),
            'kpis',
            header = 0, 
            index_col = 0,
        )
        units = pd.read_excel(
            os.path.join(self.parametric_runs_results_folder, results_filename),
            'units',
            header = 0, 
            index_col = 0,
        )
        return kpis, units
    
    def plot_costs_by_scenario(
        self,
        capex_col: str = ("Output", "CAPEX"),
        opex_col: str = ("Output", "OPEX"),
        totex_col: str = ("Output", "TOTEX"),
        sort_by: str | None = ("Output", "TOTEX"),   # set None to keep original order
        show_check: bool = True,
        scenarios_to_plot: list | None = None,  # If none, plots all
        destination_folder: str | None = None, 
        filename: str | None = None
    ):
        """
        df: one row per scenario, with columns for CAPEX, OPEX, TOTEX.
        Produces stacked bars for CAPEX+OPEX and a line for TOTEX.
        """

        # --- basic validation
        required = {capex_col, opex_col, totex_col}
        missing = required - set(self.output.columns)
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        if scenarios_to_plot is not None:
            d = self.output.loc[scenarios_to_plot, [capex_col, opex_col, totex_col]].copy()
        else:
            d = self.output.loc[:, [capex_col, opex_col, totex_col]].copy()
        # optional sort
        if sort_by is not None:
            sort_col = {"CAPEX": capex_col, "OPEX": opex_col, "TOTEX": totex_col}.get(sort_by, sort_by)
            d = d.sort_values(sort_col, ascending=True)

        # --- (optional) check TO-TEX consistency
        if show_check:
            diff = (d[totex_col] - (d[capex_col] + d[opex_col])).abs()
            # You can tighten/loosen this tolerance depending on units / rounding
            if (diff > 1e-6).any():
                bad = d.index[diff > 1e-6].tolist()
                print(
                    "Warning: TOTEX != CAPEX + OPEX for scenarios: "
                    f"{bad}. (Might be fine if definitions differ.)"
                )

        # --- plot
        sns.set_theme(style="whitegrid")

        fig, ax = plt.subplots(figsize=(10, 5))

        x = d.index.astype(str)
        capex = d[capex_col].to_numpy()
        opex = d[opex_col].to_numpy()
        totex = d[totex_col].to_numpy()

        # stacked bars
        ax.bar(x, capex, label="CAPEX")
        ax.bar(x, opex, label="OPEX")

        ax.set_xlabel("Scenario")
        ax.set_ylabel("System costs")
        ax.tick_params(axis="x", rotation=30)
        ax.plot(x, totex, marker="o", linewidth=2, color = 'black', label="TOTEX")

        # combined legend (both axes)
        ax.legend(loc="upper left", frameon=True)

        plt.tight_layout()

        if destination_folder is not None:
            destination_filename = f'{filename}.png' if filename else 'Scenario-based cost analysis.png'
            plt.savefig(os.path.join(destination_folder, destination_filename))

    # ---------------------------
    # Example usage:
    # df = pd.DataFrame({
    #     "scenario": ["Base", "High PV", "High Storage"],
    #     "CAPEX": [1.2e6, 1.6e6, 1.9e6],
    #     "OPEX":  [0.4e6, 0.3e6, 0.25e6],
    #     "TOTEX": [1.6e6, 1.9e6, 2.15e6],
    # })
    # fig, axes = plot_costs_by_scenario(df)
    # plt.show()
