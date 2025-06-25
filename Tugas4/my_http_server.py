import sys
import os.path
import uuid
from glob import glob
from datetime import datetime
import os
import shutil

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.png'] = 'image/png'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        self.web_root = os.getcwd()

    def response(self, kode=404, message='Not Found', messagebody='', headers={}):
        """
        Membangun dan mengembalikan respons HTTP lengkap dalam bentuk bytes.
        messagebody dapat berupa string atau bytes.
        """
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append("HTTP/1.0 {} {}\r\n".format(kode, message))
        resp.append("Date: {}\r\n".format(tanggal))
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        
        if isinstance(messagebody, str):
            messagebody_as_bytes = messagebody.encode('utf-8')
        elif isinstance(messagebody, bytes):
            messagebody_as_bytes = messagebody
        else:
            messagebody_as_bytes = str(messagebody).encode('utf-8')

        resp.append("Content-Length: {}\r\n".format(len(messagebody_as_bytes)))
        for kk in headers:
            resp.append("{}:{}\r\n".format(kk, headers[kk]))
        resp.append("\r\n")

        response_headers_str = ''
        for i in resp:
            response_headers_str += i
        
        final_response_bytes = response_headers_str.encode('utf-8') + messagebody_as_bytes
        return final_response_bytes

    def proses(self, raw_data_bytes):
        """
        Memproses raw HTTP request bytes dan mengembalikan respons HTTP dalam bytes.
        """
        # Cari akhir header HTTP (\r\n\r\n)
        header_end = raw_data_bytes.find(b'\r\n\r\n')
        if header_end == -1:
            # logging.error("Malformed request: no end of headers (CRLFCRLF not found)")
            return self.response(400, 'Bad Request', 'Malformed request: no end of headers', {})
        
        data_string_headers = raw_data_bytes[:header_end].decode('utf-8', errors='ignore')

        requests_lines = data_string_headers.split("\r\n")
        baris = requests_lines[0]
        all_headers = [n for n in requests_lines[1:] if n!='']

        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            object_address = j[1].strip()

            if (method == 'GET'):
                return self.http_get(object_address, all_headers)
            elif (method == 'POST'):
                return self.http_post(object_address, all_headers, raw_data_bytes)
            elif (method == 'DELETE'):
                return self.http_delete(object_address, all_headers)
            else:
                return self.response(400, 'Bad Request', 'Method Not Supported', {})
        except IndexError:
            return self.response(400, 'Bad Request', 'Malformed request line', {})
        except Exception as e:
            return self.response(500, 'Internal Server Error', f'Server processing error: {e}', {})

    def http_get(self, object_address, headers):
        clean_object_address = object_address[1:] if object_address.startswith('/') else object_address
        clean_object_address = os.path.normpath(clean_object_address)
        if clean_object_address.startswith('..'):
             return self.response(403, 'Forbidden', 'Directory traversal forbidden', {})

        full_path = os.path.join(self.web_root, clean_object_address)

        if object_address == '/': # Default root directory listing (HTML)
            return self.list_directory('.')
        elif object_address.startswith('/list/'): # Specific directory listing (HTML)
            dir_to_list = object_address[len('/list/'):]
            dir_to_list = os.path.normpath(dir_to_list)
            if dir_to_list.startswith('..'):
                 return self.response(403, 'Forbidden', 'Directory traversal forbidden', {})
            return self.list_directory(dir_to_list)
        elif object_address == '/list_simple': 
            return self.list_directory_simple('.')
        elif os.path.isdir(full_path):
             return self.list_directory(clean_object_address)
        
        elif os.path.isfile(full_path):
            try:
                with open(full_path, 'rb') as fp:
                    isi = fp.read()
                fext = os.path.splitext(full_path)[1]
                content_type = self.types.get(fext.lower(), 'application/octet-stream')
                headers = {'Content-type': content_type}
                return self.response(200, 'OK', isi, headers)
            except FileNotFoundError:
                # logging.warning(f"File not found: {full_path}")
                return self.response(404, 'Not Found', 'File Not Found', {})
            except Exception as e:
                # logging.error(f"Error reading file {full_path}: {e}", exc_info=True)
                return self.response(500, 'Internal Server Error', f"Error reading file: {e}", {})
        else: # Resource not found or not a file/directory
            return self.response(404, 'Not Found', 'Resource Not Found', {})

    def http_post(self, object_address, headers, raw_data_bytes):
        if object_address == '/upload':
            content_type_header = ""
            for h in headers:
                if h.lower().startswith('content-type:'):
                    content_type_header = h
                    break

            if not content_type_header or "multipart/form-data" not in content_type_header:
                return self.response(400, 'Bad Request', "Expected multipart/form-data for upload.", {})

            try:
                boundary_str = ""
                if "boundary=" in content_type_header:
                    boundary_str = content_type_header.split("boundary=")[1].strip()
                else:
                    return self.response(400, 'Bad Request', "Boundary not found in Content-Type header.", {})

                boundary = b'--' + boundary_str.encode('ascii')

                body_start_index = raw_data_bytes.find(b'\r\n\r\n') + 4
                if body_start_index == 3:
                    return self.response(400, 'Bad Request', "Malformed POST body.", {})

                body_bytes = raw_data_bytes[body_start_index:] 
                parts = body_bytes.split(boundary)

                filename = None
                file_content = None

                for part in parts:
                    if not part.strip():
                        continue
                    part_header_end = part.find(b'\r\n\r\n')
                    if part_header_end == -1:
                        # logging.warning("Malformed multipart part: no header end.")
                        continue 

                    part_headers = part[:part_header_end].decode('utf-8', errors='ignore')
                    part_content = part[part_header_end + 4:] 

                    if "Content-Disposition:" in part_headers:
                        disposition_lines = part_headers.split('\r\n')
                        for d_line in disposition_lines:
                            if "filename=" in d_line:
                                try:
                                    filename = d_line.split("filename=")[1].strip('\"')
                                    if part_content.endswith(b'\r\n'):
                                        file_content = part_content[:-2]
                                    else:
                                        file_content = part_content
                                    break
                                except IndexError:
                                    # logging.warning("Malformed filename in Content-Disposition.")
                                    pass 
                    if filename and file_content is not None:
                        break

                if filename and file_content is not None:
                    clean_filename = os.path.basename(filename)
                    filepath = os.path.join(self.web_root, clean_filename)

                    with open(filepath, 'wb') as f:
                        f.write(file_content)
                    return self.response(200, 'OK', f"File '{clean_filename}' uploaded successfully.", {})
                else:
                    return self.response(400, 'Bad Request', "No file found in upload request or malformed data.", {})
            except Exception as e:
                # logging.error(f"Error during file upload: {e}", exc_info=True)
                return self.response(500, 'Internal Server Error', f"Error uploading file: {e}", {})
        else:
             return self.response(400, 'Bad Request', 'Invalid POST request path.', {})

    def http_delete(self, object_address, headers):
        if object_address.startswith('/delete/'):
            file_to_delete = object_address[len('/delete/'):]
            clean_file_to_delete = os.path.basename(file_to_delete)
            filepath = os.path.join(self.web_root, clean_file_to_delete)
            if not os.path.normpath(filepath).startswith(os.path.normpath(self.web_root)):
                 return self.response(403, 'Forbidden', 'Deletion outside web root forbidden.', {})

            if os.path.exists(filepath):
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                        return self.response(200, 'OK', f"File '{clean_file_to_delete}' deleted successfully.", {})
                    except Exception as e:
                        return self.response(500, 'Internal Server Error', f"Error deleting file: {e}", {})
                else:
                    return self.response(400, 'Bad Request', "Cannot delete directories this way.", {})
            else:
                return self.response(404, 'Not Found', "File to delete not found.", {})
        else:
            return self.response(400, 'Bad Request', 'Invalid DELETE request path.', {})

    def list_directory(self, path):
        """
        Menghasilkan string HTML yang mewakili daftar file dan subdirektori.
        """
        clean_path = os.path.normpath(path)
        if clean_path.startswith('..'):
             return self.response(403, 'Forbidden', 'Directory traversal forbidden', {'Content-type': 'text/html'})

        full_path = os.path.join(self.web_root, clean_path)
        
        if not os.path.isdir(full_path):
            return self.response(404, 'Not Found', f"Directory '{clean_path}' not found or is not a directory.", {'Content-type': 'text/html'})

        files_and_dirs = os.listdir(full_path)
        files_and_dirs.sort()
        html_list = f"<h1>Contents of /{clean_path}</h1><ul>"
        for item in files_and_dirs:
            item_full_path = os.path.join(full_path, item)
            relative_item_path = os.path.relpath(item_full_path, self.web_root)
            if os.path.isdir(item_full_path):
                html_list += f"<li><a href=\"/list/{relative_item_path}\">{item}/</a></li>"
            else:
                html_list += f"<li><a href=\"/{relative_item_path}\">{item}</a></li>"
        html_list += "</ul>"

        html_list += """
        <h2>Upload File</h2>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="file" name="file">
            <input type="submit" value="Upload">
        </form>
        """

        return self.response(200, 'OK', html_list, {'Content-type': 'text/html'})

    def list_directory_simple(self, path):
        """
        Menghasilkan string teks biasa yang mewakili daftar file dalam direktori.
        """
        clean_path = os.path.normpath(path)
        if clean_path.startswith('..'):
             return self.response(403, 'Forbidden', 'Directory traversal forbidden', {'Content-type': 'text/plain'})

        full_path = os.path.join(self.web_root, clean_path)
        
        if not os.path.isdir(full_path):
            return self.response(404, 'Not Found', f"Directory '{clean_path}' not found or is not a directory.", {'Content-type': 'text/plain'})

        files_and_dirs = os.listdir(full_path)
        text_list = "daftar file :\n"
        files_and_dirs.sort()
        for item in files_and_dirs:
            item_full_path = os.path.join(full_path, item)
            if os.path.isfile(item_full_path):
                text_list += f"- {item}\n"
        return self.response(200, 'OK', text_list, {'Content-type': 'text/plain'})

if __name__ == "__main__":
    httpserver = HttpServer()
    
    # Contoh GET /list_simple
    print("--- Test GET /list_simple ---")
    req_simple_list = b"GET /list_simple HTTP/1.0\r\nHost: localhost\r\n\r\n"
    res_simple_list = httpserver.proses(req_simple_list)
    print(res_simple_list.decode(errors='ignore'))

    # Contoh GET /donalbebek.jpg
    print("\n--- Test GET /donalbebek.jpg ---")
    req_image = b"GET /donalbebek.jpg HTTP/1.0\r\nHost: localhost\r\n\r\n"
    res_image = httpserver.proses(req_image)
    # Karena ini biner, mungkin cuma nyetak sebagian header dan awal body
    print(res_image[:200].decode(errors='ignore') + "...")
