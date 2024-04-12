import smbus
import time
import datetime
import math
from random import random
import os

import channel_calibration

class ADS7828:
    
    # Globals
    bus = None
    _i2c_addr = 0x48
    _error_counter = 0
    _sample_counter  = 0
    _channel_calibration = None

    # Constants
    full_scale_12bits = math.pow(2, 12)
    _channel_reg_index = [0x000, 0b100, 0b001, 0b101, 0b010, 0b110, 0b011, 0b111]
    #_channel_reg_index = [0x000, 0b001, 0b010, 0b011, 0b100, 0b101, 0b110, 0b111]
    
    # ADS7828 I2C Command Byte
    # Input Type: 
    #   Differential = 0
    #   Single-ended = 1
    adc_input_type = 1

    # Power Mode:
    #   0 = Power Down
    #   1 = Internal Ref OFF, and ADC ON
    #   2 = Internal Ref ON, and ADC OFF
    #   3 = Internal Ref ON, and ADC ON
    adc_power_config = 3

    '''Initialize the ADS7828 object - fast init, no fail'''
    def __init__(self, i2c_bus=1, i2c_addr=0x48) -> None:
        self.bus = smbus.SMBus(i2c_bus)
        self._i2c_addr = i2c_addr
        self._error_counter = 0
        self._sample_counter = 0
        self._channel_0to5V_calibration = channel_calibration.ChannelCalibration("ads7828_channel_voltage_calibration.json",
                                                                           init_channel_count=8)
        self._channel_4to20ma_calibration = channel_calibration.ChannelCalibration("ads7828_channel_4to20ma_calibration.json",
                                                                           init_channel_count=8)
        pass
            
    '''Return voltage for a given channel''' 
    def get_voltage_from_channel(self, channel_index, apply_calibration=True) -> float:
        scale=2.5
        channel_reg_index = self._ch_index_to_reg_index(channel_index)
        command_byte = (self.adc_input_type << 7) + (channel_reg_index << 4 ) + (self.adc_power_config << 2) 
        adc_voltage = float('NaN')
        try:
            self.bus.write_byte(self._i2c_addr, command_byte)
            data = self.bus.read_i2c_block_data(self._i2c_addr, command_byte, 2)
            raw_adc_bits = (data[0] & 0x0F) * 256 + data[1]
            print(f"ch_idx:{channel_index}\tcmd_byte:{command_byte:08b}\tdata:{raw_adc_bits:04x}")
            # Raw / Uncalibrated Voltage
            adc_voltage = (raw_adc_bits / self.full_scale_12bits) * scale
            # Apply Channel Calibration
            if apply_calibration:
                ch_cal = self._channel_0to5V_calibration.get_scale_offset(channel_index)
                adc_voltage = adc_voltage * ch_cal.scale + ch_cal.offset
            self._sample_counter += 1
        except Exception as e:
            print(e)
            self._error_counter += 1
        finally:
            return adc_voltage

    '''Return voltage for a given channel''' 
    def get_4to20ma_from_channel(self, channel_index) -> float:
        scale=2.5
        channel_reg_index = self._ch_index_to_reg_index(channel_index)
        command_byte = (self.adc_input_type << 7) + (channel_reg_index << 4 ) + (self.adc_power_config << 2) 
        adc_voltage = float('NaN')
        try:
            self.bus.write_byte(self._i2c_addr, command_byte)
            data = self.bus.read_i2c_block_data(self._i2c_addr, command_byte, 2)
            raw_adc_bits = (data[0] & 0x0F) * 256 + data[1]
            print(f"ch_idx:{channel_reg_index}\tcmd_byte:{command_byte:08b}\tdata:{raw_adc_bits:04x}")
            # Raw / Uncalibrated Voltage
            adc_voltage = (raw_adc_bits / self.full_scale_12bits) * scale
            # Apply Channel Calibration
            ch_cal = self._channel_4to20ma_calibration.get_scale_offset(channel_index)
            adc_voltage = adc_voltage * ch_cal.scale + ch_cal.offset
            self._sample_counter += 1
        except Exception as e:
            print(e)
            self._error_counter += 1
        finally:
            return adc_voltage
    
    '''Read 8 channels and return list of voltages''' 
    def get_voltages_from_device(self, apply_calibration=True) -> list:
        voltages = list()
        for channel_index in range(8):
            voltages.append(self.get_voltage_from_channel(channel_index, apply_calibration))
        return voltages

    '''Read 8 channels and return list of voltages''' 
    def get_currents_from_device(self) -> list:
        currents = list()
        for channel_index in range(8):
            currents.append(self.get_4to20ma_from_channel(channel_index))
        return currents
    
    '''Print a static table of data to the console'''
    def print_data_table(self, data_dict):
        
        total_width = (len(list(data_dict.keys()))+1)*10+1
        
        # Print Header
        print("_"*total_width)
        header = list()
        for device_name in list(data_dict.keys()):
            header.append(device_name)
        self._print_data_line(header)
        print("-"*total_width)
        line = "|"
        for voltage in list(data_dict.values()):
            float_str = f"{voltage:.3f}"
            line += f"{float_str:>10}|"
        print(line)
        err_rate = 0
        if self._sample_counter > 0:
            err_rate = (self._error_counter / self._sample_counter)
        print(f"Errors: {self._error_counter}   Samples: {self._sample_counter}    Error Rate: {err_rate:.1f}")    
  
    '''Print a pretty data line'''
    def _print_data_line(self, line_list):
        line_str = "|"
        for item in line_list:
            line_str = line_str + f'{str(item):^10}' + "|"
        print(line_str)

    '''Convert numerical channel index to register value'''
    def _ch_index_to_reg_index(self, adc_channel_index) -> int:
        if adc_channel_index >= 0 and adc_channel_index <= 7:
            return self._channel_reg_index[adc_channel_index]
        else:
            raise Exception(f"_ch_index_to_reg_index invalid adc channel index provided: {adc_channel_index}")
    
    # End of ADS7828 Class
 
'''Measure and print 8 channels'''
if __name__ == '__main__':
    
    # ADC Device
    ads7828 = ADS7828()
    
    while True:
        now = datetime.datetime.now()
        print(f"Time: {now}")
        #adc_raw_data = ads7828.get_voltages_from_device(apply_calibration=False)
        adc_raw_data = ads7828.get_currents_from_device()
        data_dict = dict()
        channel_index = 0
        
        for voltage in adc_raw_data:
            data_dict[f"Channel {channel_index+1}"] = voltage
            channel_index = channel_index + 1
        ads7828.print_data_table(data_dict)
        time.sleep(0.2)
        os.system('cls' if os.name == 'nt' else 'clear')
    