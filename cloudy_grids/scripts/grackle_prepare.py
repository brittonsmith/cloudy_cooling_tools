"""
Prepare cooling data for Grackle.

Britton Smith <brittonsmith@gmail.com>
"""

from collections import defaultdict
import h5py
import numpy as np
import sys

class H5InMemory(object):
    def __init__(self, fh):
        if isinstance(fh, str):
            fh = h5py.File(fh, 'r')

        self.attrs = {}
        if hasattr(fh, "attrs"):
            self.attrs = dict([(attr, fh.attrs[attr]) \
                               for attr in fh.attrs])
                               
        if isinstance(fh, h5py.highlevel.Dataset):
            self.value = fh.value
        else:
            self.data = dict([(field, H5InMemory(fh[field])) \
                               for field in fh.keys()])

        if isinstance(fh, h5py.highlevel.File):
            fh.close()

    def __getitem__(self, key):
        return self.data[key]

    def __repr__(self):
        if hasattr(self, "data"):
            return "<H5InMemory Group object (%d items)>" % \
              len(self.keys())
        else:
            return "<H5InMemory Data object %s>" % \
              str(self.value.shape)

    def __str__(self):
        return self.__repr__()

    def __iter__(self):
        for field in self.keys():
            yield field
    
    def keys(self):
        if hasattr(self, "data"):
            return self.data.keys()
        return None

    def save(self, fh):
        top = False
        if isinstance(fh, str):
            top = True
            fh = h5py.File(fh, 'w')

        for attr in self.attrs:
            fh.attrs[attr] = self.attrs[attr]
            
        if hasattr(self, "data"):
            for field in self:
                if hasattr(self.data[field], "data"):
                    self.data[field].save(fh.create_group(field))
                else:
                    dfh = fh.create_dataset(field, 
                                            data=self.data[field].value)
                    self.data[field].save(dfh)

        if top:
            fh.close()

def rearrange_attrs(data):
    "Move Temperature, Parameter1, Parameter2, etc. datasets to attributes."
    ignore_attrs = ["Dimension", "Rank"]
    ignore_fields = ["MMW"]
    datasets = ["Cooling", "Heating"]
    new_attrs = {}

    # Grab data from the datasets that are to be converted to attributes.
    for field in data.keys():
        if field in ignore_fields + datasets: continue
        new_attrs[field] = data[field].value
        for attr in data[field].attrs.keys():
            if attr in ignore_attrs: continue
            new_attrs["%s_%s" % (field, attr)] = data[field].attrs[attr]
        del data.data[field]

    # Add the new attributes to the datasets that are to be kept.
    for field in datasets:
        data[field].attrs.update(new_attrs)

    # Remove unwanted fields.
    for field in ignore_fields:
        if field in data.keys():
            del data.data[field]
            
if __name__ == "__main__":
    if (len(sys.argv) < 4):
        print("Usage: python grackle_prepare.py [uvb_file] [no_uvb_file] [output_file]")
        exit(1)
    
    uvb_file = sys.argv[1]
    no_uvb_file = sys.argv[2]
    output_file = sys.argv[3]

    print("Reading %s." % uvb_file)
    uvb_data = H5InMemory(uvb_file)

    # Rename Parameter2 Name attribute
    print("Changing Parameter2 attribute Name from %s to redshift." % \
      uvb_data["Parameter2"].attrs["Name"])
    uvb_data["Parameter2"].attrs["Name"] = "redshift"
    
    # Rearrange attributes
    print("Rearranging attributes.")
    rearrange_attrs(uvb_data)

    print("Reading %s." % no_uvb_file)
    no_uvb_data = H5InMemory(no_uvb_file)

    # Zero out heating values for no_uvb data
    print("Zeroing heating values for no_uvb data.")
    no_uvb_data["Heating"].value[:] = 0.0

    # Graft no_uvb data onto uvb_data
    print("Grafting no_uvb data onto uvb_data.")
    for field in ["Cooling", "Heating"]:
        print("Grafting %s." % field)
        new_data = np.concatenate([np.rollaxis(uvb_data[field].value, 1),
                                   [no_uvb_data[field].value]])
        new_data = np.rollaxis(new_data, 1)
        
        uvb_data[field].value = new_data
        uvb_data[field].attrs["Dimension"] = new_data.shape
        uvb_data[field].attrs["Parameter2"] = \
          np.concatenate([uvb_data[field].attrs["Parameter2"],
                          [uvb_data[field].attrs["Parameter2"][-1]]])

    # Scale data to correspond to Z = Zsun.
    scale_factor = 1000.
    print("Scaling data by %f." % scale_factor)
    for field in ["Cooling", "Heating"]:
        uvb_data[field].value *= scale_factor

    # Move datasets into group "CoolingRates/Metals"
    print("Moving datasets into correct groups.")
    uvb_data.data["CoolingRates"] = H5InMemory({})
    uvb_data["CoolingRates"].data["Metals"] = H5InMemory({})
    for field in ["Cooling", "Heating"]:
        uvb_data["CoolingRates"]["Metals"].data[field] = uvb_data[field]
        del uvb_data.data[field]

    # Write out new data.
    print("Saving new dataset as %s." % output_file)
    uvb_data.save(output_file)
