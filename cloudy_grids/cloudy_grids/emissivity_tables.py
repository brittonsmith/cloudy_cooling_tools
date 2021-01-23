import h5py
import numpy as np
import re
import copy

from cloudy_grids.utilities import get_grid_indices

floatType = '>f8'
intType = '>i8'

par_names = {'Parameter1': 'log_nH'}

def convert_emissivity_tables(runFile, outputFile):
    """
    Convert ascii emissivity tables to hdf5.

    Parameters
    ----------
    run_file : string
        Path to the input file ending in .run.
    output_file : string
        HDF5 output file name.

    Examples
    --------

    >>> from cloudy_grids import convert_emissivity_tables
    >>> convert_emissivity_tables("emissivity/emissivity.run", "emissivity.h5")

    """

    print ("Converting from %s to %s." % (runFile, outputFile))

    if runFile[-4:] == '.run':
        prefix = runFile[0:-4]
    else:
        print ("Run file needs to end in .run.")
        exit(1)

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
                if values.count(';') == 2 and \
                  values.startswith('(') and values.endswith(')'):
                    fs, fe, fi = [float(v) for v in values[1:-1].split(';')]
                    floatValues = np.arange(fs, fe+fi/2, fi)
                else:
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
    gridData = []
    for q in range(totalRuns):
        mapFile = "%s_run%d.dat" % (prefix, (q+1))
        indices = get_grid_indices(gridDimension,q)
        loadMap(mapFile,gridDimension,indices,gridData)

    ienergy = parameterNames.index("energy")
    energy = parameterValues.pop(ienergy)

    temperature = gridData.pop(0)
    emissivity = gridData.pop(0)

    # Write out hdf5 file.
    output = h5py.File(outputFile,'w')
    
    # Write data.
    dataset = "Emissivity"
    output.create_dataset(dataset, data=emissivity,dtype=floatType)
    output[dataset].attrs['log_T'] = \
      np.log10(temperature, dtype=floatType)
    output[dataset].attrs['log_E'] = \
      np.log10(energy, dtype=floatType)

    # Write loop parameter values.
    for q,values in enumerate(parameterValues):
        name = "Parameter%d" % (q+1)
        if name in par_names:
            name = par_names[name]
        output[dataset].attrs[name] = np.array(values, dtype=floatType)

    output.close()

def loadMap(mapFile,gridDimension,indices,gridData):
    "Read individual cooling map ascii file and fill data arrays."

    f = open(mapFile,'r')
    lines = f.readlines()
    f.close()

    t = []
    emissivity = []

    for line in lines:
        line.strip()
        if not line.startswith("#"):
            onLine = line.split()
            t.append(float(onLine.pop(0)))
            emissivity.append([float(val) for val in onLine])

    emissivity = np.squeeze(emissivity)
    
    if len(gridData) == 0:
        myDims = copy.deepcopy(gridDimension)
        myDims.extend(emissivity.shape)
        gridData.append(np.array(t))
        gridData.append(np.zeros(shape=myDims))

    gridData[-1][tuple(indices)][:] = emissivity
