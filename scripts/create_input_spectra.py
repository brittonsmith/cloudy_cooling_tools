"""
Script for creating input files for Cloudy from Haardt/Madau and Faucher-Giguerre models.
"""

import glob
import numpy as np
import os

tiny_number = 1e-50
l_tiny = np.log10(tiny_number)

planck_constant_cgs   = 6.62606896e-27  # erg s
speed_of_light_cgs = 2.99792458e10
Ryd_to_erg = 13.60569253 * 1.60217646e-12

def read_UVB_data_FG(input_directory, file_suffix=".dat"):
    "Load Faucher-Giguere data."

    print "Loading Faucher-Giguere data from %s." % input_directory
    redshift = []
    energy = None
    jnu = []
    for my_file in glob.glob(os.path.join(input_directory, 
                                          "*" + file_suffix)):
        my_energy = []
        my_jnu = []
        my_redshift = None
        lines = open(my_file).readlines()
        for line in lines:
            if line.startswith("#z="):
                my_redshift = float(line[3:])
                continue
            elif line.startswith("#"):
                continue
            elif line:
                online = line.split()
                my_energy.append(float(online[0]))
                my_jnu.append(float(online[1]))

        if my_redshift is None:
            print "Could not get redshift from input file: %s." % my_file
            return None

        redshift.append(my_redshift)
        if energy is None: energy = my_energy
        jnu.append(my_jnu)

    redshift = np.array(redshift)
    energy = np.array(energy)
    jnu = np.log10(jnu)
    jnu -= 21.0 # convert from 10^-21 erg s^-1 cm^-2 Hz^-1 sr^-1

    my_sort = redshift.argsort()
    redshift = redshift[my_sort]
    jnu = jnu[my_sort]
    
    return (redshift, energy, jnu)

def read_UVB_data_HM(input_file):
    "Load Haardt & Madau data."

    print "Loading Haardt & Madau data from %s." % input_file
    lines = file(input_file).readlines()
    first_line = True
    wavelength = []
    jnu = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('#'): continue
        online = line.split()
        if not online: continue
        if first_line:
            redshift = np.array(online).astype(float)
            first_line = False
            continue
        wavelength.append(online.pop(0))
        jnu.append(online)

    wavelength = np.array(wavelength).astype(float)
    jnu = np.array(jnu).astype(float)
    jnu = np.rollaxis(jnu, 1)
    jnu[jnu < tiny_number] = tiny_number
    return (redshift, wavelength, np.log10(jnu))

def create_interpolated_spectrum(redshift, jnu, my_redshift):
    indices = np.digitize(my_redshift, redshift)
    indices = np.clip(indices, a_min=1, a_max=redshift.size-1)
    slope = (jnu[indices, :] - jnu[indices-1, :]) / \
      (redshift[indices] - redshift[indices-1])
    values = slope * (my_redshift - redshift[indices]) + jnu[indices, :]
    return values

def write_spectrum_table(output_file, redshift, energy, ljnu,
                         reverse=True):

    my_energy = np.copy(energy)
    my_ljnu = np.copy(ljnu)
    
    e_min = 1.001e-8
    e_max = 7.354e6
    if reverse:
        my_energy = my_energy[::-1]
        my_ljnu = my_ljnu[::-1]
    my_energy = np.concatenate([[0.99 * my_energy[0]],
                                my_energy,
                                [1.01 * my_energy[-1], e_max]])
    my_ljnu = np.concatenate([l_tiny * np.ones(1),
                              my_ljnu,
                              l_tiny * np.ones(2)])
    
    print "Writing spectrum for z = %f to %s." % (redshift, output_file)
    out_file = file(output_file, 'w')
    out_file.write("# Haardt & Madau (2011)\n")
    out_file.write("# z = %f\n" % redshift)
    out_file.write("# E [Ryd] log (J_nu)\n")
    out_file.write("interpolate (%.10f %.10f)\n" % \
                   (e_min, np.log10(tiny_number)))
    for i, e in enumerate(my_energy):
        if my_energy[i] == my_energy[i-1]:
            e *= 1.0001
        out_file.write("continue (%.10f %.10f)\n" % (e, my_ljnu[i]))

    my_e = 1.0
    e_value = np.log10(my_e)
    my_energy = np.log10(my_energy)
    index = np.digitize([e_value], my_energy)[0]
    slope = (my_ljnu[index] - my_ljnu[index - 1]) / \
      (my_energy[index] - my_energy[index - 1])
    my_j = slope * (e_value - my_energy[index]) + my_ljnu[index]
    my_j += np.log10(4 * np.pi)
    out_file.write("f(nu) = %.10f at %.10f Ryd\n" % \
                   (my_j, my_e))
    out_file.close()

def angstrom_to_Ryd(wavelength):
    return planck_constant_cgs * speed_of_light_cgs / \
      (wavelength * 1e-8 * Ryd_to_erg)

def write_spectra(redshift, energy, ljnu,
                  output_redshift, output_dir,
                  reverse=True):

    if not os.path.exists(output_dir): os.mkdir(output_dir)
    for z in output_redshift:
        output_file = os.path.join(output_dir,
                                   "z_%10.4e.out" % z)
        my_spec = create_interpolated_spectrum(redshift, ljnu, [z])
        write_spectrum_table(output_file, z, energy, my_spec[0],
                             reverse=reverse)

def print_redshift_list(redshift, my_format="%10.4e"):
    for z in redshift:
        print my_format % z,
    print ""
        
if __name__ == '__main__':
    my_dlx = 0.05

    redshift_hm, wavelength_hm, ljnu_hm = read_UVB_data_HM("UVB.out")
    energy_hm = angstrom_to_Ryd(wavelength_hm)
    my_lx = np.arange(np.log10(redshift_hm[0]+1), 
                      np.log10(redshift_hm[-1]+1), my_dlx)
    my_redshift = np.power(10, my_lx) - 1
    write_spectra(redshift_hm, energy_hm, ljnu_hm,
                  my_redshift, "HM11_UVB", reverse=True)

    print_redshift_list(my_redshift)
    
    redshift_fg, energy_fg, ljnu_fg = read_UVB_data_FG("fg_uvb_dec11")
    my_lx = np.arange(np.log10(redshift_fg[0]+1), 
                      np.log10(redshift_fg[-1]+1), my_dlx)
    my_redshift = np.power(10, my_lx) - 1
    write_spectra(redshift_fg, energy_fg, ljnu_fg,
                  my_redshift, "FG11_UVB", reverse=False)

    print_redshift_list(my_redshift)
