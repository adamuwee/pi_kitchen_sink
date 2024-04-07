import mcp23017
import datetime

class TimeoutTimer:
    def __init__(self, timeout_secs):
        self.timeout_secs = timeout_secs
        self.start_time = datetime.datetime.now()
    
    def has_timed_out(self):
        current_time = datetime.datetime.now()
        elapsed_time = current_time - self.start_time
        return elapsed_time.total_seconds() >= self.timeout_secs

class TransitionResponse:
    def __init__(self, request_okay, response):
        self.request_okay = request_okay
        self.response = response

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

    '''This should be called in a loop to process the ball valve state and transition timeouts'''
    def process(self):
        # Check if the ball valve is transitioning and if the transition has timed out
        # Code to check the transition state and timeout goes here
        
        # Big ol' State Machine
        if self._state == self.STATE_INIT:
            # Initialize variables
            self._timer = None      
            # Set default pin states
            self._change_state(self.STATE_IDLE)
            
        elif self._state == self.STATE_IDLE:
            if self._transition_request == self.TRANSITION_NONE:
                pass # Do nothing - no request to change
            elif self._transition_request == self.TRANSITION_OPEN:
                self._transition_request = self.TRANSITION_NONE
                self._change_state(self.STATE_START_OPENING)
            elif self._transition_request == self.TRANSITION_CLOSE:
                self._transition_request = self.TRANSITION_NONE
                self._change_state(self.STATE_START_CLOSING)
        
        elif self._state == self.STATE_START_OPENING:
            # Set the Pins to Open Valve
            # Start the timer
            self._timer = TimeoutTimer(self._transition_timeout_secs)
            self._change_state(self.STATE_OPENING)
        
        elif self._state == self.STATE_OPENING:
            # Check the pins for the OPEN state
            # Test the timer
            if self._timer.has_timed_out():
                # Error - timeout occurred
                # return to idle state
                pass
            
        elif self._state == self.STATE_OPEN:
            pass
        
        elif self._state == self.STATE_START_CLOSING:
            # Set the Pins to Close Valve
            # Start the timer
            self._timer = TimeoutTimer(self._transition_timeout_secs)
            self._change_state(self.STATE_CLOSING)
            
        elif self._state == self.STATE_CLOSING:
            # Check the pins for the CLOSED state
            # Test the timer
            if self._timer.has_timed_out():
                # Error - timeout occurred
                # return to idle state
                pass
            
        elif self._state == self.STATE_CLOSED:
            pass
        
        else:
            pass
        
    def start_open(self) -> TransitionResponse:
        # Set the direction and enable outputs to open the ball valve
        # Code to control the direction and enable pins goes here
        return TransitionResponse(False, "Not Implemented")


    def start_close(self) -> TransitionResponse:
        # Set the direction and enable outputs to close the ball valve
        # Code to control the direction and enable pins goes here
        return TransitionResponse(False, "Not Implemented")

    def is_open(self) -> bool:
        # Read the state of the open input pin and return True if the ball valve is open, False otherwise
        # Code to read the state of the open pin goes here
        return False

    def is_closed(self) -> bool:
        # Read the state of the close input pin and return True if the ball valve is closed, False otherwise
        # Code to read the state of the close pin goes here
        return False
    
    def _change_state(self, new_state):
        # Change the state of the ball valve and call the state change callback if it is set
        self._state = new_state
        
        if self._state_change_callback != None:
            self._state_change_callback(self._state, new_state)