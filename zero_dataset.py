import h5py
from hdf5_attributes import *

def zero_dataset(inputFile,data_fields=['Heating','MMW'],outputFile=None):
    "Set all values in a dataset to zero."

    if outputFile is None:
        outputFile = inputFile

    data = {}

    print "Reading file: %s." % inputFile
    input = h5py.File(inputFile,'r')
    for dataset in input.listnames():
        data[dataset] = input[dataset].value
    attributes = get_attributes(input)
    input.close()

    for dataset in data_fields:
        print "Setting %s to zero." % dataset
        data[dataset][:] = 0.0


    print "Writing file: %s." % outputFile
    output = h5py.File(outputFile,'w')
    for dataset in data.keys():
        output.create_dataset(dataset,data=data[dataset])
    write_attributes(output,attributes)
    output.close()
