import mcp23017
import datetime
import time

'''Measures the time remaining in a state transition and indicates if the transition has timed out'''
class TimeoutTimer:
    def __init__(self, timeout_secs):
        self.timeout_secs = timeout_secs
        self.start_time = datetime.datetime.now()
    
    def has_timed_out(self):
        current_time = datetime.datetime.now()
        elapsed_time = current_time - self.start_time
        return elapsed_time.total_seconds() >= self.timeout_secs
    
    def time_remaining_seconds(self) -> int:
        current_time = datetime.datetime.now()
        elapsed_time = current_time - self.start_time
        remaining_time = self.timeout_secs - elapsed_time.total_seconds()
        return remaining_time
    
'''Returns true / false if the transition request is valid and an error if invalid'''
class TransitionResponse:
    def __init__(self, request_okay : bool, err_response : str):
        self.request_okay = request_okay
        self.response = err_response

'''Returned to the caller to indicate the state of the valve including the time remaining of a transition state'''
class ValveState:
    def __init__(self, state : int, transition_time_remaining : int):
        self.state = state
        self.transition_time_remaining = transition_time_remaining

'''Represents a Ball Valve with the ability to open and close the valve'''
class BallValve:
    
    # Private Constants - States
    STATE_INIT = 0
    STATE_IDLE = 1
    STATE_START_OPENING = 2
    STATE_OPENING = 3
    STATE_OPEN = 4
    STATE_START_CLOSING = 5
    STATE_CLOSING = 6
    STATE_CLOSED = 7
    
    # Private Constants - Transitions
    TRANSITION_NONE = 0
    TRANSITION_OPEN = 1
    TRANSITION_CLOSE = 2
    
    # Private Constants - Valve Position
    VALVE_POSITION_UNKNOWN = 0
    VALVE_POSITION_OPEN = 1
    VALVE_POSITION_CLOSE = 2
    
    # Private Members
    _state = STATE_INIT
    _transition_request = TRANSITION_NONE
    _state_change_callback = None
    _timer = None
    _mcp_io = None
    _timed_out = False
    _verbose_status_msg = False
    
    '''Initialize Ball Valve Object - fast init'''
    def __init__(self,
                 valve_name : str, 
                 mcp_io : mcp23017.MCP23017,
                 din_open_pin, 
                 din_close_pin,
                 dout_direction_pin, 
                 dout_enable_pin, 
                 transition_timeout_secs=20,
                 state_change_callback=None,
                 valve_position_change_callback=None):
        
        # Init vars
        self._mcp_io = mcp_io
        
        self._open_pin = din_open_pin
        self._close_pin = din_close_pin
        self._direction_pin = dout_direction_pin
        self._enable_pin = dout_enable_pin
        self.valve_name = valve_name

        self._transition_timeout_secs = transition_timeout_secs
        self._state_change_callback = state_change_callback
        self._valve_position_change_callback = valve_position_change_callback
        
        self._transition_request = self.TRANSITION_NONE
        self._state = self.STATE_INIT
    
    '''Public API: Request to OPEN the Ball Valve'''
    def request_open(self) -> TransitionResponse:
        if self._state == self.STATE_IDLE:
            self._transition_request = self.TRANSITION_OPEN
            return TransitionResponse(True, "")
        else:
            # Error - invalid state for open request
            return TransitionResponse(False, "Ball Valve is not in the IDLE state")
    
    '''Public API: Request to CLOSE the Ball Valve'''
    def request_close(self) -> TransitionResponse:
        if self._state == self.STATE_IDLE:
            self._transition_request = self.TRANSITION_CLOSE
            return TransitionResponse(True, "")
        else:
            # Error - invalid state for open request
            return TransitionResponse(False, "Ball Valve is not in the IDLE state")
    
    '''Public API: Get Valve State'''
    def get_valve_state(self) -> ValveState:
        current_state = self._state
        time_remaining = 0
        if self._timer != None:
            time_remaining = self._timer.time_remaining_seconds()  
        return ValveState(current_state, time_remaining)
    
    def is_open(self) -> bool:
        return self.get_valve_position() == self.VALVE_POSITION_OPEN
    
    def is_closed(self) -> bool:
        return self.get_valve_position() == self.VALVE_POSITION_CLOSE
    
    def is_timedout(self) -> bool:
        return self._timed_out

    def is_in_transition_state(self) -> bool:
        '''Return if the ball valve is transition from one state to another'''
        return self.current_state in (BallValve.STATE_START_OPENING,
                                      BallValve.STATE_OPENING,
                                      BallValve.STATE_START_CLOSING,
                                      BallValve.STATE_CLOSING)
             
    '''Public API: This should be called in a loop to process the ball valve state and transition timeouts'''
    def process(self):
        # Big ol' State Machine
        # STATE_INIT 
        if self._state == self.STATE_INIT:
            self._timer = None      
            self._change_state(self.STATE_IDLE, "Initialization complete.")
            pass
        
        # STATE_IDLE            
        elif self._state == self.STATE_IDLE:
            if self._transition_request == self.TRANSITION_OPEN:
                self._change_state(self.STATE_START_OPENING, "Start opening.")
            elif self._transition_request == self.TRANSITION_CLOSE:
                self._change_state(self.STATE_START_CLOSING, "Start closing")
            self._transition_request = self.TRANSITION_NONE
            pass
        
        # STATE_START_OPENING
        elif self._state == self.STATE_START_OPENING:
            self._set_drive_state(self.TRANSITION_OPEN)
            self._timer = TimeoutTimer(self._transition_timeout_secs)
            self._change_state(self.STATE_OPENING, f"Valve Opening\tTimeout: {self._transition_timeout_secs} seconds")
            self._timed_out = False
            pass
        
        # STATE_OPENING
        elif self._state == self.STATE_OPENING:
            valve_position = self.get_valve_position()
            if valve_position == self.VALVE_POSITION_OPEN:
                self._change_state(self.STATE_OPEN, f"Valve Opened - moving to OPEN state.")  
                self._timed_out = False              
            elif self._timer.has_timed_out():
                self._change_state(self.STATE_INIT, f"Valve Opening Timeout. Returning to INIT state.")   
                self._timed_out = True 
            else:
                self._change_state(self.STATE_OPENING, f"Valve Opening - {self._timer.time_remaining_seconds():.1f} seconds remain")  
            pass
            
        # STATE_OPEN
        elif self._state == self.STATE_OPEN:
            self._set_drive_state(self.TRANSITION_NONE)
            self._change_state(self.STATE_IDLE, "Valve Open. Returning to IDLE state.")
            pass
        
        # STATE_START_CLOSING
        elif self._state == self.STATE_START_CLOSING:
            self._set_drive_state(self.TRANSITION_CLOSE)
            self._timer = TimeoutTimer(self._transition_timeout_secs)
            self._change_state(self.STATE_CLOSING, f"Valve Closing\tTimeout: {self._transition_timeout_secs} seconds")
            pass
        
        # STATE_CLOSING
        elif self._state == self.STATE_CLOSING:
            valve_position = self.get_valve_position()
            if valve_position == self.VALVE_POSITION_CLOSE:
                self._change_state(self.STATE_CLOSED, f"Valve Closed. Returning to IDLE state.")  
                self._timed_out = False 
            elif self._timer.has_timed_out():
                self._change_state(self.STATE_INIT, f"Valve Closiing Timeout. Returning to INIT state.")  
                self._timed_out = True 
            else:
                self._change_state(self.STATE_CLOSING, f"Valve Closing - {self._timer.time_remaining_seconds():.1f} seconds remain")  
            pass
        
        # STATE_CLOSED    
        elif self._state == self.STATE_CLOSED:
            self._timed_out = False
            self._set_drive_state(self.TRANSITION_NONE)
            self._change_state(self.STATE_IDLE, "Valve Closed")
            pass
        
        # Error - Unknown state, return to init
        else:
            self._change_state(self.STATE_INIT, f'Unknown state: [{self._state}]\tReturning to INIT state.')
            pass
    
    '''Change the state of the ball valve and call the state change callback if it is set'''
    def _change_state(self, new_state, context:str = "") -> None:
        self._state = new_state
        self._emit_state_change_event(new_state, context)
            
    '''Read the state of the open input pin and return True if the ball valve is open, False otherwise'''
    '''VALVE_POSITION_UNKNOWN, VALVE_POSITION_OPEN, or VALVE_POSITION_CLOSE'''
    def get_valve_position(self) -> int:
        valve_position = self.VALVE_POSITION_UNKNOWN
        valve_position_string = "Unknown"
        open_pin_state = self._mcp_io.read_kitchensink_dinput(self._open_pin)
        close_pin_state = self._mcp_io.read_kitchensink_dinput(self._close_pin)
        if (open_pin_state) and (not close_pin_state):
            valve_position = self.VALVE_POSITION_CLOSE
            valve_position_string = "Closed"
        elif (not open_pin_state) and (close_pin_state):
            valve_position = self.VALVE_POSITION_OPEN
            valve_position_string = "Open"
        self._emit_valve_position_change_callback(valve_position_string)
        return valve_position
                      
    '''Change the drive pin state using the TRANSITION values'''
    '''TRANSITION_NONE, TRANSITION_OPEN, or TRANSITION_CLOSE'''
    def _set_drive_state(self, transition : int):
        if transition == self.TRANSITION_NONE:
            self._mcp_io.write_kitchensink_doutput(self._direction_pin, False)
            self._mcp_io.write_kitchensink_doutput(self._enable_pin, False)
        elif transition == self.TRANSITION_OPEN:
            self._mcp_io.write_kitchensink_doutput(self._direction_pin, False)
            self._mcp_io.write_kitchensink_doutput(self._enable_pin, True)
        elif transition == self.TRANSITION_CLOSE:
            self._mcp_io.write_kitchensink_doutput(self._direction_pin, True)
            self._mcp_io.write_kitchensink_doutput(self._enable_pin, True)
        else:
            raise Exception("_set_drive_state:: Unknown drive state transition")
        pass
    
    '''Emit a state change event to the caller if the state change callback is set'''
    def _emit_state_change_event(self, new_state:int, err_message : str):
        if self._state_change_callback != None:
            self._state_change_callback(self,
                                        self._state, 
                                        self._state_to_string(new_state), 
                                        err_message) 
            
    def _state_to_string(self, state) -> str:
        if state == BallValve.STATE_INIT:
            return "Init"
        elif state == BallValve.STATE_IDLE:
            return "Idle"
        elif state == BallValve.STATE_START_OPENING:
            return "Start Opening"
        elif state == BallValve.STATE_OPENING:
            return "Opening"
        elif state == BallValve.STATE_OPEN:
            return "Open"
        elif state == BallValve.STATE_START_CLOSING:
            return "Start Closing"
        elif state == BallValve.STATE_CLOSING:
            return "Closing"
        elif state == BallValve.STATE_CLOSED:
            return "Closed"
        else:
            return "Unknown Valve State"
    
    def _emit_valve_position_change_callback(self, valve_state_str:str): 
        if self._valve_position_change_callback != None:
            self._valve_position_change_callback(self, valve_state_str)
            

