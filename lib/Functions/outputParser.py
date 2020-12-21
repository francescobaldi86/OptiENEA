import pandas as pd
import os

def outputManager(problem, sim_id, output_dict = None):
    """
    This function takes care of all the actions required to read the output
    """
    if problem.temp_problem_folder is not None:
        filename_output = problem.temp_folder + sim_id + "\\output.out"
    else:
        filename_output = problem.sim_folder + sim_id + "\\output.out"
    variables_to_read = problem.main["Outputs of interest"]
    output_sim = parserOutput(filename_output, variables_to_read)
    if not isinstance(output_dict, dict):
        output_dict = createOutputDictionary(output_sim)
    output_dict = updateOutputDictionary(output_dict, output_sim)
    return output_dict

def parserOutput(filename_output, variables_to_read):
    output = dict()
    with open(filename_output, "r") as output_file:
        counter = 0
        read = False
        for line in output_file:
            if "Column name" in line:
                read = True
            if "Karush" in line: # This means it has found the "Karus-Tucker" optimal conditions line
                break
            if read:
                for variable in variables_to_read:
                    if variable in line:
                        if len(line.split()) == 2:
                            output = readVariable(output, variable, line, next(output_file))
                        else:
                            output = readVariable(output, variable, line, False)
    os.remove(filename_output)
    return output

def readVariable(output, variable, line, next_line):
    indeces = line[line.find("[") + 1:line.find("]")].split(",")
    if len(indeces) == 1 and len(line[line.find("[") + 1:line.find("]")].split()) == 1:
        if variable not in output.keys():
            output[variable] = {}
        if next_line:
            output[variable][indeces[0]] = float(next_line.split()[1])
        else:
            output[variable][indeces[0]] = float(line.split()[3])
    else:
        output[variable] = float(line.split()[3])
    return output

def createOutputDictionary(output_sim):
    """
    THis function creates the pandas dataframe with output values
    """
    output_dict = dict()
    for variable, value in output_sim.items():
        if isinstance(value, float):
            output_dict[(variable, "", "")] = []
        elif isinstance(value, dict):
            for variable_2, value_2 in value.items():
                output_dict[(variable, variable_2, "")] = []
    return output_dict

def updateOutputDictionary(output_dict, output_sim):
    """
    This function updates the output pandas dataframe after a simulation
    """
    # output_temp = pd.DataFrame(columns= pd_output.keys(), index = [sim_id])
    for variable, value in output_sim.items():
        if isinstance(value, float):
            output_dict[(variable, "", "")].append(value)
        elif isinstance(value, dict):
            for variable_2, value_2 in value.items():
                output_dict[(variable, variable_2, "")].append(value_2)
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