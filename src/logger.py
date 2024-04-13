from enum import Enum
from datetime import datetime
import os
import sys

# Fixed multi-threading bug by using os.write instead of print
# Ref: https://stackoverflow.com/questions/75367828/runtimeerror-reentrant-call-inside-io-bufferedwriter-name-stdout

class MessageLevel(Enum):
    INFO = 0
    WARN = 1
    ERROR = 2

class Logger:

    _mute_list = []
    _mute_list.append("mqtt-subscriber")
    
    def __init__(self) -> None:
        self._msg_count = 0
        pass

    def write(self, key, msg, level = MessageLevel.INFO) -> None:
        if (key in self._mute_list):
            return
        level_str = ""
        if (level == MessageLevel.ERROR):
            level_str = 'ERROR'
        elif (level == MessageLevel.WARN):
            level_str = 'WARN'
        elif (level == MessageLevel.INFO):
            level_str = 'INFO'
        else:
            level_str = 'UNKNOWN'
        
        # Format
        # [DateTime][key][level]{message} 
        header = "[{0}][{1}][{2}]".format(datetime.now(),
                                            key,
                                            level_str).ljust(60)
        #print(header + msg)
        os.write(sys.stdout.fileno(), ("\n" + header + msg).encode('utf8'))
    
    '''
    Write a string to the console without a header or new line
    '''
    def write_single_line_no_header(self, msg) -> None:
        os.write(sys.stdout.fileno(), (msg).encode('utf8'))