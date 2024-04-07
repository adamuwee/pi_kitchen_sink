import mcp23017
import datetime

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
    def __init(self, state : int, transition_time_remaining : int):
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
    
    # Private Members
    _state = STATE_INIT
    _transition_request = TRANSITION_NONE
    _state_change_callback = None
    _timer = None
    
    '''Initialize Ball Valve Object - fast init'''
    def __init__(self, 
                 direction_pin, 
                 enable_pin, 
                 open_pin, 
                 close_pin, 
                 transition_timeout_secs=10,
                 state_change_callback=None):
        
        # Init vars
        self._direction_pin = direction_pin
        self._enable_pin = enable_pin
        self._open_pin = open_pin
        self._transition_timeout_secsclose_pin = close_pin
        self._transition_timeout_secs = transition_timeout_secs
        self._transition_request = self.TRANSITION_NONE
        self._state_change_callback = state_change_callback
        self._timer = None
        
        # Set init state for valve
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
         
    '''Public API: This should be called in a loop to process the ball valve state and transition timeouts'''
    def process(self):
        # Check if the ball valve is transitioning and if the transition has timed out
        # Code to check the transition state and timeout goes here
        
        # Big ol' State Machine
        
        # STATE_INIT 
        if self._state == self.STATE_INIT:
            # Initialize variables
            self._timer = None      
            # Set default pin states
            self._change_state(self.STATE_IDLE)
            pass
        
        # STATE_IDLE            
        elif self._state == self.STATE_IDLE:
            if self._transition_request == self.TRANSITION_NONE:
                pass # Do nothing - no request to change
            elif self._transition_request == self.TRANSITION_OPEN:
                self._transition_request = self.TRANSITION_NONE
                self._change_state(self.STATE_START_OPENING)
            elif self._transition_request == self.TRANSITION_CLOSE:
                self._transition_request = self.TRANSITION_NONE
                self._change_state(self.STATE_START_CLOSING)
            pass
        
        # TODO: STATE_START_OPENING
        elif self._state == self.STATE_START_OPENING:
            # Set the Pins to Open Valve
            # Start the timer
            self._timer = TimeoutTimer(self._transition_timeout_secs)
            self._change_state(self.STATE_OPENING)
            pass
        
        # TODO: STATE_OPENING
        elif self._state == self.STATE_OPENING:
            # Check the pins for the OPEN state
            # Test the timer
            if self._timer.has_timed_out():
                # Error - timeout occurred
                # return to idle state
                pass
            pass
            
        # TODO: STATE_OPEN
        elif self._state == self.STATE_OPEN:
            # Set drive pins to idle
            pass
        
        # TODO: STATE_START_CLOSING
        elif self._state == self.STATE_START_CLOSING:
            # Set the Pins to Close Valve
            # Start the timer
            self._timer = TimeoutTimer(self._transition_timeout_secs)
            self._change_state(self.STATE_CLOSING)
            pass
        
        # TODO: STATE_CLOSING
        elif self._state == self.STATE_CLOSING:
            # Check the pins for the CLOSED state
            # Test the timer
            if self._timer.has_timed_out():
                # Error - timeout occurred
                # return to idle state
                pass
            pass
        # TODO: STATE_CLOSED    
        elif self._state == self.STATE_CLOSED:
            pass
        
        # Error - Unknown state, return to init
        else:
            self._change_state(self.STATE_INIT)
            # TODO: report error
            pass
    
    '''Change the state of the ball valve and call the state change callback if it is set'''
    def _change_state(self, new_state):
        self._state = new_state
        if self._state_change_callback != None:
            self._state_change_callback(self._state, new_state)
            
    '''TODO: Read the state of the open input pin and return True if the ball valve is open, False otherwise'''
    '''TRANSITION_NONE, TRANSITION_OPEN, or TRANSITION_CLOSE'''
    def _get_valve_state(self) -> int:
        pass
                    
    '''TODO: Change the drive pin state using the TRANSITION values'''
    '''TRANSITION_NONE, TRANSITION_OPEN, or TRANSITION_CLOSE'''
    def _set_drive_state(self, transition : int):
        if transition == self.TRANSITION_NONE:
            # Code to set the drive pin to stop the valve goes here
            pass
        elif transition == self.TRANSITION_OPEN:
            # Code to set the drive pin to open the valve goes here
            pass
        elif transition == self.TRANSITION_CLOSE:
            # Code to set the drive pin to close the valve goes here
            pass
        else:
            # Error - unknown transition state
            pass    