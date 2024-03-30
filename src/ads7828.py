import smbus
import paho.mqtt.client as mqtt
import time
import datetime
import math
from random import random
import os
import scalar

# TODOs
# 2. Connect to actual ADC hardware

class ads7828:
    # Globals
    bus = None

    # Constants
    base_i2c_addr = 0x48
    full_scale_12bits = math.pow(2, 12)
    _channel_reg_index = [0x000, 0b100, 0b001, 0b101, 0b010, 0b110, 0b011, 0b111]

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

    def __init__(self, i2c_bus=1) -> None:
        self.bus = smbus.SMBus(i2c_bus)
        pass

    # Return voltage for a given channel
    def get_voltage_from_channel(self, i2c_addr, channel_index, scale=5.0) -> float:
        channel_reg_index = self._ch_index_to_reg_index(channel_index)
        command_byte = (self.adc_input_type << 7) + (channel_reg_index << 4 ) + (self.adc_power_config << 2) 
        self.bus.write_byte(i2c_addr, command_byte)
        time.sleep(0.01)
        data = self.bus.read_i2c_block_data(i2c_addr, command_byte, 2)
        raw_adc_bits = (data[0] & 0x0F) * 256 + data[1]
        #print(f"i2c_addr:{i2c_addr:02x}\tch_idx:{channel_reg_index}\tcmd_byte:{command_byte:08b}\tdata:{raw_adc_bits:04x}")
        adc_voltage = (raw_adc_bits / self.full_scale_12bits) * scale
        return adc_voltage
    
    # Read 8 channels and return list of voltages
    def get_voltages_from_device(self, i2c_addr) -> list():
        voltages = list()
        for channel_index in range(8):
            voltages.append(self.get_voltage_from_channel(i2c_addr, channel_index))
        return voltages

    # Print a static table of data to the console
    def print_data_table(self, data_dict):
        total_width = (len(list(data_dict.keys()))+1)*10+1
        # Print Header
        print("_"*total_width)
        header = list()
        header.append("Channel")
        for device_name in list(data_dict.keys()):
            header.append(device_name)
        self._print_data_line(header)
        print("="*total_width)
        # Print one row per channel
        for channel_index in range(8):
            channel_line_list = list()
            channel_line_list.append(str(channel_index))
            for device_key in list(device_data.keys()):
                channel_values_list = device_data[device_key]
                channel_value = channel_values_list[channel_index]
                channel_line_list.append(f'{channel_value:.3f}')
            self._print_data_line(channel_line_list)

    def _print_data_line(self, line_list):
        line_str = "|"
        for item in line_list:
            line_str = line_str + f'{str(item):^10}' + "|"
        print(line_str)

    def _ch_index_to_reg_index(self, adc_channel_index) -> int:
        if adc_channel_index >= 0 and adc_channel_index <= 7:
            return self._channel_reg_index[adc_channel_index]
        else:
            raise Exception(f"_ch_index_to_reg_index invalid adc channel index provided: {adc_channel_index}")
 
# MQTT Client
flag_connected = False
# MQTT Client Callback - Connected
def on_connect(client, userdata, flags, rc):
        global flag_connected
        flag_connected = 1

# MQTT Client Callback - Disconnected
def on_disconnect(client, userdata, rc):
        global flag_connected
        flag_connected = 0   

# Convert current transducer output voltage to measured current (A) based on the scalar config.
def current_transducer_to_power(transducer_output_volts, transducer_scalar) -> float:
    # Transducer Voltage to Current (0 - 5.0V to Transducer Scale)
    current_transducer_output_scale_volts = 5.0
    current_transducer_input_scale_amps = transducer_scalar
    line_current_amps = (transducer_output_volts / current_transducer_output_scale_volts) * current_transducer_input_scale_amps
    # Current to Power
    line_voltage = 120
    line_average_power_watts = line_current_amps * line_voltage / 2
    return line_average_power_watts

