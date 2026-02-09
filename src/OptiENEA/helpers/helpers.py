import pandas as pd
import os
from collections import defaultdict
import stat, shutil, time
REQUIRED_STRUCTURE = {
    'folders': ['Input', ],
    'files': ['Input/units.yml', 'Input/general.yml']
}

def read_config_file(filename: str, data_structure = {}) -> dict:
    """
      This function reads the input text file and parses it into the required
      input to the problem, in the form of a multi-level dictionary
    """
    with open(filename) as file:
        field_L1 = None
        for line in file.readlines():
            # The "#" is the signed used for comments
            if line[0] == "#":
                continue
            elif line[0] == "%":  # The "%" sign is used for identifying the main key in the dictionaire
                field_L1 = line.replace("%", "").replace("\n", "").strip()
                if field_L1 not in data_structure.keys():
                    data_structure[field_L1] = {}
            elif line == "\n":
                pass
            else:
                if "#" in line:
                    line = line.split(sep="#")[0].strip()
                fields = line.split(sep=";")
                for id_field, field in enumerate(fields):
                    fields[id_field] = field.replace("\n", "").strip()
                if field_L1 is not None:
                    data_structure[field_L1] = save_info_recursively(data_structure[field_L1], fields)
                else:
                    data_structure = save_info_recursively(data_structure, fields)
    return data_structure

def safe_to_list(input: int | str | float | list):
    # Reads the input. If it is a list it returns it as is, otherwise it makes it a list
    return input if isinstance(input, list) else [input]


def save_info_recursively(dictionary, fields):
    if len(fields) < 2:
        return dictionary
    if len(fields) == 2:
        dictionary.update({fields[0]: eval(fields[1])})  # Write output on current level
    else:
        if fields[0] not in dictionary.keys():
            dictionary[fields[0]] = {}
        low_level_field = fields.pop(0)
        dictionary[low_level_field] = save_info_recursively(dictionary[low_level_field], fields)
    return dictionary

def check_value_type(value):
    """
    This function checks the input string, and if needed converts it to the appropriate format (float or string)
    """
    try:
        return float(value)  # Checking if the value is a float
    except:
        if value[0] == '"' and value[-1] == '"':  # The value is number that should be read as a string (e.g. "0")
            return value[1:-1]
        elif value == "None":  # If the value is "None", we have to translate it to a "real" none
            return None
        else:  # If it is neither a float nor a list, then it's a string
            return value

def add_to_set(set, field):
    """
    This function helps reading a field that can be either a single value/string or a list
    And adds its contents to a set
    """
    if isinstance(field, list):
        for item in field:
            set.add(item)
    else:
        set.add(field)
    return set

def reference_or_updated(tuple_name, simulation_data, problem, type):
    """
    This function is used to select what value to use.
    If the required parameter is available in the "simulation data" columns, then the most updated
    value is used
    Otherwise, the "reference" one is used instead
    """
    if tuple_name in simulation_data.keys():
        return simulation_data[tuple_name]
    else:
        if type == "unit":
            return problem.units[tuple_name[1]][tuple_name[0]]
        elif type == "extra":
            return problem.parameters["extra"][tuple_name][0]
        
def read_data_file(input: str, unit_name: str, layer_name: str, problem_folder: str = None) -> pd.DataFrame: 
    """
    Reads the file_input string. If it is "file" creates the input file name
    based on unit_name and project folder. Else, it expects the file_input
    to be the full location of the file name
    :param: file_input      File input. Can be either 'file' or a full address
    :param: unit_name       The name of the entity we are reading data of. 
    :param: problem_folder  The location of the project where we should read the file
    """
    if input == 'file':
        if problem_folder:
            return pd.read_csv(
                f'{problem_folder}\\data\\{unit_name}.csv', 
                index_col=0, 
                header=0)[layer_name]
        else:
            raise ValueError(f'If the input value for the data is "file", then a real problem folder needs to be provided')
    else:
        if input[-4:] != '.csv':
            raise TypeError(f"The file provided should have a .csv format. {input} was provided instead")
        try:
            return pd.read_csv(input, index_col=0, header=0)[layer_name]
        except:
            FileNotFoundError(f'File at location {input} was not found')

def attribute_name_converter(input: str) -> str:
    # This function is used to convert "extensive" attribute names used in the YAML configuration file to 
    # the pure snake-case format used for unit attributes
    return input.replace(" ", "_").replace("-", "_").lower()

class ProjectStructureError(Exception):
    """Custom exception for project structure errors."""
    pass

def validate_project_structure(project_path, required=REQUIRED_STRUCTURE):
    missing_items = []

    # Check required folders
    for folder in required.get('folders', []):
        folder_path = os.path.join(project_path, folder)
        if not os.path.isdir(folder_path):
            missing_items.append(f"Missing folder: {folder}")

    # Check required files
    for file in required.get('files', []):
        [folder_name, file_name] = file.split('/')
        file_path = os.path.join(project_path, folder_name, file_name)
        if not os.path.isfile(file_path):
            missing_items.append(f"Missing file: {file}")

    if missing_items:
        raise ProjectStructureError(
            f"Project at '{project_path}' is missing the following:\n" + "\n".join(missing_items)
        )
    
def dict_tree():
    return defaultdict(dict_tree)

def to_dict(d):
    if isinstance(d, defaultdict):
        return {k: to_dict(v) for k, v in d.items()}
    return d

def handle_remove_readonly(func, path, exc_info):
    """Clear the readonly bit and reattempt the removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def safe_rmtree(path, retries=3, delay=0.1):
    for i in range(retries):
        try:
            shutil.rmtree(path, onerror=handle_remove_readonly)
            return
        except PermissionError:
            time.sleep(delay)
    # if it still fails, raise
    shutil.rmtree(path, onerror=handle_remove_readonly)

def get_from_path(d, path):
    for key in path:
        d = d[key]
    return d

def set_in_path(d, path, value):
    current = d
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    return d

def key_dotted_to_tuple(dotted_key):
    return tuple(dotted_key.split(':'))

def key_tuple_to_dotted(tuple_key):
    return ':'.join(tuple_key)