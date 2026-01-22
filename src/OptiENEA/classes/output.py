import numpy as np
import pandas as pd
from typing import Optional, Sequence, Union
import os
from OptiENEA.classes.amplpy import AmplProblem
from OptiENEA.classes.typical_periods import TypicalPeriodSet
from dataclasses import dataclass, field
from copy import copy

@dataclass
class OptimizationOutput:
    ampl: AmplProblem
    varnames_output: dict
    results_folder: str
    typical_periods: TypicalPeriodSet = None
    output_kpis: list = field(default_factory=list)
    output_units: pd.DataFrame = field(default_factory=pd.DataFrame)
    output_timeseries: pd.DataFrame = field(default_factory=pd.DataFrame)
    output_extra: dict = field(default_factory=dict)
    
    def generate_output_structures(self):
        for var_name, var_info in self.varnames_output.items():
            if var_info.indexed_over == None:
                self.output_kpis.append({'KPI': var_name, 'Value': self.ampl.get_variable(var_name).value()})
            elif 'timeSteps' in var_info.indexed_over:
                temp = self.ampl.get_variable(var_name).get_values().to_pandas()
                temp.columns = [x.strip('.val') for x in temp.columns]
                temp = temp.unstack(level=[0, 1])
                # output['timeseries'] = temp.combine_first(output['timeseries'])
                if self.typical_periods is not None:
                    temp = self.reconstruct_output_ts_data_from_typical_periods(temp)
                self.output_timeseries = pd.concat([self.output_timeseries, temp], axis = 1)
            elif 'nonmarketUtilities' in var_info.indexed_over:
                temp = self.ampl.get_variable(var_name).get_values().to_pandas()
                temp.columns = [x.strip('.val') for x in temp.columns]
                self.output_units = temp.combine_first(self.output_units)
            else:
                self.output_extra[var_name] = self.ampl.get_variable(var_name).get_values().to_pandas()
                self.output_extra[var_name].columns = [x.strip('.val') for x in self.output_extra[var_name].columns]
        self.output_timeseries_full = copy(self.output_timeseries)
        columns_to_drop = []
        for column in self.output_timeseries.columns:
            if (self.output_timeseries[column] == 0).all():
                columns_to_drop.append(column)
        self.output_timeseries = self.output_timeseries.drop(columns=columns_to_drop, axis=1)
        self.output_kpis = pd.DataFrame(self.output_kpis).set_index('KPI')
    
    def save_output_to_excel(self, run_name):
        # Writing all output to Excel
        with pd.ExcelWriter(os.path.join(self.results_folder, f"Results_{run_name}.xlsx"), engine="xlsxwriter") as writer:
            self.output_kpis.to_excel(writer, sheet_name='kpis', float_format = "%.3f")
            self.output_units.to_excel(writer, sheet_name='units', float_format = "%.3f")
            self.output_timeseries.to_excel(writer, sheet_name='timeseries', float_format = "%.3f")
            self.output_timeseries_full.to_excel(writer, sheet_name='timeseries_full', float_format = "%.3f")
            for sheet_name, df in self.output_extra.items():
                if not df.empty:
                    df.to_excel(writer, sheet_name=sheet_name, float_format = "%.3f")


    def reconstruct_output_ts_data_from_typical_periods(self, df) -> pd.DataFrame:
        """
        Reconstruct an 8760-like hourly DataFrame from typical-period results.

        Parameters
        ----------
        Returns
        -------
        pd.DataFrame with length P*hours_per_period and same columns as df_typ.
        """
        out_array = []
        for tp_id in range(len(self.typical_periods.assignment)):
            out_array.append(df.xs(self.typical_periods.assignment[tp_id], level = 0))
        output = pd.concat(out_array)
        output.index = np.arange(len(self.typical_periods.assignment) * self.typical_periods.L)
        return output