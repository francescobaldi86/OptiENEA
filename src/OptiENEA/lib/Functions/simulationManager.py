import pandas as pd
import chevron
from shutil import copyfile
import os
import sys
import subprocess
import copy
import importlib
import time
import math
from lib.Functions.parametricAnalysis import parametricSimulationMatrix
# from lib.sensitivityAnalysis import generateSensitivitySample
from lib.Functions.helpers import referenceOrUpdated
import lib.Functions.outputParser as out


def simulationManager(problem):
    """
    This function simply prepares the whole simulations setup
    """
    problem, simulation_matrix, full_simulation_matrix = saveSimulationMatrix(problem)
    writeProblemSets(problem) # The problem sets are written only once, at the beginning
    copyfile(problem.optienea_folder + "problem_types\\" + problem.problem_type + "\\mod_file.mod",
             problem.sim_folder + "mod_file.mod")
    # Now we can finally run the simulations
    counter = 0
    elapsed_time, start_time = 0, time.time()
    output = None
    for sim in simulation_matrix.index:
        counter += 1
        parameters = copy.deepcopy(problem.parameters)
        set_output(problem, sim)  # The output writing system is updated only once, at the beginning
        if sim != "REF":
            parameters = updateParameters(parameters, problem, simulation_matrix.loc[sim, :])
        parameters = runCustomPythonCode(problem.problem_folder, simulation_matrix.loc[sim, :], parameters)
        writeProblemParameters(parameters, simulation_matrix.loc[sim, :], problem)
        runSimulation(problem, sim, counter, len(simulation_matrix.index), elapsed_time)
        elapsed_time = time.time() - start_time
        output = out.outputManager(problem, sim, output)
    output = pd.DataFrame(output, index = simulation_matrix.index)
    output = out.filterOutput(output)
    output.to_csv(problem.sim_folder + "output.csv")
    pd.concat([simulation_matrix, output], axis=1).to_csv(problem.sim_folder + "output_full.csv")
    return output, simulation_matrix

def saveSimulationMatrix(problem):
    # First we create the dataframe based on the reference simulation
    full_simulation_matrix = saveReferenceParameterValues(problem)
    # Part 2: Other simulations
    if "parametric" in problem.analysis:
        full_simulation_matrix = parametricSimulationMatrix(problem, full_simulation_matrix)
    #if "GSA" in problem["Main"]["Analysis"]:
        # problem, simulation_matrix = generateSensitivitySample(problem, simulation_matrix)
    problem.nSim = len(full_simulation_matrix)
    full_simulation_matrix.to_csv(problem.sim_folder + "full_simulation_matrix.csv")
    simulation_matrix = full_simulation_matrix.copy()
    for col in full_simulation_matrix.keys():
        temp = simulation_matrix[col].to_numpy()
        if (temp[0] == temp).all() or simulation_matrix[col].isnull().all():
            simulation_matrix = simulation_matrix.drop(columns = [col])
    simulation_matrix.to_csv(problem.sim_folder + "simulation_matrix.csv")
    return problem, simulation_matrix, full_simulation_matrix


def saveReferenceParameterValues(problem):
    """
    This function is used to save all problem inputs into one input matrix.
    For reasons of readability, this is not done for parameters indexed on time steps
    """
    output = {}
    for param, value in problem.parameters["0"].items():
        output[(param, "","")] = value
    for param, slice in problem.parameters["1"].items():
        if len(slice) <= 10:  # This prevents reading parameters indexed on time steps
            for slice_name, slice_value in slice.items():
                output[(param, slice_name, "")] = slice_value
    for param, slice_1 in problem.parameters["2"].items():
        if len(slice_1) <= 10:
            for slice_name_1, slice_2 in slice_1.items():
                if len(slice_2) <= 10: # This prevents reading parameters indexed on time steps
                    for slice_name_2, slice_value in slice_2.items():
                        output[(param, slice_name_1, slice_name_2)] = slice_value
    for param, value in problem.parameters["extra"].items():
        output[(param, "", "")] = value
    return pd.DataFrame(output, index = ["REF"])