def _state_change_callback(self, new_state:int, context:str):
    print(f"State Change: [{new_state}]\tContext: {context}")
            
'''Component Test'''
if __name__ == '__main__':
    
    valve_channel = 0   # Valid Range: 0-3
    
    if valve_channel < 0 or valve_channel > 3:
        raise Exception("Invalid Valve Channel")
       
    # I/O Port Expander
    mcp_device = mcp23017.MCP23017(0x21)
    
    # Pin assignments
    pin_assignments = ([    [0, 1, 8, 9], 
                            [2, 3, 10, 11], 
                            [4, 5, 12, 13], 
                            [6, 7, 14, 15]])
    
    open_pin        = pin_assignments[valve_channel][0] # Green
    close_pin       = pin_assignments[valve_channel][1] # Red
    direction_pin   = pin_assignments[valve_channel][2] # Yellow
    enable_pin      = pin_assignments[valve_channel][3] # Blue
          
    ball_valve = BallValve(mcp_device,
                           "Test Valve", 
                           open_pin, 
                           close_pin, 
                           direction_pin, 
                           enable_pin, 
                           state_change_callback=_state_change_callback)
    
    # Test List
    test_read_valve_state = False
    test_toggle_open_close_state = True
    
    # Read and print the position of the valve
    if test_read_valve_state:
        test_duration_seconds = 60
        start_time = datetime.datetime.now()
        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        while elapsed_time < test_duration_seconds:
            valve_position = ball_valve.get_valve_position()
            print(f"Valve State Ch. # {valve_channel+1}: 0b{valve_position:02b}\tTiming: {elapsed_time:.0f} of {test_duration_seconds}s")
            time.sleep(1.0)
            elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
    
    # Toggle the valve position
    if test_toggle_open_close_state:
        
        # Open Valve
        test_timeout_seconds = 20
        start_time = datetime.datetime.now()
        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        print("Opening valve...")
        ball_valve.process()
        ball_valve.request_open()
        valve_position = ball_valve.VALVE_POSITION_UNKNOWN
        while elapsed_time < test_timeout_seconds and valve_position is not ball_valve.VALVE_POSITION_OPEN:
            ball_valve.process()
            valve_position = ball_valve.get_valve_position()
            print(f"Valve State Ch. # {valve_channel+1}: 0b{valve_position:02b}\tTiming: {elapsed_time:.0f} of {test_timeout_seconds}s")
            time.sleep(1.0)
            elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        
        # Run out the state machine
        for proc_index in range(10):
            ball_valve.process()
            time.sleep(0.1)
            
        # Close Valve
        test_timeout_seconds = 20
        start_time = datetime.datetime.now()
        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        print("Closing valve...")

        ball_valve.request_close()
        valve_position = ball_valve.VALVE_POSITION_UNKNOWN
        while elapsed_time < test_timeout_seconds and valve_position is not ball_valve.VALVE_POSITION_CLOSE:
            ball_valve.process()
            valve_position = ball_valve.get_valve_position()
            print(f"Valve State Ch. # {valve_channel+1}: 0b{valve_position:02b}\tTiming: {elapsed_time:.0f} of {test_timeout_seconds}s")
            time.sleep(1.0)
            elapsed_time = (datetime.datetime.now() - start_time).total_seconds()        