if __name__ == '__main__':
    debug_single_channel = False
    # Debug Single channel
    if debug_single_channel == True:
        bus = smbus.SMBus(1)
        counter = 1
        dev_addr = 0x4A
        bus.write_byte(dev_addr, 0x08)
        time.sleep(1)
        while True:
            bus.write_byte(dev_addr, 0x8C)
            time.sleep(0.5)
            data = bus.read_i2c_block_data(dev_addr, 0x8C, 2)
            time.sleep(0.5)
            raw_adc = (data[0] & 0x0F) * 256 + data[1]
            print(F"Analog Input [{counter}]: {raw_adc}")
            counter = counter + 1
            
    app_start_time = datetime.datetime.now()
    # App Constants
    report_period_secs = 5.0

    # ADC interface / driver
    adc = ads7828()

    # Create four ports
    device_data = dict()
    device_data["Port A"] = list()
    device_data["Port B"] = list()
    device_data["Port C"] = list()
    device_data["Port D"] = list()

    # Create MQTT Client
    openhab_host = "debian-openhab"
    mqtt_broker_port = 1883
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    try:
        client.connect(openhab_host, mqtt_broker_port)
        client.loop_start()
    except:
            print('MQTT client connect failure')
            flag_connected = False

    # Create Scalar
    meas_scalars = scalar.scalar("32ch_ads7828.json")

    # loop forever printing ADC values and sending to OpenHab
    while True:
        loop_start_time = datetime.datetime.now()
        os.system('cls' if os.name == 'nt' else 'clear')
        # Device Index Iterator
        device_index_itr = ads7828.base_i2c_addr

        # Iterate through each port
        for device_key in device_data.keys():
            data_list = adc.get_voltages_from_device(device_index_itr)
            device_data[device_key] = data_list
            device_index_itr = device_index_itr + 1

        # Send data to OpenHab
        channel_index = 1
        scalars_copy = meas_scalars.scalars_copy()
        for device_key in device_data.keys():
            for measurement in device_data[device_key]:
                uid = f'\elec_load\channel_{channel_index}'
                # Convert voltage to current to power
                scalar_value = scalars_copy[str(channel_index)]
                line_average_power_watts = current_transducer_to_power(measurement, scalar_value)
                infot = client.publish(uid, round(line_average_power_watts, 2), qos=1, retain=False)
                infot.wait_for_publish()
                channel_index = channel_index + 1

        # --- Special Calculations ---
        # Dryer: sum two channels and report
        uid = '\elec_load\dryer_power'
        dryer_branch_1_current = device_data["Port D"][5]
        dryer_branch_2_current = device_data["Port D"][6]
        dryer_branch_1_scalar_value = scalars_copy['25']
        dryer_branch_2_scalar_value = scalars_copy['26']
        dryer_branch_1_power = current_transducer_to_power(dryer_branch_1_current, dryer_branch_1_scalar_value)
        dryer_branch_2_power = current_transducer_to_power(dryer_branch_2_current, dryer_branch_2_scalar_value)
        total = dryer_branch_1_power + dryer_branch_2_power
        infot = client.publish(uid, round(total, 2), qos=1, retain=False)
        infot.wait_for_publish()
        # Dryer: sum two channels and report
        uid = '\elec_load\garage_subpanel_power'
        garage_subpanel_branch_1_current = device_data["Port B"][7]
        garage_subpanel_branch_2_current = device_data["Port D"][7]
        garage_subpanel_branch_1_scalar_value = scalars_copy['27']
        garage_subpanel_branch_2_scalar_value = scalars_copy['28']
        garage_subpanel_branch_1_power = current_transducer_to_power(garage_subpanel_branch_1_current, garage_subpanel_branch_1_scalar_value)
        garage_subpanel_branch_2_power = current_transducer_to_power(garage_subpanel_branch_2_current, garage_subpanel_branch_2_scalar_value)
        total = garage_subpanel_branch_1_power + garage_subpanel_branch_2_power
        infot = client.publish(uid, round(total, 2), qos=1, retain=False)
        infot.wait_for_publish()
        
        # Print Data Table to console
        
        print("Table 1 - ADC Voltages")
        adc.print_data_table(device_data)
        
        # Report Time Durations and delay to reporting period
        loop_finish_time = datetime.datetime.now()
        app_duration_time = (loop_finish_time - app_start_time).total_seconds()
        loop_duration_time = (loop_finish_time - loop_start_time).total_seconds()
        print(f"App time:\t{app_duration_time:.3f} s")
        print(f"Loop time:\t{loop_duration_time:.3f} s")
        if loop_duration_time > report_period_secs:
            pass
        else:
            delay_secs = report_period_secs - loop_duration_time - 0.01
            time.sleep(delay_secs)