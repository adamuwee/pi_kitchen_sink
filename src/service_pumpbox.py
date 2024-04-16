import time
import datetime

import logger
import pumpbox_config
import mqtt_client_pubsub
import mcp23017
import ads7828
import ball_valve

class ServiceExitError:
    def __init__(self, error = True, error_message = "") -> None:
        self.error = error
        self.error_message = error_message

class PumpMonitor:
    '''Class Constants'''
    LOG_KEY = 'monitor'
    
    '''Public Variables'''
    motor_current_amps = None
    water_pressure_psi = None
    pump_run_time_secs = None
    
    '''Private Variables'''
    _last_mqtt_publish = None
    _pump_start_time = None
    
    def __init__(self, app_logger, app_config, mqtt_client, mqtt_transmit_time_sec=5) -> None:
        '''Monitors environmental conditions of the pump.'''
        self._logger = app_logger
        self._config = app_config
        self._mqtt_client = mqtt_client
        self._mqtt_transmit_time_sec = mqtt_transmit_time_sec
        self._adc = ads7828.ADS7828()
    
    def update(self):
        '''Refreshes measurements from the pump.'''
        # Motor Current (Amps)
        self.motor_current_amps = None
        motor_current_channel_index = self._config.active_config['motor_current']['adc_channel_index']
        raw_motor_current_meas = self._adc.get_4to20ma_from_channel(motor_current_channel_index)
        motor_current_scale = self._config.active_config['motor_current']['scale']
        motor_current_offset = self._config.active_config['motor_current']['offset']
        self.motor_current_amps = motor_current_scale * raw_motor_current_meas + motor_current_offset
        # Water Pressure (PSI)    
        self.water_pressure_psi = None
        water_pressure_channel_index = self._config.active_config['water_pressure']['adc_channel_index']
        raw_water_pressure_meas = self._adc.get_4to20ma_from_channel(water_pressure_channel_index)
        water_pressure_scale = self._config.active_config['water_pressure']['scale']
        water_pressure_offset = self._config.active_config['water_pressure']['offset']
        self.water_pressure_psi = water_pressure_scale * raw_water_pressure_meas + water_pressure_offset
        # Run Time
        self.pump_run_time_secs = 0
        if self._pump_start_time != None:
             self.pump_run_time_secs = (datetime.datetime.now() - self._pump_start_time).total_seconds()
             
        # Print it
        self._logger.write(self.LOG_KEY, f"Motor Current: {self.motor_current_amps:.2f} A", logger.MessageLevel.INFO)
        self._logger.write(self.LOG_KEY, f"Water Pressure: {self.water_pressure_psi:.0f} PSI", logger.MessageLevel.INFO)
        self._logger.write(self.LOG_KEY, f"Pump Run Time: {self.pump_run_time_secs:.0f} secs", logger.MessageLevel.INFO)        
        # Ship it
        if self._last_mqtt_publish == None or (datetime.datetime.now() - self._last_mqtt_publish).total_seconds() > self._mqtt_transmit_time_sec:
            self._last_mqtt_publish = datetime.datetime.now()
            self._mqtt_client.publish(self._config.active_config['publish']['motor_current'], self.motor_current_amps)
            self._mqtt_client.publish(self._config.active_config['publish']['water_pressure'], self.water_pressure_psi)
            self._mqtt_client.publish(self._config.active_config['publish']['pump_run_time_secs'], self.water_pressure_psi)
    
    def update_pump_state(self, new_state):
        '''Updated from the main state machine and used to monitor the pump'''
        if new_state == PumpBoxService.PUMP_STATE_INIT:
            self._pump_start_time = None
        elif new_state == PumpBoxService.PUMP_STATE_IDLE:
            self._pump_start_time = None
        elif new_state == PumpBoxService.PUMP_STATE_STARTING:
            self._pump_start_time = datetime.datetime.now()
        elif new_state == PumpBoxService.PUMP_STATE_OPENING_VALVE:
            pass
        elif new_state == PumpBoxService.PUMP_STATE_PUMPING:
            pass
        elif new_state == PumpBoxService.PUMP_STATE_STOPPING:
            pass
        elif new_state == PumpBoxService.PUMP_STATE_CLOSING_VALVE:
            pass
        elif new_state == PumpBoxService.PUMP_STATE_STOPPED:
            pass
        else:
            pass
                        