def writeProblemSets(problem):
    """
    This function is used to write the sets of the problem into a .dat input file for GLPK
    Note: In the current version of OptiENEA, the sets are defined once and for all, to save time
    """
    # First we read the data for 0-Dimensional sets, i.e. non-indexed sets
    output = {}
    output["0D"] = list()
    for set_name, set_content in problem.sets["0"].items():
        objects = list()
        for object in set_content:
            objects.append({"name": object})
        output["0D"].append({"set_name": set_name, "objects": objects})
    # Then we parse the date for 1-Dimensional sets, i.e. sets that are indexed on another set
    output["1D"] = list()
    for set_name, set_content in problem.sets["1"].items():
        for slice_name, slice_content in set_content.items():
            objects = list()
            for object in slice_content:
                objects.append({"name": object})
            output["1D"].append({"set_name": set_name, "slice_name": slice_name, "objects": objects})
    # Finally we write the data file with the sets information
        with open(problem.optienea_folder + "problem_types\\" + problem.problem_type + "\\data_sets.mustache", "r") as f:
            data_sets = chevron.render(f, output)
        with open(problem.sim_folder + "sets.dat", "w") as f:
            f.write(data_sets)
    return None


def writeProblemParameters(parameters, data, problem):
    """
    This function is used to write the parameters of the problem into a .dat input file for GLPK
    """
    # First we read the data for 0-Dimensional parameters, i.e. single-value parameters
    problem_type = problem.problem_type
    output = dict()
    output["0D"] = list()
    for param_name, value in parameters["0"].items():
        if (param_name, "", "") in data.keys() and not math.isnan(data[(param_name, "", "")]):
            output["0D"].append({"param_name": param_name, "value": data[(param_name, "", "")]})
        else:
            output["0D"].append({"param_name": param_name, "value": value})
    # Then we parse the date for 1-Dimensional parameters, i.e. parameters that are indexed on one set
    output["1D"] = list()
    for param_name, param_content in parameters["1"].items():
        objects = list()
        for slice_name, value in param_content.items():
            if (param_name, slice_name, "") in data.keys() and not math.isnan(data[(param_name, slice_name, "")]):
                objects.append({"name": slice_name, "value": data[(param_name, slice_name, "")]})
            else:
                objects.append({"name": slice_name, "value": value})
        output["1D"].append({"param_name": param_name, "objects": objects})
    # Then we parse the data for 2-dimensional parameters, indexed on two different sets
    output["2D"] = list()
    for param_name, param_content in parameters["2"].items():
        slice_1 = list()
        for slice_1_name, slice_1_content in param_content.items():
            slice_2 = list()
            for slice_2_name, value in slice_1_content.items():
                if (param_name, slice_1_name, slice_2_name) in data.keys() and not math.isnan(data[(param_name, slice_1_name, slice_2_name)]):
                    slice_2.append({"name": slice_2_name, "value": data[(param_name, slice_1_name, slice_2_name)]})
                else:
                    slice_2.append({"name": slice_2_name, "value": value})
            slice_1.append({"name": slice_1_name, "slice_2": slice_2})
        output["2D"].append({"param_name": param_name, "slice_1": slice_1})

    # NOTE, VERY IMPORTANT!!! IN THIS MOMENT PARAMETERS WITH 3 INDEXES CANNOT BE CHANGED AFTERWARDS
    output["3D"] = list()
    for param_name, param_content in parameters["3"].items():
        slice = list()
        for slice_1_name, slice_1_content in param_content.items():
            for slice_2_name, slice_2_content in slice_1_content.items():
                object = list()
                for slice_3_name, param_value in slice_2_content.items():
                    object.append({"name_3": slice_3_name, "value": param_value})
                slice.append({"name_1": slice_1_name, "name_2": slice_2_name, "objects": object})
        output["3D"].append({"param_name": param_name, "slice": slice})
    # Finally we write the data file with the sets information
    with open(problem.optienea_folder + "problem_types\\" + problem_type + "\\data_parameters.mustache", "r") as f:
        data_parameters = chevron.render(f, output)
    if problem.temp_folder is None:
        os.mkdir(problem.sim_folder + data.name)
        filename = problem.sim_folder + data.name + "\\parameters.dat"
    else:
        os.mkdir(problem.temp_folder + data.name)
        filename = problem.temp_folder + data.name + "\\parameters.dat"
    with open(filename, "w") as f:
        f.write(data_parameters)
    return None


