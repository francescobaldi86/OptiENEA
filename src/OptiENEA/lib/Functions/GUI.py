# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 10:33:51 2019

@author: Francesco Baldi

This file is used to create a simple GUI to manage the simulations
"""

import tkinter as tk
from tkinter import filedialog

def get_problem_directories():
    top = tk.Tk()
    top.withdraw()
    top.directory_problem = filedialog.askdirectory(
        title = "Provide problem directory",
        initialdir="C:\\Users\\FrancescoBaldi\\Dropbox\\Condivisa Coraddu-Collu-Baldi\\Ottimizzatore\\GLPK\\AmmoniaProblem")
    top.directory_temp = filedialog.askdirectory(
        title = "Provide temporary directory",
        initialdir="C:\\Users\\FrancescoBaldi\\Documents\\ENEA\\AmmoniaProblem")
    top.destroy()
    return top.directory_problem, top.directory_temp

def get_problem_general_file_folder():
    top = tk.Tk()
    top.directory = filedialog.askdirectory()
    top.destroy()
    return top.directory