class PumpBoxService:
    
    '''Class Constants'''
    LOG_KEY = 'service'
    
    # Pump State
    PUMP_STATE_INIT             = 0
    PUMP_STATE_IDLE             = 1
    PUMP_STATE_STARTING         = 2
    PUMP_STATE_OPENING_VALVE    = 3
    PUMP_STATE_PUMPING          = 4
    PUMP_STATE_STOPPING         = 5
    PUMP_STATE_CLOSING_VALVE    = 6
    PUMP_STATE_STOPPED          = 7
    _pump_state = PUMP_STATE_INIT

    # Remote Control Request
    PUMP_REQUEST_NONE = 0
    PUMP_REQUEST_ON = 1
    PUMP_REQUEST_OFF = 2
    _pump_request = PUMP_REQUEST_NONE
    
    '''Private Class Members'''
    _mqtt_client = None
    _run_main_loop = True
    _last_loop_start = None
    _last_pump_start = None
    _analog_inputs = None
    _mcp_portexpander = None
    
    def __init__(self, app_logger, app_config) -> None:
        '''Initialize the PumpBoxService object - fast init, _can_ fail'''
        # Logger and config
        self._logger = app_logger
        self._config = app_config
        
        
        
        # Create and Start Mqtt Client
        self._logger.write(self.LOG_KEY, "Initializing MQTT Client...", logger.MessageLevel.INFO)
        self._mqtt_client = mqtt_client_pubsub.MqttClient(app_config, 
                                                app_logger, 
                                                self._on_new_message, 
                                                self._on_publish_message)
        self._mqtt_client.start()
        self._mqtt_client.subscribe(self._config.active_config['subscribe']['pump_control'])
        
        # Create Port Expander
        self._mcp_portexpander = mcp23017.MCP23017()
        
        # Ball Valve 
        self._ball_valve = ball_valve.BallValve(self._mcp_portexpander,
                                                self._config.active_config['ball_valve']['open_pin'],
                                                self._config.active_config['ball_valve']['close_pin'],
                                                self._config.active_config['ball_valve']['direction_pin'],
                                                self._config.active_config['ball_valve']['enable_pin'],
                                                self._config.active_config['ball_valve']['transition_time_secs'],
                                                state_change_callback=self._ball_valve_state_change)
        
        # Pump Monitor
        self._pump_monitor = PumpMonitor(app_logger, app_config, self._mqtt_client)
        
        
                
    ''' Run Main Loop '''
    def run(self) -> ServiceExitError:
        
        # Main loop
        while self._run_main_loop:
            self._last_loop_start = datetime.datetime.now()
            # Process the ball valve state machine
            self._ball_valve.process()
            # Update Monitor
            self._pump_monitor.update()
            # Main State Machine
            # PUMP_STATE_INIT - Initialize vars and state machine
            if self._pump_state == self.PUMP_STATE_INIT:
                self._pump_request = self.PUMP_REQUEST_NONE
                self._last_pump_start = None
                self._ball_valve.request_close()
                self._change_state(self.PUMP_STATE_IDLE)
                pass
            
            # PUMP_STATE_IDLE - check for remote requests    
            elif self._pump_state == self.PUMP_STATE_IDLE:
                if self._pump_request == self.PUMP_REQUEST_ON:
                    self._pump_request = self.PUMP_REQUEST_NONE
                    self._change_state(self.PUMP_STATE_STARTING)
                pass
            
            # PUMP_STATE_STARTING - Open the ball valve        
            elif self._pump_state == self.PUMP_STATE_STARTING:
                self._ball_valve.request_open()
                self._change_state(self.PUMP_STATE_OPENING_VALVE)
                pass
            
            # PUMP_STATE_OPENING_VALVE - Awaiting valve open
            elif self._pump_state == self.PUMP_STATE_OPENING_VALVE:
                # If valve is open, start motor and move to next state
                if self._ball_valve.is_open():
                    self._change_state(self.PUMP_STATE_PUMPING)
                    # TODO Start motor
                    self._last_pump_start = datetime.datetime.now()
                elif self._ball_valve.is_timedout():
                    self._change_state(self.PUMP_STATE_INIT)
                    # TODO Publish error        
            
            elif self._pump_state == self.PUMP_STATE_PUMPING:
                if self._pump_request == self.PUMP_REQUEST_OFF:
                    self._pump_request = self.PUMP_REQUEST_NONE
                    self._change_state(self.PUMP_STATE_STOPPING)
                    # TODO Stop motor
                    self._ball_valve.request_close()
                pass
            
            # PUMP_STATE_STOPPING - Close the ball valve
            elif self._pump_state == self.PUMP_STATE_STOPPING:
                # If valve is open, start motor and move to next state
                if self._ball_valve.is_closed():
                    self._change_state(self.PUMP_STATE_STOPPED)
                elif self._ball_valve.is_timedout():
                    self._change_state(self.PUMP_STATE_INIT)
                    # TODO Publish error   
                    
            # PUMP_STATE_STOPPED - Ball valve closed and motor stopped, return to idle
            elif self._pump_state == self.PUMP_STATE_STOPPED:
                self._change_state(self.PUMP_STATE_IDLE)
                
            else:
                # Unknown state
                self._change_state(self.PUMP_STATE_INIT)

            # Sleep to prevent CPU thrashing     
            time.sleep(0.1)
            
    def _change_state(self, new_state):
        '''Change the state of the pump'''
        self._pump_state = new_state
        self._logger.write(self.LOG_KEY, f"New state: {self._system_state_to_str(self._pump_state)}", logger.MessageLevel.INFO)
        self._pump_monitor.update_pump_state(self._pump_state)
        sys_state_topic = self._config.active_config['publish']['system_state']
        self._mqtt_client.publish(sys_state_topic, self._system_state_to_str(self._pump_state))
        
    def _on_new_message(self, topic, message) -> None:
        '''Received a new message from the MQTT Broker'''
        self._logger.write(self.LOG_KEY, f"New message: {topic}->[{message}]", logger.MessageLevel.INFO)
        # Parse the message
        if topic == self._format_topic(self._config.active_config['subscribe']['pump_control']):
            self._logger.write(self.LOG_KEY, f"Pump Control Updated: [{message}]", logger.MessageLevel.INFO)
            if message == b'ON':
                self._pump_request = self.PUMP_REQUEST_ON
            elif message == b'OFF':
                self._pump_request = self.PUMP_REQUEST_OFF
            
    def _on_publish_message(self, topic, message) -> None:
        '''Published a new message to the MQTT Broker'''
        self._logger.write(self.LOG_KEY, f"Publishing message: {topic}->[{message}]", logger.MessageLevel.INFO)

    def _format_topic(self, topic) -> str:
        '''Format the topic with the base topic'''
        return f"{self._config.active_config['base_topic']}/{topic}"  
    
    def _ball_valve_state_change(self, valve_state, new_state, context) -> None:
        '''Callback for when the ball valve state changes'''
        ball_valve_state_str = f"Ball Valve State Changed [{new_state}]: {context}"
        self._logger.write(self.LOG_KEY, ball_valve_state_str, logger.MessageLevel.INFO)
        valve_state_topic = self._config.active_config['publish']['valve_state']
        self._mqtt_client.publish(valve_state_topic, ball_valve_state_str)
    
    def _system_state_to_str(self, state) -> str:
        if state == self.PUMP_STATE_INIT:
            return "INIT"
        elif state == self.PUMP_STATE_IDLE:
            return "IDLE"
        elif state == self.PUMP_STATE_STARTING:
            return "STARTING"
        elif state == self.PUMP_STATE_OPENING_VALVE:
            return "OPENING VALVE"
        elif state == self.PUMP_STATE_PUMPING:
            return "PUMPING"
        elif state == self.PUMP_STATE_STOPPING:
            return "STOPPING"
        elif state == self.PUMP_STATE_CLOSING_VALVE:
            return "CLOSING VALVE"
        elif state == self.PUMP_STATE_STOPPED:
            return "STOPPED"
        else:
            raise Exception("Unknown State")
            
'''Measure and print 8 channels'''
if __name__ == '__main__':
    
    # Main variables
    log_key = "main"
    config_file = "default_pumpbox_config.json"
    
    # Initialize Main object
    app_logger = logger.Logger()
    app_logger.write(log_key, "Initializing PumpBox Service...", logger.MessageLevel.INFO)
    
    # Load or create default config
    app_logger.write(log_key, "Loading config...", logger.MessageLevel.INFO)
    app_config = pumpbox_config.ConfigManager(config_file, app_logger)
    
    # Create service object and run it
    app_logger.write(log_key, "Running Pump Box Service...", logger.MessageLevel.INFO)
    pumpbox = PumpBoxService(app_logger, app_config)
    exit_msg = pumpbox.run()
    
    # Service exit, print message
    if exit_msg.error:
        app_logger.write(log_key, "Service exited with error: " + str(exit_msg.error_message), logger.MessageLevel.ERROR)
    