# coding: utf-8
import numpy as np
import unyt as u
from scipy.interpolate import interp1d

fname = "puchwein19_bkgthick.out"
source = "Puchwein et al 2019"

zs = np.genfromtxt(fname, max_rows=1)
data = np.genfromtxt(fname, skip_header=11)

Ryd = 2.1798723611035e-18 * u.J
wave = data[:, 0] * u.Angstrom

# The table likely contains duplicate entries for the Lyman series
# One entry is just redward, and the other is just blueward
# Shift both entries slightly
# Indicies of duplicates based on https://stackoverflow.com/a/25265385

unq_wv, freq = np.unique(wave, return_counts=True)
pairs = [(wave == val).nonzero()[0] for val in unq_wv[freq>1]] # list of arrays w/ indicies

for pair in pairs:
    assert pair.size==2, "More than two duplicates found"
    assert pair[0] < pair[1]

    # adjust wavelenghts by 0.01%
    wave[pair[0]] -= 0.0001 * wave[pair[0]]
    wave[pair[1]] += 0.0001 * wave[pair[1]]

energy = wave.to("J", equivalence="spectral") / Ryd
    
# Set the lowest and highest frequencies Cloudy expects to negligible flux
lJ_pad = -50

for iz, z in enumerate(zs):

    
    fname = f"z_{z:.4e}.out"
    spec = np.log10(data[:, iz+1])

    interp = interp1d(energy, spec)

    with open(fname, "w") as f:
        f.write(f"# {source}\n")
        f.write(f"# z = {z:.6f}\n")
        f.write("# E [Ryd] log (J_nu)\n")

        f.write(f"interpolate ({1e-8:.10f}) ({lJ_pad:.10f})\n")
        f.write(f"continue ({energy[-1].value*0.99:.10f}) ({lJ_pad:.10f})\n")

        # loop backwards through wavelengths so that lowest energy is first
        for i in range(energy.size-1, -1, -1):
            f.write(f"continue ({energy[i].value:.10f}) ({spec[i]:.10f})\n")

        f.write(f"continue ({energy[0].value*1.01:.10f}) ({lJ_pad:.10f})\n")
        f.write(f"continue ({7.354e6:.10f}) ({lJ_pad:.10f})\n")

        x = 10**interp(1)
        f.write(f"f(nu) = {np.log10(x * 4 * np.pi):.10f} at {1:.10f} Ryd\n")
