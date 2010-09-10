"""
Britton Smith <brittonsmith@gmail.com>

Set all values in a dataset to zero.
"""

import h5py
from hdf5_attributes import *

def zero_dataset(input_file,data_fields=['Heating','MMW'],output_file=None):
    "Set all values in a dataset to zero."

    if output_file is None:
        output_file = input_file

    data = {}

    print "Reading file: %s." % input_file
    input = h5py.File(input_file,'r')
    for dataset in input.listnames():
        data[dataset] = input[dataset].value
    attributes = get_attributes(input)
    input.close()

    for dataset in data_fields:
        print "Setting %s to zero." % dataset
        data[dataset][:] = 0.0


    print "Writing file: %s." % output_file
    output = h5py.File(output_file,'w')
    for dataset in data.keys():
        output.create_dataset(dataset,data=data[dataset])
    write_attributes(output,attributes)
    output.close()