def runSimulation(problem, simname, counter, nsim_tot, elapsed_time):
    """
    This is the function that actually runs the simulations
    """
    if problem.temp_problem_folder is None:
        os.chdir(problem.sim_folder + simname)  # Changes the current directory to the output folder
    else:
        if counter == 1:
            copyfile(problem.sim_folder + "mod_file.mod", problem.temp_folder + "mod_file.mod")
            copyfile(problem.sim_folder + "sets.dat", problem.temp_folder + "sets.dat")
        os.chdir(problem.temp_folder + simname)  # Changes the current directory to the output folder
    # temp = os.system("glpsol -m ..\\mod_file.mod -d ..\\sets.dat -d parameters.dat -o output.out --log log.txt")
    if elapsed_time == 0:
        time_left = " is unknown"
    else:
        time_left = ": " + "{:.0f}".format((nsim_tot - counter + 1) * elapsed_time / (counter-1) / 60) + " minutes"
    print("Start sim. # " + str(counter) + " of " + str(nsim_tot) + ". Expected time left" + time_left)

    if problem.interpreter == "ampl":
        solve_ampl_problem(problem, simname)
    if problem.interpreter == "glpk":
        solve_glpk_problem(problem.solver_options)

    return None


def solve_ampl_problem(problem, simname):
    """
    This function prepares the call for the optimization using AMPL
    """
    copyfile(problem.sim_folder + problem.filenames["runfile"], problem.temp_folder + simname + "\\" + problem.filenames["runfile"])
    subprocess.run(["ampl", problem.filenames["runfile"]])
    return None


def solve_glpk_problem(solver_options):
    """
    This function prepares the call for the optimization using GLPK
    """
    run_list = ["glpsol", "-m", "..\\mod_file.mod", "-d", "..\\sets.dat", "-d", "parameters.dat", "--log", "log.txt"]
    for option, value in solver_options.items():
        run_list.append(option)
        run_list.append(value)
    subprocess.run(run_list, stdout=subprocess.DEVNULL)
    return None

def set_output(problem, simname):
    """
    This function serves the purpose of including in the mod or run file the required information for printing the output
    """
    output_structure = [
        {"type": "indexed", "filename": "output_units.txt", "column_names": ["Size", "C_INV"], "var_names": ["size", "unitAnnualizedInvestmentCost"], "set": "nonmarketUtilities"},
        {"type": "indexed", "filename": "output_economics.txt", "column_names": ["C_OP"], "var_names": ["layer_operating_cost"], "set": "outputMarketLayers", "setdim": 2},
        {"type": "values", "filename": "output_KPIs.txt", "var_names": ["CAPEX", "OPEX", "obj"]}]
    if problem.interpreter == "glpk":
        writePrintfStatementsForGlpk(output_structure, problem.sim_folder)
    elif problem.interpreter == "ampl":
        writePrintfStatementsForAmpl(output_structure, problem, simname)

    return None


def writePrintfStatementsForGlpk(output_structure, sim_folder):
    output_setup_string = ""
    output_setup_string += "\n \n solve; \n\n"
    for output in output_structure:
    # If the value is indexed over a set:
        if output["type"] == "indexed":
            output_setup_string += 'printf "%s' + ',%s'*len(output["column_names"]) + '\\n", "Name"'
            for name in output["column_names"]:
                output_setup_string += ', "' + name + '"'
            output_setup_string += ' > "' + output["filename"] + '"; \n'
            if "setdim" not in output.keys():
                output_setup_string += 'for {i in ' + output["set"] + '} {\n \t printf '
            else:
                output_setup_string += 'for {(i,j) in ' + output["set"] + '} {\n \t printf '
            if "setdim" not in output.keys():
                output_setup_string += '"%s' + ',%.1f'*len(output["column_names"]) + '\\n", i'
            else:
                output_setup_string += '"%s:%s' + ',%.1f'*len(output["column_names"]) + '\\n", i,j'
            for variable in output["var_names"]:
                if "setdim" not in output.keys():
                    output_setup_string += ', ' + variable + "[i]"
                else:
                    output_setup_string += ', ' + variable + "[i,j]"
            output_setup_string += ' >> "' + output["filename"] + '" ;\n'
            output_setup_string += '}\n'
        # If the values are simply a series of non-indexed values
        elif output["type"] == "values":
            output_setup_string += 'printf "%s,%s\\n", "Name", "Value" > "' + output["filename"] + '";\n'
            output_setup_string += 'printf "' + '%s,%.1f\\n' * len(output["var_names"]) + '\\n"'
            for variable in output["var_names"]:
                output_setup_string += ', "' + variable + '", ' + variable
            output_setup_string += ' >> "' + output["filename"] + '";\n\n\n'
        else:
            raise ValueError ("The output type should be either 'indexed' or 'value'. " + output["type"] + " was provided instead.")
    # In the case of GLPK output syntax is added at the bottom of the mod file, in the case of AMPL in the runfile
    with open(sim_folder + "mod_file.mod", "a") as mod_file:
        mod_file.write(output_setup_string)
    
    return None

