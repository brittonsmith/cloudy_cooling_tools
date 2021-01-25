# Grackle parameter files

Files in here were used to make the cooling tables used by the Grackle
chemistry and cooling library.

File keywords:
* ot - optically thin: no self-shielding. Cloudy outputs illuminated
face of the cloud (i.e., zone 1).
* mf - metal-free: all elements other than H/He are disabled
* sh - self-shielding: Cloudy integrates to cloud depth given by local
Jeans length or max 100 pc.
* cr - cosmic rays: cosmic ray flux includes at a fraction of local MW
value (see coolingMapCRFraction parameter in CIAOLoop)

Files:
* noUVB[_mf].par - collisional ionization equilibrium (CIE, i.e., no radiation) run
* hm_2012[_mf/sh/cr].par - Haardt & Madau (2012) UV background run
* fg_2011[_mf/sh/cr].par - Faucher-Giguerre (2011) UV background run
* metal_free.dat - commands to disable metals in Cloudy
* HM12_UVB - directory with Cloudy-readable spectra of Haardt\Madau background
* FG11_UVB - directory with Cloudy-readable spectra for FG2011 background
