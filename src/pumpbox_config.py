'''
Config file I/O for static app parameters
'''
import json
from collections import defaultdict
from os.path import exists
import os
import copy
from enum import IntEnum
from enum import Enum
import logger

class ConfigManager:

    # Private Class Constants
    _CONFIG_FOLDER = "conf"
    _log_key = "config"

    # Public Class Members
    active_config = None

    '''
    Construction - create empty active config
    '''
    def __init__(self, init_cfg_file_name : str, app_logger : logger.Logger) -> None:
        self._app_logger = app_logger
        # Create tree
        self.active_config = tree()
        # Attempt to load from disk
        (load_ok, load_msg) = self.load_from_disk_by_path(init_cfg_file_name)
        if load_ok is False:
            self._app_logger.write(self._log_key, load_msg, logger.MessageLevel.ERROR)
            self._app_logger.write(self._log_key, "Loading default config...", logger.MessageLevel.INFO)
            self.set_as_default_config()
            self._app_logger.write(self._log_key, "Default config loaded.", logger.MessageLevel.INFO)
            default_file_path = os.path.join(os.getcwd(), self._CONFIG_FOLDER, "default.json")
            self.save_to_disk_filepath(default_file_path, True)
            self._app_logger.write(self._log_key, f"Default config saved as: {default_file_path}", logger.MessageLevel.INFO)
            
    '''
    Load a config from disk by config name
    '''
    def load_from_disk_by_path(self, config_file_name : str) -> tuple:
        full_config_file_path = os.path.join(os.getcwd(), self._CONFIG_FOLDER, config_file_name)   
        json_string = ""
        try:
            with open(full_config_file_path, 'r') as file:
                json_string = file.read()
                self.active_config = json.loads(json_string)
        except FileNotFoundError:
            # Create default config
            self.set_as_default_config()
            self.save_to_disk_filepath(full_config_file_path, True)
            return (True, f"Created configuration file '{full_config_file_path}' with default settings.")
        except json.JSONDecodeError:
            return (False, f"Error decoding JSON in '{full_config_file_path}' not found.")

        return (True, json_string)
    
    '''
    Provides a deep copy of the active config
    '''
    def deep_copy(self) -> defaultdict:
        return copy.deepcopy(self.active_config)
    
    '''
    Save the config to disk with a specified filepath
    '''
    def save_to_disk_filepath(self, filepath, overwrite : bool) -> bool:
        # Check if the file exists; append is not supported.
        if exists(filepath):
            if (overwrite):
                os.remove(filepath)
            else:
                raise Exception("File already exists and overwrite disabled: {0}".format(filepath))
        else:
            # Create folder if it doesn't exist
            folder_path = os.path.dirname(filepath)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            
        # Write to disk
        with open(filepath, 'w') as file:
            file.write(self.to_json_string())
    
    '''
    Save the config to disk based on the config's name (useful for 'Save' function)
    '''
    def save_to_disk_by_name(self, overwrite : bool = True) -> bool:
        if ("Name" not in self.active_config):
            raise Exception("Config does not have a name; cannot save to disk.")
        # Build file path based on name
        full_file_path = self._config_name_to_filepath(self.active_config['Name'])
        # Check if the file exists; append is not supported.
        if exists(full_file_path):
            if (overwrite):
                os.remove(full_file_path)
            else:
                raise Exception("File already exists and overwrite disabled: {0}".format(self._filename))
            
        # Write to disk
        self.save_to_disk_filepath(full_file_path, overwrite)

    '''
    Create a full file path based on the config name
    '''
    def _config_name_to_filepath(self, config_name : str) -> str:
        full_file_name = config_name + ".json"
        full_file_path = os.path.join(os.getcwd(), self._CONFIG_FOLDER, full_file_name)
        return full_file_path

    '''
    Build a default configuration - useful for first time run in a new environment
    Uncomment ONE of the following functions
    '''
    def set_as_default_config(self) -> None:
        self.active_config = tree()
        self.active_config['Name'] = 'default'
        
        # MQTT Broker Connection
        #self.active_config['mqtt_broker']['connection']['host_addr'] = 'sc-app'
        self.active_config['mqtt_broker']['connection']['host_addr'] = 'debian-openhab'
        self.active_config['mqtt_broker']['connection']['host_port'] = 1883

        # All Topics
        self.active_config['base_topic'] = '/RainBarrelPump'
        
        # Subscribe Topics
        self.active_config['subscribe']['pump_control'] = 'remote_run_state'
        
        # Publish Topics
        self.active_config['publish']['system_state'] = 'system_state'
        self.active_config['publish']['valve_state'] = 'valve_state'
        self.active_config['publish']['valve_position'] = 'valve_position'
        self.active_config['publish']['water_pressure'] = 'pressure'
        self.active_config['publish']['motor_current'] = 'motor_current'
        self.active_config['publish']['pump_run_time_secs'] = 'pump_run_time_secs'
        self.active_config['publish']['error_message'] = 'error_message'

        # Ball Valve
        self.active_config['ball_valve']['open_pin'] = 0
        self.active_config['ball_valve']['close_pin'] = 1
        self.active_config['ball_valve']['direction_pin'] = 8
        self.active_config['ball_valve']['enable_pin'] = 9
        self.active_config['ball_valve']['transition_time_secs'] = 20

        # Motor Contactor
        self.active_config['motor_contactor']['direction_pin'] = 10
        self.active_config['motor_contactor']['enable_pin'] = 11
        self.active_config['motor_contactor']['max_motor_runtime_secs'] = 1200

        # Motor Current
        self.active_config['motor_current']['adc_channel_index'] = 0
        #self.active_config['motor_current']['scale'] = 1.563
        #self.active_config['motor_current']['offset'] = -6.250
        self.active_config['motor_current']['scale'] = 4.25
        self.active_config['motor_current']['offset'] = 0
        self.active_config['motor_current']['max_motor_current_amps'] = 10.0
        
        # Water Pressure
        self.active_config['water_pressure']['adc_channel_index'] = 1
        self.active_config['water_pressure']['scale'] = 1
        self.active_config['water_pressure']['offset'] = 0
                    
    '''
    Recursively convert all defaultdicts to dicts; useful for JSON serialization
    '''
    def _unwrap_defaultdict(self, config_dict : defaultdict) -> dict:
        new_dict = {}
        for key, value in config_dict.items():
            if isinstance(value, defaultdict):
                new_dict[key] = dict(self._unwrap_defaultdict(value))
            else:
                new_dict[key] = copy.deepcopy(value)
        return new_dict    

    '''
    Convert the current active config to a JSON string
    '''
    def to_json_string(self) -> str:
        # Convert all defaultdicts to dicts
        config_dict = dict()
        for key, value in self.active_config.items():
            if isinstance(value, defaultdict):
                config_dict[key] = self._unwrap_defaultdict(value)
            else:
                config_dict[key] = value
        json_string = json.dumps(config_dict)
        return json_string

def tree(): return defaultdict(tree)