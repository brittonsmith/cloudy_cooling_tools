# Cloudy cooling tools

Hello! This code is very old. It mostly still works, but is poorly
organized and documented. Contributions very welcome and
appreciated. Contact Britton Smith at brittonsmith@gmail.com with any
questions.

## What is this?

This repository contains a code called CIAOLoop, which is capable of
running and colating grids of Cloudy models in parallel. It has
multiple running modes for creating:
* cooling tables for Grackle
* ionization balance tables for trident
* xray emissivity tables for yt
* line emissivity tables like those used in the FOGGIE II paper
* any dimensional grids of Cloudy runs to fill your heart with joy

In addition, there are also:
* cloudy_grids - Python routines for converting ascii tables to hdf5
* scripts - helpful Perl scripts for making cooling tables
* examples - example parameter files for making various types of data
* parallel_tools - some tools for running in parallel

Executables:

* CIAOLoop - the main cooling map generation code (a.k.a. ROCO in
  Smith, Sigurdsson, & Abel 2008) Type ./CIAOLoop -h for options.

Scripts:

* combine_runfile_parts.pl - combines partial run files made when
  using the -mp option with CIAOLoop. Type ./combine_runfile_parts.pl
  with no argument for usage. 
* find_map_zeros.pl - Looks for gaps in the cooling data and fills
  with zeroes.
* subtract_cooling.pl - used to make metals only cooling data.
  Subtracts metal-only cooling data from data with all elements to
  make metal-only data.  USE THE OTHER ONE. Type ./subtract_cooling.pl
  with no argument for usage.
* subtract_cooling_lite.pl - same as subtract_cooling.pl, except uses
  less ram and may be slightly slower.  USE THIS ONE.

Examples:

* grackle - directory of parameter files for making grackle tables
* sample_cooling.par - sample cooling map parameter file.
* sample_cooling_metal_free.par - sample parameter file for metal-free cooling.
* metal_free.dat - additional Cloudy commands for disabling metals
  with metals-free cooling data.
* xray_emissivity.par - sample parameter file for making x-ray emissivity maps.

## Running CIAOLoop:

See sample_cooling.par for a sample parameter file.

CIAOLoop:
Usage: ./CIAOLoop [flags] <parameter file>
        -h: print this help text.
        -m <filename>: supply machine file for running on multiple machines.
        -mp <this part> <total parts>: break run into parts to be run separately.
        -np <number of processors>: run on multiple cores on a single machine.
        -r: restart run from last file finished.
        -x: reprocess existing output data instead of running Cloudy.

For restarts, the code will go through the previously made 
run file, and restart the last map on the list.

### Parallelism

To run on more than one node, you need to specify a machine file.
Example machine file:

machine1:1
machine1:1
machine2:1
machine2:1

See the note below for running batch jobs on distributed memory systems.

### Changing the precision of the cooling maps.

Change the values of the variables: 
$temperaturePrecision (Line 189)
$heatingPrecision (Line 192)
$coolingPrecision (Line 195)
$mmwPrecision (Line 198)

### Note on Cloudy versions.

The file format for the cooling output was changed between Cloudy versions 
06 and 07.  If you are using versions 06 or earlier, uncomment line 2017 
and comment out line 2006.  If you are using version 07 or later, comment 
out line 2020, and uncomment line 2006.  ROCO is currently set to work with 
versions 07 and later.

### Running on distributed systems

Note, this is very old and probably doesn't work well anymore.

To run this in parallel on a distributed memory system, you will just 
need to supply a machine file at run time that has the full list of 
available nodes.  The parallel tools directory contains some crude 
scripts to help out with that.

* make_machine_list.pl - this will read in the id of the job from a file 
                       called "job.dat" and will parse "qstat -f" to 
                       get the allocated nodes.  It will then write 
                       a machine file called "machines.dat" that can 
                       be used with CIAOLoop.
* submit_job.pl - this is a simple wrapper around the qsub command that 
                will write the job id to a file called "job.dat" that 
                can be used with the above script.  Give the name of the 
                batch script file on the command line.

An example of using these to run a parallel CIAOLoop job on a 
supercomputing system with a queue.

In the batch script:

```
./make_machine_list.pl

./CIAOLoop -m machines.dat <parameter_file>
```

To submit the job:

```
./submit_job.pl <batch script>
```

## Converting Ascii tables to HDF5

The *cloudy_grids* directory has Python tools for converting cooling,
ionization balance, x-ray emission, and line emissivity tables to
hdf5. To use it, do:

```
cd cloudy_grids
pip install -e .
```

For documentation on running the various functions do (in Python):
```
>>> from cloudy_grids import *
>>> # see what functions exist
>>> dir()
>>> # use help to get documentation
>>> help(convert_cooling_tables)
```

The *cloudy_grids/scripts* file contains a script used to convert hdf5
files into Grackle-readable format. It may need a little TLC.