def writePrintfStatementsForAmpl(output_structure, problem, simname):
    output_setup_string = ""
    output_setup_string += "option solver " + problem.solver + ";\n"
    output_setup_string += 'option ampl_include "' + problem.temp_folder + '";\n'
    output_setup_string += "model mod_file.mod; \n"
    output_setup_string += "data sets.dat;\n"
    output_setup_string += 'option ampl_include "' + problem.temp_folder + simname + '\\";\n'
    output_setup_string += "data parameters.dat; \n"
    output_setup_string += "solve; \n\n"
    # Writing the actual output format
    for output in output_structure:
        # If the value is indexed over a set:
        if output["type"] == "indexed":
            output_setup_string += 'printf "%s' + ',%s'*len(output["column_names"]) + '\\n", "Name"'
            for name in output["column_names"]:
                output_setup_string += ', "' + name + '"'
            output_setup_string += ' > "' + output["filename"] + '"; \n'
            output_setup_string += 'printf {i in ' + output["set"] + '} \t '
            output_setup_string += '"%s' + ',%.1f'*len(output["column_names"]) + '\\n", i'
            for variable in output["var_names"]:
                if "setdim" not in output.keys():
                    output_setup_string += ', ' + variable + "[i]"
                else:
                    output_setup_string += ', ' + variable + "[i,j]"
            output_setup_string += ' >> "' + output["filename"] + '" ;\n'
            output_setup_string += '\n'
        # If the values are simply a series of non-indexed values
        elif output["type"] == "values":
            output_setup_string += 'printf "%s,%s\\n", "Name", "Value" > "' + output["filename"] + '";\n'
            output_setup_string += 'printf "' + '%s,%.1f\\n' * len(output["var_names"]) + '\\n"'
            for variable in output["var_names"]:
                output_setup_string += ', "' + variable + '", ' + variable
            output_setup_string += ' >> "' + output["filename"] + '";\n\n\n'
        else:
            raise ValueError ("The output type should be either 'indexed' or 'value'. " + output["type"] + " was provided instead.")
        # In the case of GLPK output syntax is added at the bottom of the mod file, in the case of AMPL in the runfile
    with open(problem.sim_folder + problem.filenames["runfile"], "w") as runfile:
        runfile.write(output_setup_string)
    # Finally we add the "end" at the end of the mod file
    with open(problem.sim_folder + "mod_file.mod", "a") as mod_file:
        mod_file.write("\nend;")
    
    return None



def runCustomPythonCode(main_folder, simulation_data, parameters):
    """
    This function is used to add pieces of Python code that are specific to a given project and not to be considered
    valid for any problem
    """
    if any([filename.split(".")[-1] == "py" for filename in os.listdir(main_folder)]):
        sys.path.append(main_folder)
        for filename in os.listdir(main_folder):
            if filename.split(".")[-1] == "py":
                custom_module = importlib.import_module(filename[:-3])
                parameters = custom_module.main(simulation_data, parameters)
    return parameters


def updateParameters(parameters, problem, simulation_data):
    for parameter_tuple in simulation_data.keys():
        if parameter_tuple[0].upper() == parameter_tuple[0]:  # In this case we have provided already the AMPL parameter value
            parameters = updateAmplParameter(parameters, parameter_tuple, simulation_data[parameter_tuple])
        else:
            parameters = updateRawParameter(parameters, parameter_tuple, simulation_data, problem)
    return parameters

def updateAmplParameter(parameters, name, value):
    """
    This function is used to update a parameter that is given to the parametric/sensitivity analysis
    directly as an AMPL parameter
    """
    if name[1] == "":
        parameters["0"][name[0]] = value
    elif name[2] == "":
        parameters["1"][name[0]][name[1]] = value
    else:
        parameters["2"][name[0]][name[1]][name[2]] = value
    return parameters

