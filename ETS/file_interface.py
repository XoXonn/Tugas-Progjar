import os
import base64
from glob import glob
import logging

class FileInterface:
    def __init__(self):
        self.storage_dir = os.path.join(os.path.dirname(__file__), 'files')
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def list(self, params=[]):
        try:
            list_files = glob(os.path.join(self.storage_dir, '*.*'))
            file_names = [os.path.basename(f) for f in list_files]
            return dict(status='OK', data=file_names)
        except Exception as e:
            logging.error(f"Error listing files: {e}")
            return dict(status='ERROR', data=str(e))

    def get(self, params=[]):
        if not params:
            return dict(status='ERROR', data='Nama file tidak boleh kosong')
        filename = params[0]
        file_path = os.path.join(self.storage_dir, filename)
        
        if not os.path.exists(file_path):
            return dict(status='ERROR', data=f'File {filename} tidak ditemukan')
            
        try:
            with open(file_path, 'rb') as fp:
                isifile = base64.b64encode(fp.read()).decode()
            return dict(status='OK', data_namafile=filename, data_file=isifile)
        except Exception as e:
            logging.error(f"Error getting file {filename}: {e}")
            return dict(status='ERROR', data=str(e))
    
    def upload(self, params=[]):
        if len(params) < 2:
            return dict(status='ERROR', data='Perintah UPLOAD butuh namafile dan data')
        
        filename = params[0]
        filedata_base64 = params[1]
        file_path = os.path.join(self.storage_dir, filename)
        
        try:
            with open(file_path, 'wb') as fp:
                fp.write(base64.b64decode(filedata_base64))
            return dict(status='OK', data=f'File {filename} berhasil diupload')
        except Exception as e:
            logging.error(f"Error uploading file {filename}: {e}")
            return dict(status='ERROR', data=str(e))
