import h5py
import numpy as np
import re
import copy

from cloudy_grids.utilities import get_grid_indices

floatType = '>f8'
intType = '>i8'

field_dict = {"hden": "log_nH",
              "log_T": "log_T"}

def convert_line_tables(runFile,outputFile):
    """
    Convert ascii line emissivity tables to hdf5.

    Parameters
    ----------
    run_file : string
        Path to the input file ending in .run.
    output_file : string
        HDF5 output file name.

    Examples
    --------

    >>> from cloudy_grids import convert_emissivity_tables
    >>> convert_line_tables("line/line.run", "line.h5")

    """

    print ("Converting %s to %s." % (runFile,outputFile))

    if runFile[-4:] == '.run':
        prefix = runFile[0:-4]
    else:
        raise RuntimeError("Run file needs to end in .run.")

    f = open(runFile,'r')
    lines = f.readlines()
    f.close()

    # Values of loop parameters.
    parameterValues = []
    parameterNames = []

    getParameterValues = False
    getRunValues = False

    re_parValue = re.compile('^\# Loop commands and values:')
    re_runValue = re.compile('^\#run')

    totalRuns = 0

    for q,line in enumerate(lines):
        line = line.strip()
        if getParameterValues:
            if line == '#':
                getParameterValues = False
            else:
                (par,values) = line.split(': ')
                floatValues = [float(val) for val in values.split()]
                parameterValues.append(floatValues)
                parameterNames.append(par[2:])
        elif getRunValues:
            totalRuns = len(lines) - q
            break
        else:
            if (re_parValue.match(line) is not None):
                getParameterValues = True
            elif (re_runValue.match(line) is not None):
                getRunValues = True

    # Check file line number against product of parameter numbers.
    gridDimension = [len(q) for q in parameterValues]
    if totalRuns != np.prod(gridDimension):
        raise RuntimeError(
            "Error: total runs (%d) in run file not equal to product of parameters(%d)." %
            (totalRuns, np.prod(gridDimension)))

    # Read in data files.
    gridData = {}
    for q in range(totalRuns):
        mapFile = "%s_run%d.dat" % (prefix,(q+1))
        indices = get_grid_indices(gridDimension,q)
        loadMap(mapFile,gridDimension,indices,gridData, parameterValues, parameterNames)

    # Write out hdf5 file.
    output = h5py.File(outputFile,'w')
    
    # Write data.
    for field in gridData:
        group = output.create_group(field)
        dataset = group.create_dataset("emissivity", data=gridData[field], dtype=floatType)
        dataset.attrs["units"] = "erg * s**(-1) * cm**(3)"

        # Write loop parameter values.
        for q,values in enumerate(parameterValues):
            values = np.array(values,dtype=float)
            name = field_dict[parameterNames[q]]
            dataset = group.create_dataset(name,data=values,dtype=floatType)
            dataset.attrs["units"] = ""

    output.close()

def loadMap(mapFile,gridDimension,indices,gridData, parameterValues, parameterNames):
    "Read individual cooling map ascii file and fill data arrays."

    f = open(mapFile,'r')
    lines = f.readlines()
    f.close()

    data = []
    fields = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line.startswith('#'):
            if not fields:
                fields = lines[i-1].split()[1:]
            data.append(line.split())

    data = np.rollaxis(np.array(data, dtype=np.float64), 1)

    if not gridData:
        myDims = copy.deepcopy(gridDimension)
        myDims.append(data.shape[1])

        for field in fields:
            gridData[field] = np.zeros(shape=myDims)
        parameterNames.append("log_T")
        parameterValues.append(data[0])

    for i, field in enumerate(fields):
        gridData[field][tuple(indices)][:] = data[i+1]
