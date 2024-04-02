# Stores and provides scalar information for ADC channels.
# Converts ADC values to field values

# Reference
# https://www.geeksforgeeks.org/convert-json-to-dictionary-in-python/?ref=lbp
# https://www.geeksforgeeks.org/how-to-convert-python-dictionary-to-json/

import os
from os.path import exists
import json

class ScaleOffset:
    scale = None
    offset = None
    
    def __init__(self):
        self.scale = 1.0
        self.offset = 0
    
        
class ChannelCalibration:

    _calibration_dict = None
    _json_file_name = None

    def __init__(self, config_file_name="default_channel_config.json", init_channel_count=8) -> None:
        self._calibration_dict = dict()
        self._json_file_name = config_file_name
        if exists(self._json_file_name):
            # File name is provided - read file
            with open(self._json_file_name) as json_file:
                self._calibration_dict = json.load(json_file)
        else:
            # File Name is Blank - create default  
            # Generate default file with initial channel count
            for channel_index in range(init_channel_count):
                self._calibration_dict[channel_index] = ScaleOffset()
            # Write file
            self._write_json_file()
    
    def scalars_copy(self) -> dict:
        return self._calibration_dict.copy()
    
    def write_scalar(self, key, value):
        self._calibration_dict[key] = value
        self._write_json_file()
    
    def _write_json_file(self):
        with open(self._json_file_name, "w") as outfile:
            json.dump(self._calibration_dict, outfile, default=vars)
            
    def get_scale_offset(self, channel_index=0) -> ScaleOffset:
        scale_offset = ScaleOffset()
        scale_offset.scale = self._calibration_dict[str(channel_index)].get('scale')
        scale_offset.offset = self._calibration_dict[str(channel_index)].get('offset')
        return scale_offset

if __name__ == '__main__':
    test = ChannelCalibration()
    print(test.scalars_copy())
    test = ChannelCalibration("new_file", 64)
    print(test.scalars_copy())
    test.write_scalar('0', ScaleOffset())
    print(test.scalars_copy())