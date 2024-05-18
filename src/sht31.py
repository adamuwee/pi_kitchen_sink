import busio
from busio import I2C
from adafruit_bus_device import i2c_device
from board import SCL, SDA

import time
import datetime
from random import random
import os

import json

class SingleTempHumidityMeasurement:
        
    timestamp_isostr = None 
    temperature = None
    humidity = None

    def __init__(self, temperature : float, humidity : float):
        self.timestamp_isostr = datetime.datetime.now().isoformat()
        self.temperature = temperature
        self.humidity = humidity
        
    def __str__(self) -> str:
        meas_str = f"Temperature: {self.temperature:.1f}F, Humidity: {self.humidity:.1f}%"
        return meas_str
            
    def to_json(self) -> str:
        json_dict = dict()
        json_dict["iso_timestamp"] = self.timestamp_isostr
        json_dict["temperature"] = self.temperature
        json_dict["humidity"] = self.humidity
        return json.dumps(json_dict)
    
class SHT31():
    def __init__(self, i2c_addr : int = 0x44) -> None:
        i2c = busio.I2C(SCL, SDA)
        self.i2c_device = i2c_device.I2CDevice(i2c, i2c_addr)
        
    def read_temp_humidity(self) -> SingleTempHumidityMeasurement:
        wr_data = bytearray(2)
        wr_data[0] = 0x2C
        wr_data[1] = 0x06
        self.i2c_device.write(wr_data)
        # SHT31 address, 0x44(68)
        # Read data back from 0x00(00), 6 bytes
        # Temp MSB, Temp LSB, Temp CRC, Humididty MSB, Humidity LSB, Humidity CRC
        data = bytearray(6)
        self.i2c_device.readinto(data)
        # Convert the data
        temp = data[0] * 256 + data[1]
        cTemp = -45 + (175 * temp / 65535.0)
        fTemp = -49 + (315 * temp / 65535.0)
        humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
        return SingleTempHumidityMeasurement(fTemp, humidity)
    # End of SHT31 Class
 
'''Measure and print 8 channels'''
if __name__ == '__main__':
    
    # ADC Device
    sht31_device = SHT31()
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        measurement = sht31_device.read_temp_humidity()
        print(f"Time: {datetime.datetime.now()}")
        print(measurement)
        time.sleep(0.2)        
