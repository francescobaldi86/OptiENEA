import pandas as pd

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
        
def read_data_file(input: str, entity_name: str, project_folder: str) -> pd.DataFrame: 
    """
    Reads the file_input string. If it is "file" creates the input file name
    based on unit_name and project folder. Else, it expects the file_input
    to be the full location of the file name
    :param: file_input      File input. Can be either 'file' or a full address
    :param: unit_name       The name of the entity we are reading data of. 
    :param: project_folder  The location of the project where we should read the file
    """
    if isinstance(input, list):
        return input
    elif isinstance(input, str):
        if input == 'file':
            return pd.read_csv(
                f'{project_folder}\\data\\{entity_name}.csv', 
                index_col=0, 
                header=0)
        else:
            try:
                return pd.read_csv(input, index_col=0, header=0)
            except:
                FileNotFoundError(f'File at location {input} was not found')
    else:
        return TypeError(f'The input provided for entity {entity_name} is {input} and \
                         it appears not valid. Please check it! It should be either \
                         a list of values, or a string')
            