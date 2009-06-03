import h5py
import numpy as na
import re
import copy

floatType = '>f8'
intType = '>i8'

def cloudyGrid_ascii2hdf5(runFile,outputFile):
    "Convert Cloudy cooling ascii data into hdf5."

    print "Converting %s to %s." % (runFile,outputFile)

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
        mapFile = "%s_run%d.dat" % (prefix,(q+1))
        indices = get_grid_indices(gridDimension,q)
        loadMap(mapFile,gridDimension,indices,gridData)

    # Write out hdf5 file.
    output = h5py.File(outputFile,'w')

    # Write data.
    names = ["Temperature","Heating","Cooling","MMW"]
    for q in range(len(gridData)):
        dataset = output.create_dataset(names[q],data=gridData[q],dtype=floatType)
        dataset.attrs["Dimension"] = na.array(gridData[q].shape,dtype=intType)
        dataset.attrs["Rank"] = na.array(len(gridData[q].shape),dtype=intType)

    # Write loop parameter values.
    for q,values in enumerate(parameterValues):
        values = na.array(values,dtype=float)
        name = "Parameter%d" % (q+1)
        dataset = output.create_dataset(name,data=values,dtype=floatType)
        dataset.attrs["Dimension"] = na.array(values.shape,dtype=intType)
        dataset.attrs["Name"] = parameterNames[q]

    output.close()

def loadMap(mapFile,gridDimension,indices,gridData):
    "Read individual cooling map ascii file and fill data arrays."

    f = open(mapFile,'r')
    lines = f.readlines()
    f.close()

    t = []
    h = []
    c = []
    m = []

    for line in lines:
        line.strip()
        if line[0] != '#':
            onLine = line.split()
            t.append(float(onLine[0]))
            h.append(float(onLine[1]))
            c.append(float(onLine[2]))
            m.append(float(onLine[3]))

    if len(gridData) == 0:
        myDims = copy.deepcopy(gridDimension)
        myDims.append(len(t))
        gridData.append(na.array(t))
        gridData.append(na.zeros(shape=myDims))
        gridData.append(na.zeros(shape=myDims))
        gridData.append(na.zeros(shape=myDims))

    gridData[1][tuple(indices)][:] = h
    gridData[2][tuple(indices)][:] = c
    gridData[3][tuple(indices)][:] = m

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
