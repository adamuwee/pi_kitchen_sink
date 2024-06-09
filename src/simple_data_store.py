import os
import json
from datetime import datetime

class DiskDataStore:
    
    def __init__(self, filename):
        self.filename = filename
        self.data = self._load_data()

    def _load_data(self):
        """Loads data from the file. Create if DNE"""
        if not os.path.exists(self.filename):
            os.mknod(self.filename)
        try:
            with open(self.filename, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print("DiskDataStore: File not found.")
            return {}
        except json.JSONDecodeError:
            print("DiskDataStore: JSONDecodeError")
            return {}

    def _save_data(self):
        """Saves data to the file."""
        with open(self.filename, 'w') as file:
            json.dump(self.data, file)

    def write(self, tag, value):
        """Writes a number with a timestamp based on the provided tag."""
        timestamp = datetime.now().isoformat()
        self.data[tag] = (value, timestamp)
        self._save_data()

    def read(self, tag):
        """Reads all numbers with their timestamps for the given tag."""
        if tag not in self.data:
            return (None, None)
        return self.data.get(tag, None)