"""
Britton Smith <brittonsmith@gmail.com>

Routine for grafting together cooling datasets of different dimension.
"""

import h5py
import numpy as na
from hdf5_attributes import *

def graft_grid(input_lt,input_ht,outputFile,
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
    print "Reading file: %s." % input_lt
    for dataset in input.listnames():
        data_lt[dataset] = input[dataset].value
    attributes_lt = get_attributes(input)
    input.close()

    for dim in range(len(data_lt[data_fields[0]].shape)-1):
        name = "Parameter%d" % (dim+1)
        if attributes_lt[name]["Name"]['value'] == extra_field:
            extra_dim = dim
    if extra_dim < 0:
        print "Field, %s, not found in %s." % (extra_field,input_lt)
        return None

    # Open high temperature data and create duplicate data in 
    # electron fraction dimension.

    data_ht = {}
    input = h5py.File(input_ht,'r')
    print "Reading file: %s." % input_ht
    for dataset in input.listnames():
        data_ht[dataset] = input[dataset].value
    attributes_ht = get_attributes(input)
    input.close()

    print "Combining datasets."

    data_ht_new = {}
    for dataset in data_fields:
        data_ht_new[dataset] = _add_grid_dimension(data_ht[dataset],extra_dim,
                                                  (data_lt[dataset].shape)[extra_dim])

    # Remove redundant temperature point.
    redundant_point = False
    if data_lt['Temperature'][-1] == data_ht['Temperature'][0]:
        redundant_point = True

    if redundant_point:
        data_lt['Temperature'] = na.concatenate((data_lt['Temperature'],data_ht['Temperature'][1:]))
    else:
        data_lt['Temperature'] = na.concatenate((data_lt['Temperature'],data_ht['Temperature']))

    attributes_lt['Temperature']["Dimension"]['value'][0] = data_lt['Temperature'].size
    del data_ht

    # Change dimension attribute.
    for dataset in data_fields:
        attributes_lt[dataset]["Dimension"]['value'][-1] = data_lt['Temperature'].size

    # Concatenate datasets.
    for dataset in data_fields:
        if redundant_point:
            data_ht_copy = data_ht_new[dataset]
            data_ht_copy = na.rollaxis(data_ht_copy,(len(data_ht_copy.shape)-1),0)
            data_ht_copy = data_ht_copy[1:]
            data_ht_copy = na.rollaxis(data_ht_copy,0,len(data_ht_copy.shape))
        else:
            data_ht_copy = data_ht_new[dataset]

        data_lt[dataset] = na.concatenate((data_lt[dataset],data_ht_copy),axis=-1)

    # Write new dataset.
    print "Writing file: %s." % outputFile
    output = h5py.File(outputFile,'w')
    for dataset in data_lt.keys():
        output.create_dataset(dataset,data=data_lt[dataset])
    write_attributes(output,attributes_lt)
    output.close()

def _add_grid_dimension(grid,dimension,size):
    "Add a dimension to the grid with duplicate data."

    oldShape = grid.shape
    newShape = list(oldShape)

    newShape.reverse()
    newShape.append(size)
    newShape.reverse()

    newGrid = na.zeros(newShape,dtype=grid.dtype)
    newGrid[:] = grid

    if dimension > 0:
        newGrid = na.rollaxis(newGrid,0,dimension+1)

    return newGrid
