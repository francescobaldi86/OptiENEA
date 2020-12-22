# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 10:33:51 2019

@author: Francesco Baldi

This is the main script of the "OptiENEA" toolbox for the linear optimization of energy systems

"""

import os
import importlib
from lib.Functions.simulationManager import simulationManager
from lib.Classes.problem import Problem

from winsound import Beep



def main():
    problem = Problem("AmmoniaProblem")
    problem.set_problem_folders("user")
    problem.parse_general_input_file()
    problem.parse_problem_units()
    problem.parse_problem_sets()
    problem.parse_problem_parameters()
    simulationManager(problem)
    Beep(frequency = 500, duration = 500)

    return None








    problem["filenames"]["output_folder"] = folder_name + problem[
        "project_name"] + "_" + datetime.now().strftime("%Y-%m-%d %Hh%M") + "\\"
    if not os.path.isdir(problem["filenames"]["output_folder"]):
        os.mkdir(problem["filenames"]["output_folder"])
    problem["sets"] = {"0": dict(), "1": dict()}
    problem["parameters"] = {"0": dict(), "1": dict(), "2": dict(), "3": dict(), "extra": dict()}
    return problem





if __name__ == '__main__':
    main()
