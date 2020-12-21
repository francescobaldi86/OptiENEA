# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 14:11:52 2020

@author: franc
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def parametricSimulationMatrix(problem, simulation_matrix):
    """
    Reads the parametric input data and uses it to
    :param problem:
    :param simulation_matrix:
    :param base_idf:
    :return:
    """

    list_of_parametric_fields = {"0": {}, "1": {}}  # Create a list of all parameters that are considered as parametric
    for level, parameter_list in problem.parametric.items():
        for param_name, param_data in parameter_list.items():
            list_of_parametric_fields[level][convertFieldNames(param_name, mode = "string2tuple")] = readParametricValues(problem.parametric[level][param_name])

    # Assign field values to the dataframe
    output = pd.DataFrame(columns=list(list_of_parametric_fields["0"]) + list(list_of_parametric_fields["1"]))
    for par0_name, par0_values in list_of_parametric_fields["0"].items():
        counter0 = 0
        for id_par0 in range(len(par0_values)):
            counter0 += 1
            data, _ = nestedIterations(list_of_parametric_fields["1"], "PAR-" + convertFieldNames(par0_name, mode = "tuple2string").replace(":", "_") + "-" + str(counter0) + ".", {})
            dataframe = pd.DataFrame.from_dict(data, orient="index", columns=list_of_parametric_fields["1"].keys())
            for par0_name__, par0_values__ in list_of_parametric_fields["0"].items():
                if par0_name__ == par0_name:
                    dataframe[par0_name__] = par0_values[id_par0]
                else:
                    dataframe[par0_name__] = simulation_matrix.loc["REF", par0_name__]  # If this is not the "selected" item,
            output = output.append(dataframe)
    output = assignOtherFields(simulation_matrix, output)
    output = pd.concat((simulation_matrix, output))

    return output.drop_duplicates()


def convertFieldNames(name, mode = "tuple2string"):
    if mode == "string2tuple":
        temp = name.split(sep=":")
        if len(temp) == 1:
            return (temp[0], "", "")
        elif len(temp) == 2:
            return (temp[0], temp[1], "")
        elif len(temp) == 3:
            return (temp[0], temp[1], temp[2])
        else:
            raise Exception("The parameter for parametric analysis " + name + " has too many levels. Max 2 are allowed")
    elif mode == "tuple2string":
        return ":".join(name)
    else:
        raise Exception("The conversion mode " + mode + " is not accepted")


def readParametricValues(values):
    if isinstance(values, list):
        return values
    elif isinstance(values, tuple):
        return [values[0] + (values[1] - values[0]) * x / values[2] for x in range(values[2] + 1)]


def parametricResultsAnalysis(simulation_results, problem):
    """
    This script analyses the results of the parametric simulations
    1 - Gets the net effect of each parameter
    2 - Saves one plot for each level - 0 parameter, with different lines for each level of 1-D parameters
    """
    plt.close('all')
    outputs2plot = ["yearly HVAC (total) [TOE]", "summer HVAC (Electricity) [TOE]", "winter HVAC (Gas) [TOE]"]
    colors = ["Black", "Blue", "Red", "Green", "Yellow"]
    # list_of_parameters = problem["parametric"][0].update(problem["parametric"][1])
    # First, we look at plotting the "0-level" parameters, and we plot the results as normal line plot
    for parameter, values in problem.parametric["0"].items():
        plt.figure()
        for idx, output in enumerate(outputs2plot):
            data = simulation_results.loc[simulation_results.index.str.contains(parameter), :]
            if idx == 0:
                ax = data.plot.scatter(
                    x = parameter,
                    y = outputs2plot[0],
                    color = colors[0],
                    label = str(outputs2plot[0]))
            else:
                data.plot.scatter(
                    x=parameter,
                    y=outputs2plot[idx],
                    color=colors[idx],
                    label=str(outputs2plot[idx]),
                    ax=ax)
            if data[parameter].dtype == "float64":
                z = np.polyfit(data[parameter], data[outputs2plot[idx]].astype(float), 1)
                p = np.poly1d(z)
                ax.plot(data[parameter], p(data[parameter]), color = colors[idx])
        ax.legend(loc = "lower left")
        plt.ylabel("Difference in energy demand [ToE]")
        fig = ax.get_figure()
        fig.savefig(problem["filenames"]["OUTPUT"] + "Figures\\xyplot_" + parameter.replace(":", "_") + ".png")
    return None


def nestedIterations(dict_of_values, sim_name, data={}, values=[], names=[], counter=0):
    if len(dict_of_values) > 0:
        item_to_remove = list(dict_of_values.keys())[0]
        names = names + [item_to_remove]
        for value in dict_of_values[item_to_remove]:
            data, counter = nestedIterations({k: v for k, v in dict_of_values.items() if k != item_to_remove}, sim_name,
                                             data, values + [value], names, counter)
    else:
        counter += 1
        data.update({sim_name + str(counter): values})
    return data, counter


def assignOtherFields(reference_simulation, new_data):
    for column in reference_simulation.columns:
        if column not in new_data.columns:
            new_data[column] = reference_simulation[column]["REF"]
    return new_data
