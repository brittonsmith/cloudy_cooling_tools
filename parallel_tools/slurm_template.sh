#!/bin/sh
# A template SLURM script for running CIAOLoop jobs in parallel

#SBATCH -N <num nodes>
#SBATCH --ntasks-per-node <procceses PER node>
#SBATCH --mem=<memory per node>
#SBATCH -t <walltime 00:00:00>
#SBATCH -A <account>

# Do any job preamble stuff here; change directories, load modules, etc

# Create the machine list by parsing $SLURM_NODELIST
# Default filename is "machines.dat"
./make_machine_list_slurm.pl

# Run CIAOLoop in parallel
./CIAOLoop -m machines.dat <parameter_file>
