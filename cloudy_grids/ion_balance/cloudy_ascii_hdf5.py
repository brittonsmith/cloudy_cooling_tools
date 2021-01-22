import h5py
import numpy as np
import re
import copy

from cloudy_grids.utilities import get_grid_indices

floatType = '>f4'
intType = '>i4'

def _ion_balance_convert(runFile, outputFile, species):
    "Convert Cloudy ion fraction ascii data into hdf5."

    print ("Converting %s from %s to %s." % (species, runFile, outputFile))

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
        print ("Error: total runs (%d) in run file not equal to product of parameters(%d)." % \
        (totalRuns,reduce((lambda x,y: x*y),gridDimension)))
        exit(1)

    # Read in data files.
    gridData = []
    for q in range(totalRuns):
        mapFile = "%s_run%d_%s.dat" % (prefix, (q+1), species)
        indices = get_grid_indices(gridDimension,q)
        loadMap(mapFile,gridDimension,indices,gridData)

    temperature = gridData.pop(0)
    ion_data = gridData.pop(0)
    ion_data = np.rollaxis(ion_data, -1)

    # Write out hdf5 file.
    output = h5py.File(outputFile,'a')

    # Write data.
    output.create_dataset(species, data=ion_data,dtype=floatType)
    output[species].attrs['Temperature'] = np.array(temperature, dtype=floatType)

    # Write loop parameter values.
    for q,values in enumerate(parameterValues):
        name = "Parameter%d" % (q+1)
        output[species].attrs[name] = np.array(values, dtype=floatType)

    output.close()

def loadMap(mapFile,gridDimension,indices,gridData):
    "Read individual cloudy map ascii file and fill data arrays."

    f = open(mapFile,'r')
    lines = f.readlines()
    f.close()

    t = []
    ion_fraction = []

    for line in lines:
        line.strip()
        if line[0] != '#':
            onLine = line.split()
            t.append(float(onLine.pop(0)))
            ion_fraction.append([float(val) for val in onLine])

    ion_fraction = np.array(ion_fraction)

    if len(gridData) == 0:
        myDims = copy.deepcopy(gridDimension)
        myDims.extend(ion_fraction.shape)
        gridData.append(np.array(t))
        gridData.append(np.zeros(shape=myDims))

    gridData[1][tuple(indices)][:] = ion_fraction

def convert_ion_balance_tables(run_file, output_file, elements):
    """
    Convert ascii ion balance tables to hdf5.

    Parameters
    ----------
    run_file : string
        Path to the input file ending in .run.
    output_file : string
        HDF5 output file name.
    elements : list
        List of elements to be converted.

    Examples
    --------

    >>> from cloudy_grids import convert_ion_balance_tables
    >>> convert_ion_balance_tables(
    ...     "ion_balance/ion_balance.run", "ion_balance.h5", ["C", "O"])

    """

    for element in elements:
        _ion_balance_convert(run_file, output_file, element)
