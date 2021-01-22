import h5py
import numpy as na
import re
import copy

floatType = '>f8'
intType = '>i8'

par_names = {'Parameter1': 'log_nH'}

def cloudyGrid_ascii2hdf5(runFile, outputFile):
    "Convert Cloudy ion fraction ascii data into hdf5."

    print "Converting from %s to %s." % (runFile, outputFile)

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
        mapFile = "%s_run%d.dat" % (prefix, (q+1))
        indices = get_grid_indices(gridDimension,q)
        loadMap(mapFile,gridDimension,indices,gridData)

    temperature = gridData.pop(0)
    energy = gridData.pop(0)
    emissivity = gridData.pop(0)

    # Write out hdf5 file.
    output = h5py.File(outputFile,'w')
    
    # Write data.
    dataset = "Emissivity"
    output.create_dataset(dataset, data=emissivity,dtype=floatType)
    output[dataset].attrs['log_T'] = \
      na.log10(temperature, dtype=floatType)
    output[dataset].attrs['log_E'] = \
      na.log10(energy, dtype=floatType)

    # Write loop parameter values.
    for q,values in enumerate(parameterValues):
        name = "Parameter%d" % (q+1)
        if name in par_names:
            name = par_names[name]
        output[dataset].attrs[name] = na.array(values, dtype=floatType)

    output.close()

def loadMap(mapFile,gridDimension,indices,gridData):
    "Read individual cooling map ascii file and fill data arrays."

    f = open(mapFile,'r')
    lines = f.readlines()
    f.close()

    t = []
    energy = []
    emissivity = []

    for line in lines:
        line.strip()
        if line.startswith("#E [keV]"):
            online = line.split()
            energy = map(float, online[2:])
        elif not line.startswith("#"):
            onLine = line.split()
            t.append(float(onLine.pop(0)))
            emissivity.append(map(float, onLine))

    emissivity = na.array(emissivity)
    
    if len(gridData) == 0:
        myDims = copy.deepcopy(gridDimension)
        myDims.extend(emissivity.shape)
        gridData.append(na.array(t))
        gridData.append(na.array(energy))
        gridData.append(na.zeros(shape=myDims))

    gridData[2][tuple(indices)][:] = emissivity

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
