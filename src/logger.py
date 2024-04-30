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
    _log_to_disk = False
    _log_directory = "log"

    def __init__(self, log_to_disk = False) -> None:
        self._msg_count = 0
        self._log_to_disk = log_to_disk
        if self._log_to_disk:
            if not os.path.exists(self._log_directory):
                os.makedirs(self._log_directory)
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
                                            level_str).ljust(50)
        #print(header + msg)
        log_msg = ("\n" + header + msg).encode('utf8')
        os.write(sys.stdout.fileno(), log_msg)
        self._write_to_log_file(header + msg + "\n")
    
    '''
    Write a string to the console without a header or new line
    '''
    def write_single_line_no_header(self, msg) -> None:
        os.write(sys.stdout.fileno(), (msg).encode('utf8'))
        
    ''' ---- File Logger ---- '''
    _last_log_file_date_str = None
    _log_file_date_format = '%Y%m%d.log'    
    def _write_to_log_file(self, log_msg):
        # Short-circuit if logging to disk is disabled
        if self._log_to_disk == False:
            return
        # Check if a new file should be created
        file_date_string = datetime.now().strftime(self._log_file_date_format)           
        log_file = open(self._log_directory + "/" + file_date_string, "a")
        log_file.write(log_msg)
        log_file.close()
            