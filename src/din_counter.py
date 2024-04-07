from RPi import GPIO
import datetime
import time

 

'''Counts rising edges on GPIO 5 and 6 of a Raspberry PI'''
class DinCounter:
    
    class Counter:
        
        # Class Privates
        bcm_pin = 0
        _count = 0
        _debounce_ms = 0
        _last_edge_time = datetime.datetime.now()
        
        
        def __init__(self, bcm_pin, debounce_ms=250):
            self.bcm_pin = bcm_pin
            self._count = 0
            self._debounce_ms = debounce_ms
            
        def increment(self):
            time_delta = (datetime.datetime.now() - self._last_edge_time).total_seconds() * 1000.0
            if time_delta > self._debounce_ms:
                self._count += 1
                self._last_edge_time = datetime.datetime.now()
            
        def get_count(self):
            return self._count
        
        def reset(self):
            self._count = 0
    
    def __init__(self):
        
        # Counters
        self.count_A = 0
        self.count_B = 0
    
        # Config PIN Modes and callbacks
        GPIO.setmode(GPIO.BCM)
        self._counter_A = DinCounter.Counter(16)
        self._counter_B = DinCounter.Counter(26)
        GPIO.setup(self._counter_A.bcm_pin, GPIO.IN)
        GPIO.setup(self._counter_B.bcm_pin, GPIO.IN)
        GPIO.add_event_detect(self._counter_A.bcm_pin, GPIO.FALLING, callback=self.increment_count_A)
        GPIO.add_event_detect(self._counter_B.bcm_pin, GPIO.FALLING, callback=self.increment_count_B)

    '''GPIO 5 Rising Edge Callback'''
    def increment_count_A(self, channel):
        self._counter_A.increment()

    '''GPIO 6 Rising Edge Callback'''
    def increment_count_B(self, channel):
        self._counter_B.increment()

    '''Get the GPIO5 edge count'''
    def get_count_A(self):
        return self._counter_A.get_count()

    '''Get the GPIO6 edge count'''
    def get_count_B(self):
        return self._counter_B.get_count()

    '''Reset the GPIO5 edge count'''
    def reset_count_A(self):
        self._counter_A.reset()

    '''Reset the GPIO6 edge count'''
    def reset_count_B(self):
        self._counter_B.reset()
    
    '''GPIO Clean-up on exit'''
    def cleanup(self):
        GPIO.cleanup()

'''Component Test'''
if __name__ == '__main__':
    

    # Usage example
    counter = DinCounter()

    # Do something...
    test_duration_seconds = 60
    start_time = datetime.datetime.now()
    index = 0
    while (datetime.datetime.now() - start_time).total_seconds() < test_duration_seconds:
        # Get the counts
        count_A = counter.get_count_A()
        count_B = counter.get_count_B()
        # Print
        print(f"[{index}]\tCNT-A: {count_A}\tCNT-B: {count_B}")
        index += 1
        time.sleep(1)

    # Clean up GPIO
    counter.cleanup()