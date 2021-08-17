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
nu = wave.to("J", equivalence="spectral") / Ryd

lJ_pad = -50

for iz, z in enumerate(zs):

    fname = f"z_{z:.4e}.out"
    spec = np.log10(data[:, iz+1])

    interp = interp1d(nu, spec)

    with open(fname, "w") as f:
        f.write(f"# {source}\n")
        f.write(f"# z = {z:.6f}\n")
        f.write("# E [Ryd] log (J_nu)\n")

        f.write(f"interpolate ({1e-8:.10f}) ({lJ_pad:.10f})\n")
        f.write(f"continue ({nu[-1]*0.99:.10f}) ({lJ_pad:.10f})\n")

        # loop backwards through wavelengths so that lowest energy is first
        for i in range(nu.size-1, -1, -1):
            f.write(f"continue ({nu[i]:.10f}) ({spec[i]:.10f})\n")

        f.write(f"continue ({nu[0]*1.01:.10f}) ({lJ_pad:.10f})\n")
        f.write(f"continue ({7.354e6:.10f}) ({lJ_pad:.10f})\n")

        x = 10**interp(1)
        f.write(f"f(nu) = {np.log10(x * 4 * np.pi):.10f} at {1:.10f} Ryd\n")
