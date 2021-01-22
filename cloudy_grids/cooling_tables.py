import h5py
import numpy as np
import re
import copy

from cloudy_grids.utilities import \
     get_grid_indices, \
     get_attributes, \
     write_attributes

floatType = '>f8'
intType = '>i8'

def convert_cooling_tables(runFile,outputFile):
    """
    Convert ascii cooling tables to hdf5.

    Parameters
    ----------
    run_file : string
        Path to the input file ending in .run.
    output_file : string
        HDF5 output file name.

    Examples
    --------

    >>> from cloudy_grids import convert_cooling_tables
    >>> convert_cooling_tables("cooling/cooling.run", "cooling.h5")

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
            (totalRuns, np.prog(gridDimension)))

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
        dataset.attrs["Dimension"] = np.array(gridData[q].shape,dtype=intType)
        dataset.attrs["Rank"] = np.array(len(gridData[q].shape),dtype=intType)

    # Write loop parameter values.
    for q,values in enumerate(parameterValues):
        values = np.array(values,dtype=float)
        name = "Parameter%d" % (q+1)
        dataset = output.create_dataset(name,data=values,dtype=floatType)
        dataset.attrs["Dimension"] = np.array(values.shape,dtype=intType)
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
        gridData.append(np.array(t))
        gridData.append(np.zeros(shape=myDims))
        gridData.append(np.zeros(shape=myDims))
        gridData.append(np.zeros(shape=myDims))

    gridData[1][tuple(indices)][:] = h
    gridData[2][tuple(indices)][:] = c
    gridData[3][tuple(indices)][:] = m

def graft_cooling_tables(input_lt,input_ht,outputFile,
                         data_fields=['Heating','Cooling','MMW'],
                         extra_field="metal free electron fraction"):
    """
    Attach low temperature and high temperature cooling grids.  The high 
    temperature grid will have one less dimension than the low temperature 
    grid, so duplicate data will be made in one dimension.  Fixed electron 
    fractions are used to make the low temperature data, but not the high 
    temperature data, as this causes errors in Cloudy.
    """

    # Open low temperature data and find dimension of the field not in the 
    # high temperature data.

    extra_dim = -1
    data_lt = {}

    input = h5py.File(input_lt,'r')
    print ("Reading file: %s." % input_lt)
    for dataset in input.listnames():
        data_lt[dataset] = input[dataset].value
    attributes_lt = get_attributes(input)
    input.close()

    for dim in range(len(data_lt[data_fields[0]].shape)-1):
        name = "Parameter%d" % (dim+1)
        if attributes_lt[name]["Name"]['value'] == extra_field:
            extra_dim = dim
    if extra_dim < 0:
        print ("Field, %s, not found in %s." % (extra_field,input_lt))
        return None

    # Open high temperature data and create duplicate data in 
    # electron fraction dimension.

    data_ht = {}
    input = h5py.File(input_ht,'r')
    print ("Reading file: %s." % input_ht)
    for dataset in input.listnames():
        data_ht[dataset] = input[dataset].value
    attributes_ht = get_attributes(input)
    input.close()

    print ("Combining datasets.")

    data_ht_new = {}
    for dataset in data_fields:
        data_ht_new[dataset] = add_grid_dimension(data_ht[dataset],extra_dim,
                                                  (data_lt[dataset].shape)[extra_dim])

    # Remove redundant temperature point.
    redundant_point = False
    if data_lt['Temperature'][-1] == data_ht['Temperature'][0]:
        redundant_point = True

    if redundant_point:
        data_lt['Temperature'] = np.concatenate((data_lt['Temperature'],data_ht['Temperature'][1:]))
    else:
        data_lt['Temperature'] = np.concatenate((data_lt['Temperature'],data_ht['Temperature']))

    attributes_lt['Temperature']["Dimension"]['value'][0] = data_lt['Temperature'].size
    del data_ht

    # Change dimension attribute.
    for dataset in data_fields:
        attributes_lt[dataset]["Dimension"]['value'][-1] = data_lt['Temperature'].size

    # Concatenate datasets.
    for dataset in data_fields:
        if redundant_point:
            data_ht_copy = data_ht_new[dataset]
            data_ht_copy = np.rollaxis(data_ht_copy,(len(data_ht_copy.shape)-1),0)
            data_ht_copy = data_ht_copy[1:]
            data_ht_copy = np.rollaxis(data_ht_copy,0,len(data_ht_copy.shape))
        else:
            data_ht_copy = data_ht_new[dataset]

        data_lt[dataset] = np.concatenate((data_lt[dataset],data_ht_copy),axis=-1)

    # Write new dataset.
    print ("Writing file: %s." % outputFile)
    output = h5py.File(outputFile,'w')
    for dataset in data_lt.keys():
        output.create_dataset(dataset,data=data_lt[dataset])
    write_attributes(output,attributes_lt)
    output.close()

def add_grid_dimension(grid,dimension,size):
    "Add a dimension to the grid with duplicate data."

    oldShape = grid.shape
    newShape = list(oldShape)

    newShape.reverse()
    newShape.append(size)
    newShape.reverse()

    newGrid = np.zeros(newShape,dtype=grid.dtype)
    newGrid[:] = grid

    if dimension > 0:
        newGrid = np.rollaxis(newGrid,0,dimension+1)

    return newGrid

def zero_dataset(input_file,data_fields=['Heating','MMW'],output_file=None):
    "Set all values in a dataset to zero."

    if output_file is None:
        output_file = input_file

    data = {}

    print ("Reading file: %s." % input_file)
    input = h5py.File(input_file,'r')
    for dataset in input.keys():
        data[dataset] = input[dataset].value
    attributes = get_attributes(input)
    input.close()

    for dataset in data_fields:
        print ("Setting %s to zero." % dataset)
        data[dataset][:] = 0.0


    print ("Writing file: %s." % output_file)
    output = h5py.File(output_file,'w')
    for dataset in data.keys():
        output.create_dataset(dataset,data=data[dataset])
    write_attributes(output,attributes)
    output.close()