def updateRawParameter(parameters, parameter_tuple, simulation_data, problem):
    """
    This function is used to update parameters that are given not as ready AMPL parameters, but as 'raw' parameters
    They need hence to be converted/processed in order to be used
    """
    if parameter_tuple[0] == "InterestRate":
        for unit_name in problem["units"]:
            INTEREST_RATE = simulation_data[parameter_tuple]
            INVESTMENT_COST = referenceOrUpdated(("InvestmentCost", unit_name, ""), simulation_data, problem)
            LIFETIME = referenceOrUpdated(("Lifetime", unit_name, ""), simulation_data, problem)
            parameters["SPECIFIC_INVESTMENT_COST_ANNUALIZED"][unit_name] = calculateAnnualizedInvestmentCost(INVESTMENT_COST, LIFETIME, INTEREST_RATE)
    elif parameter_tuple[0] in ["InvestmentCost", "Lifetime"]:
        if any("InterestRate" in key[0] for key in simulation_data.keys()):
            pass
        else:
            unit_name = parameter_tuple[1]
            INTEREST_RATE = problem.parameters["extra"]["InterestRate"]
            INVESTMENT_COST = referenceOrUpdated(("InvestmentCost", parameter_tuple[1], ""), simulation_data, problem)
            LIFETIME = referenceOrUpdated(("Lifetime", unit_name, ""), simulation_data, problem)
            parameters["SPECIFIC_INVESTMENT_COST_ANNUALIZED"][unit_name] = calculateAnnualizedInvestmentCost(INVESTMENT_COST, LIFETIME, INTEREST_RATE)
    elif parameter_tuple[0] == "MaxPower":
        parameters["2"]["POWER_MAX"][parameter_tuple[1]][parameter_tuple[2]] = simulation_data[parameter_tuple]
    elif parameter_tuple[0] == "ActivationFrequency":
        parameters["3"]["POWER_MAX_REL"][parameter_tuple[1]][parameter_tuple[2]] = setRelativeMaxPower(simulation_data[parameter_tuple], problem.general_parameters["NT"])
    elif parameter_tuple[0] in problem.parameters["extra"].keys():
        pass  # The parameters will be updated in the custom python code
    else:
        raise ValueError("Parameter with name " + " ".join(parameter_tuple) + "is not recognized as raw input parameter. Check if it is valid!")

    return parameters


def setRelativeMaxPower(activation_frequency, NT):
    """
    This function creates a dictionary with this logic:
        0: for all values where the maximum power is 0 (the unit is off / the connection is not active)
        1: for all values where the maximum power is >0 (the unit is on / the connection is active)
    This value is used in conjunction with "POWER_MAX"
    """
    output = pd.DataFrame(0, index = [idx+1 for idx in range(NT)], columns = ["POWER_MAX_REL"])
    output.iloc[::activation_frequency, :] = 1
    output = output["POWER_MAX_REL"].to_dict()
    return output


def updateExtraParameters(parameters, simulation_data, filenames):
    """
    This function is used to update any parameter that is in the "extra" category.
    These parameters are not fed directly to AMPL, but are used to calculate other parameters
    """
    return None


def calculateAnnualizedInvestmentCost(INVESTMENT_COST, LIFETIME, INTEREST_RATE):
    if isinstance(INVESTMENT_COST, float) or isinstance(INVESTMENT_COST, int):
        INVESTMENT_COST = float(INVESTMENT_COST)
        LIFETIME = float(LIFETIME)
        ANNUALIZED_INVESMENT_COST = INVESTMENT_COST/((1+INTEREST_RATE)**LIFETIME-1)*(INTEREST_RATE*(1+INTEREST_RATE)**LIFETIME)
    elif isinstance(INVESTMENT_COST, list):
        ANNUALIZED_INVESMENT_COST = 0
        for idx in range(len(INVESTMENT_COST)):
            ANNUALIZED_INVESMENT_COST = ANNUALIZED_INVESMENT_COST + INVESTMENT_COST[idx]/((1+INTEREST_RATE)**LIFETIME[idx]-1)*(INTEREST_RATE*(1+INTEREST_RATE)**LIFETIME[idx])
    return ANNUALIZED_INVESMENT_COST