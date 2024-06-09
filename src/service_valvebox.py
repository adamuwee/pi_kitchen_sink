import time
import datetime
import queue

import logger
import valvebox_config
import mqtt_client_pubsub
import mcp23017

import ball_valve
import din_counter
import simple_data_store

class ServiceExitError:
    def __init__(self, error = True, error_message = "") -> None:
        self.error = error
        self.error_message = error_message

class ValveQueueCommand:
    # Class Constants
    UNKNOWN = 0
    OPEN = 1
    CLOSE = 2
    
    # Class Members
    name = ""
    requested_state = UNKNOWN
    
    def __init__(self, name, requested_state) -> None:
        self.name = name
        self.requested_state = requested_state
        
    def __str__(self):
     return f"{self.name}: {self.requested_state}"
                        
class ValveBoxService:
    
    '''Class Constants'''
    LOG_KEY = 'service'
        
    '''Private Class Members'''
    _mqtt_client = None
    _run_main_loop = True
    _last_loop_start = None
    _last_pump_start = None
    _mcp_portexpander = None
    _ignore_first_mqtt_remote_control = True
    _verbose_valve_state_message = True
    _ball_valves = list()
    _command_queue = None
    
    def __init__(self, app_logger, app_config) -> None:
        '''Initialize the ValveBoxService object - fast init, _can_ fail'''
        # Logger and config
        self._logger = app_logger
        self._config = app_config
        self._command_queue = queue.Queue()
        
        # Create a simple data store for the counter
        self.data_store = simple_data_store.DiskDataStore("valve_box_data_store.json")
        
        # Create Port Expander
        self._mcp_portexpander = mcp23017.MCP23017()
                
        # Create and Start Mqtt Client
        self._logger.write(self.LOG_KEY, "Initializing MQTT Client...", logger.MessageLevel.INFO)
        self._mqtt_client = mqtt_client_pubsub.MqttClient(app_config, 
                                                app_logger, 
                                                self._on_new_message, 
                                                self._on_publish_message)
        self._mqtt_client.start()
        
        # Subscribe the Valve Box Control Topics
        # Create Ball Valve Objects
        for index in range(valvebox_config.ConfigManager.NUMBER_OF_VALVES):
            valve_topic = f'valve_{index + 1}'
            # MQTT Subscription topics
            self._mqtt_client.subscribe(self._config.active_config[valve_topic]['subscribe']['valve_control'])
            # Create list of ball valves
            self._ball_valves.append(ball_valve.BallValve(  valve_topic,  
                                                            self._mcp_portexpander,
                                                            self._config.active_config[valve_topic]['open_pin'],
                                                            self._config.active_config[valve_topic]['close_pin'],
                                                            self._config.active_config[valve_topic]['direction_pin'],
                                                            self._config.active_config[valve_topic]['enable_pin'],
                                                            self._config.active_config[valve_topic]['transition_time_secs'],
                                                            state_change_callback=self._ball_valve_state_change,
                                                            valve_position_change_callback=self._ball_valve_position_change))
            
        # Flow Counter
        self.counter = din_counter.DinCounter()
        self._last_counter_value = None
                        
    ''' Run Main Loop '''
    def run(self) -> ServiceExitError:
        
        # Main loop
        while self._run_main_loop:
            self._last_loop_start = datetime.datetime.now()
            
            # Update Flow Counter and MQTT Topic
            self._update_flow_counter()
        
            # Process the ball valve state machines
            for ball_valve in self._ball_valves:
                ball_valve.process()
            
            # Check for new requests on the subscribed channels
            while self._command_queue.qsize() > 0:
                command = self._command_queue.get()
                self._logger.write(self.LOG_KEY, f"New valve command: {command}", logger.MessageLevel.INFO)
                # Update the ball valve
                for ball_valve in self._ball_valves:
                    if (ball_valve.valve_name == command.name):
                        if ball_valve.is_in_transition_state():
                            '''Block if the ball valve is transitioning to another state'''
                            valve_in_transition_err_string = f"Command Blocked. {ball_valve.valve_name} is in transition."
                            self._logger.write(self.LOG_KEY, valve_in_transition_err_string, logger.MessageLevel.ERROR)
                            valve_box_error_topic = self._config.active_config['publish']['system_error']
                            self._mqtt_client.publish(valve_box_error_topic, valve_in_transition_err_string)
                        else:
                            if command.requested_state == ValveQueueCommand.OPEN:
                                ball_valve.request_open()
                            elif command.requested_state == ValveQueueCommand.CLOSE:
                                ball_valve.request_close()
                            else:
                                self._logger.write(self.LOG_KEY, f"Unknown valve command received: {command}", logger.MessageLevel.ERROR)    
                
            # Sleep to prevent CPU thrashing    
            time.sleep(0.2)
            
    def _update_flow_counter(self) -> None:
        '''Syncs flow counter output and what was written to disk last'''
        FLOW_COUNTER_TAG = "FLOW_COUNTER"
        flag_send_flow_counter_mqtt = False
        
        if (self._last_counter_value == None):
            '''First time checking counter. Runs onces at startup. Set last counter value from disk'''
            (value, timestamp) = self.data_store.read(FLOW_COUNTER_TAG)
            if (value == None):
                '''File not initiatied - write 0 to disk'''
                self._last_counter_value = 0
                self.data_store.write(FLOW_COUNTER_TAG, self._last_counter_value) 
            else:
                self._last_counter_value = value  
            self.counter.set_count_A(self._last_counter_value) 
            flag_send_flow_counter_mqtt = True
        
        new_counter_value = self.counter.get_count_A()    
        if (self._last_counter_value != new_counter_value):
            # Update last and publish to mqtt
            self._last_counter_value = new_counter_value
            self.data_store.write(FLOW_COUNTER_TAG, self._last_counter_value) 
            flag_send_flow_counter_mqtt = True
            
        if flag_send_flow_counter_mqtt:
            self._mqtt_client.publish(self._config.active_config['publish']['flow_counter'], 
                                        self._last_counter_value)  
                
    def _on_new_message(self, topic, message) -> None:
        '''Received a new message from the MQTT Broker'''
        self._logger.write(self.LOG_KEY, f"New message: {topic}->[{message}]", logger.MessageLevel.INFO)
        # Parse the message
        # First Scan - Valve Control (Hacked for now)
        for (valve_key, valve_conf) in self._config.get_valve_configs().items():
            valve_cmd_topic = self._config.active_config['base_topic'] + "/" + valve_conf['subscribe']['valve_control']
            if topic == valve_cmd_topic:
                if message == b'OPEN':
                    self._command_queue.put(ValveQueueCommand(valve_key, ValveQueueCommand.OPEN))
                elif message == b'CLOSE':
                    self._command_queue.put(ValveQueueCommand(valve_key, ValveQueueCommand.CLOSE))               

            
    def _on_publish_message(self, topic, message) -> None:
        '''Published a new message to the MQTT Broker'''
        #self._logger.write(self.LOG_KEY, f"Publishing message: {topic}->[{message}]", logger.MessageLevel.INFO)
        pass
    
    def _format_topic(self, topic) -> str:
        '''Format the topic with the base topic'''
        return f"{self._config.active_config['base_topic']}/{topic}"  
    
    def _ball_valve_state_change(self, valve_obj, valve_state, new_state, context) -> None:
        '''Callback for when the ball valve state changes'''
        # TODO: Figure out the ball valve name 
        ball_valve_state_str = new_state
        if self._verbose_valve_state_message:
            ball_valve_state_str = f"{valve_obj.valve_name} State: [{new_state}]: {context}"
        self._logger.write(self.LOG_KEY, ball_valve_state_str, logger.MessageLevel.INFO)
        valve_state_topic = self._config.active_config[valve_obj.valve_name]['publish']['state']
        self._mqtt_client.publish(valve_state_topic, context)
    
    def _ball_valve_position_change(self, valve_obj, valve_position_str) -> None:
        self._logger.write(self.LOG_KEY, f"{valve_obj.valve_name} Position: {valve_position_str}", logger.MessageLevel.INFO)
        valve_position_topic = self._config.active_config[valve_obj.valve_name]['publish']['position']
        self._mqtt_client.publish(valve_position_topic, valve_position_str)
                                
'''Main Service App'''
if __name__ == '__main__':
    
    # Main variables
    log_key = "main"
    config_file = "default_valvebox_config.json"
    
    # Initialize Main object
    app_logger = logger.Logger()
    app_logger.write(log_key, "Initializing ValveBox Service...", logger.MessageLevel.INFO)
    
    # Load or create default config
    app_logger.write(log_key, "Loading config...", logger.MessageLevel.INFO)
    app_config = valvebox_config.ConfigManager(config_file, app_logger)
    
    # Create service object and run it
    app_logger.write(log_key, "Running ValveBox Service...", logger.MessageLevel.INFO)
    valvebox = ValveBoxService(app_logger, app_config)
    exit_msg = valvebox.run()
    
    # Service exit, print message
    if exit_msg.error:
        app_logger.write(log_key, "Service exited with error: " + str(exit_msg.error_message), logger.MessageLevel.ERROR)
    