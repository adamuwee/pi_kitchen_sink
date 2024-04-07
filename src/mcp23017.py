import smbus
import time
import datetime

# Datasheet
# https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf

# Define MCP23017 registers
IODIRA = 0x00  # I/O direction register for port A
IODIRB = 0x01  # I/O direction register for port B
GPIOA = 0x12   # Register for port A
GPIOB = 0x13   # Register for port B

MCP23x17_IODIRA		= 0x00
MCP23x17_IPOLA		= 0x02
MCP23x17_GPINTENA	= 0x04
MCP23x17_DEFVALA	= 0x06
MCP23x17_INTCONA	= 0x08
MCP23x17_IOCON		= 0x0A
MCP23x17_GPPUA		= 0x0C
MCP23x17_INTFA		= 0x0E
MCP23x17_INTCAPA	= 0x10
MCP23x17_GPIOA		= 0x12
MCP23x17_OLATA		= 0x14

MCP23x17_IODIRB		= 0x01
MCP23x17_IPOLB		= 0x03
MCP23x17_GPINTENB	= 0x05
MCP23x17_DEFVALB	= 0x07
MCP23x17_INTCONB	= 0x09
MCP23x17_IOCONB		= 0x0B
MCP23x17_GPPUB		= 0x0D
MCP23x17_INTFB		= 0x0F
MCP23x17_INTCAPB	= 0x11
MCP23x17_GPIOB		= 0x13
MCP23x17_OLATB		= 0x15

IOCON_UNUSED	    = 0x01
IOCON_INTPOL	    = 0x02
IOCON_ODR	        = 0x04
IOCON_HAEN	        = 0x08
IOCON_DISSLW	    = 0x10
IOCON_SEQOP	        = 0x20
IOCON_MIRROR	    = 0x40
IOCON_BANK_MODE	    = 0x80

class MCP23017:
    def __init__(self, address, bus=1):
        self.address = address
        self.bus = smbus.SMBus(bus)
        
        # Enable sequential mode - increments its address counter after each byte during the data transfer.
        self.bus.write_byte_data(self.address, MCP23x17_IOCON, IOCON_SEQOP) 
        
        self.bus.write_byte_data(self.address, IODIRA, 0xFF)  # Set all pins on port A as inputs
        self.bus.write_byte_data(self.address, IODIRB, 0x00)  # Set all pins on port B as outputs

    '''Raw Write - pins 0 - 16'''
    def write_pin(self, pin, value):
        if pin < 8:
            register = GPIOA
        else:
            register = GPIOB
            pin -= 8
        current_value = self.bus.read_byte_data(self.address, register)
        if value:
            current_value |= (1 << pin)
        else:
            current_value &= ~(1 << pin)
        self.bus.write_byte_data(self.address, register, current_value)

    '''Raw Read - pins 0 - 16'''
    def read_pin(self, pin):
        if pin < 8:
            register = GPIOA
        else:
            register = GPIOB
            pin -= 8
        current_value = self.bus.read_byte_data(self.address, register)
        return (current_value >> pin) & 1
    
    '''Read a digital input that is mapped to the Kitchen Sink I/O'''
    def read_kitchensink_dinput(self, channel_index=0) -> bool:
        if channel_index < 0 or channel_index > 15:
            raise ValueError("Invalid channel index")
        return self.read_pin(channel_index)
    
    '''Write a digital output that is mapped to the Kitchen Sink I/O'''
    def write_kitchensink_doutput(self, channel_index=0, value=False):
        if channel_index < 0 or channel_index > 15:
            raise ValueError("Invalid channel index")
        self.write_pin(channel_index, value)
        
    def read_kitchensink_dports(self) -> int:
        port_a = current_value = self.bus.read_byte_data(self.address, MCP23x17_GPIOA)
        port_b = current_value = self.bus.read_byte_data(self.address, MCP23x17_GPIOB)
        port_value = (port_b << 8) | port_a
        return port_value
    
    def print_kitchensink_dports(self):
        port_value = self.read_kitchensink_dports()
        print(f"Port A: 0x{port_value & 0xFF:08b}\tPort B: 0x{port_value >> 8:08b}")
        
'''Component Test'''
if __name__ == '__main__':
    
    # MCP23017 object
    mcp = MCP23017(0x21)
    
    # Test List
    test_toggle_port_ab = False
    test_repeat_port_a_read = True
    
    # Toggle Outputs on the MCP23017
    if test_toggle_port_ab:
        for channel_index in range(16):
            toggle_count = 4
            print(f"Toggling Channel {channel_index}")
            for toggle_index in range(toggle_count):
                mcp.write_kitchensink_doutput(channel_index, True)
                mcp.print_kitchensink_dports()
                print("<")
                time.sleep(0.25)
                mcp.write_kitchensink_doutput(channel_index, False)
                mcp.print_kitchensink_dports()
                print(">")
                time.sleep(0.25)
    
    # Repeat Read of Port A
    if test_repeat_port_a_read:
        test_duration_seconds = 60
        start_time = datetime.datetime.now()
        
        while (datetime.datetime.now() - start_time).total_seconds() < test_duration_seconds:
            mcp.print_kitchensink_dports()
            time.sleep(1)