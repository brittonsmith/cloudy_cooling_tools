from cloudy_ascii_hdf5 import *
import sys

input = sys.argv[1]
output = sys.argv[2]
elements = sys.argv[3:]

for element in elements:
    cloudyGrid_ascii2hdf5(input, output, element)
