import pandas as pd
import os

def outputManager(problem, sim_id, output_dict = None):
    """
    This function takes care of all the actions required to read the output
    """
    if problem.temp_problem_folder is not None:
        output_folder = problem.temp_folder + sim_id + "\\"
    else:
        output_folder = problem.sim_folder + sim_id + "\\"
    output_units = pd.read_csv(output_folder + "output_units.txt", index_col = "Name")
    output_economics = pd.read_csv(output_folder + "output_economics.txt", index_col = "Name")
    output_KPIs = pd.read_csv(output_folder + "output_KPIs.txt", index_col="Name")
    if not isinstance(output_dict, dict):
        output_dict = createOutputDictionary([output_units, output_economics, output_KPIs])
    output_dict = updateOutputDictionary(output_dict, [output_units, output_economics, output_KPIs])
    return output_dict

def createOutputDictionary(output_dataframes):
    """
    This function creates the pandas dataframe with output values
    """
    output_dict = dict()
    for output in output_dataframes:
        for varname in output.keys():
            for idx in output.index:
                if varname != "Value":
                    output_dict[(varname, idx, "")] = []
                else:
                    output_dict[(idx, "", "")] = []
    return output_dict

def updateOutputDictionary(output_dict, output_dataframes):
    """
    This function updates the output pandas dataframe after a simulation
    """
    # output_temp = pd.DataFrame(columns= pd_output.keys(), index = [sim_id])
    for output in output_dataframes:
        for varname in output.keys():
            for idx in output.index:
                if varname != "Value":
                    output_dict[(varname, idx, "")].append(output.loc[idx, varname])
                else:
                    output_dict[(idx, "", "")].append(output.loc[idx, varname])
    return output_dict


def filterOutput(pd_output):
    """
    This function is meant to filter the output and eliminate all columns that are only zeros
    """
    columns_to_drop = []
    for column in pd_output.columns:
        if (pd_output[column] == 0).all():
            columns_to_drop.append(column)
    output = pd_output.drop(columns = columns_to_drop)
    return output