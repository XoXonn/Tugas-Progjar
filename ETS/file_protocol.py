import json
import logging
from file_interface import FileInterface

class FileProtocol:
    def __init__(self):
        self.file = FileInterface()

    def proses_string(self, string_datamasuk=''):
        try:
            parts = string_datamasuk.strip().split(' ', 1)
            command = parts[0].lower()
            
            params = []
            if len(parts) > 1:
                if command == 'upload':
                    params = parts[1].split(' ', 1)
                else:
                    params = [parts[1]]

            logging.warning(f"Request: {command}, Params: {params[0] if params else 'N/A'}")

            if hasattr(self.file, command):
                method = getattr(self.file, command)
                hasil = method(params)
                return json.dumps(hasil)
            else:
                return json.dumps(dict(status='ERROR', data=f'Perintah {command} tidak dikenali'))
        except Exception as e:
            logging.error(f"Error processing protocol string: {e}")
            return json.dumps(dict(status='ERROR', data=str(e)))
