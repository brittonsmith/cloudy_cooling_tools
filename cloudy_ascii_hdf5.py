import h5py
import numpy as na
import re
import copy

floatType = '>f4'
intType = '>i4'

def cloudyGrid_ascii2hdf5(runFile, outputFile, species):
    "Convert Cloudy ion fraction ascii data into hdf5."

    print "Converting %s from %s to %s." % (species, runFile, outputFile)

    if runFile[-4:] == '.run':
        prefix = runFile[0:-4]
    else:
        print "Run file needs to end in .run."
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
                floatValues = map(float,values.split())
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
    if totalRuns != reduce((lambda x,y: x*y),gridDimension):
        print "Error: total runs (%d) in run file not equal to product of parameters(%d)." % \
        (totalRuns,reduce((lambda x,y: x*y),gridDimension))
        exit(1)

    # Read in data files.
    gridData = []
    for q in range(totalRuns):
        mapFile = "%s_run%d_%s.dat" % (prefix, (q+1), species)
        indices = get_grid_indices(gridDimension,q)
        loadMap(mapFile,gridDimension,indices,gridData)

    temperature = gridData.pop(0)
    ion_data = gridData.pop(0)
    ion_data = na.rollaxis(ion_data, -1)

    # Write out hdf5 file.
    output = h5py.File(outputFile,'a')

    # Write data.
    output.create_dataset(species, data=ion_data,dtype=floatType)
    output[species].attrs['Temperature'] = na.array(temperature, dtype=floatType)

    # Write loop parameter values.
    for q,values in enumerate(parameterValues):
        name = "Parameter%d" % (q+1)
        output[species].attrs[name] = na.array(values, dtype=floatType)

    output.close()

def loadMap(mapFile,gridDimension,indices,gridData):
    "Read individual cooling map ascii file and fill data arrays."

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
            ion_fraction.append(map(float, onLine))

    ion_fraction = na.array(ion_fraction)

    if len(gridData) == 0:
        myDims = copy.deepcopy(gridDimension)
        myDims.extend(ion_fraction.shape)
        gridData.append(na.array(t))
        gridData.append(na.zeros(shape=myDims))

    gridData[1][tuple(indices)][:] = ion_fraction

def get_grid_indices(dims,index):
    "Return indices with shape of dims corresponding to scalar index."
    indices = []
    dims.reverse()
    for dim in dims:
        indices.append(index % dim)
        index -= indices[-1]
        index /= dim

    dims.reverse()
    indices.reverse()
    return indices
