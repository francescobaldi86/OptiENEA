def simulationHandler():
    """
    This function handles the simulations
    """




def updateInput(project_folder, filename, tuple):
    output = ""
    with open(project_folder + "\\" + filename, "r") as datafile:
        parameter_name = tuple[0]
        parameter_slice = tuple[1]
        parameter_value = tuple[2]
        read = False
        for line in datafile:
            if parameter_name in line:
                read = True
            if read:
                if len(line.split()) == 0:
                    continue
                if line.split()[0] == parameter_slice:
                    temp = ["\t"]
                    counter = 0
                    for item in line.split():
                        counter += 1
                        if item == "#":
                            temp.append(" ".join(line.split()[counter-1:len(line.split())]))
                            break
                        try:
                            old_value = float(item)
                            temp.append('{:f}'.format(parameter_value))
                        except:
                            temp.append(item)
                    line = " ".join(temp) + "\n"
            output = output + line
    with open(project_folder + "\\" + filename, "w") as datafile:
        print(output, file=datafile)
    return output