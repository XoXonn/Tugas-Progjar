import sys
import os.path
import uuid
from glob import glob
from datetime import datetime
import os
import shutil
# import logging # Anda bisa mengaktifkan ini jika ingin logging yang lebih detail di dalam kelas

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.png'] = 'image/png'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        # Tambahkan tipe lain sesuai kebutuhan
        self.web_root = os.getcwd()  # Set web root directory to current working directory

    def response(self, kode=404, message='Not Found', messagebody='', headers={}):
        """
        Membangun dan mengembalikan respons HTTP lengkap dalam bentuk bytes.
        messagebody dapat berupa string atau bytes.
        """
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append("HTTP/1.0 {} {}\r\n".format(kode, message))
        resp.append("Date: {}\r\n".format(tanggal))
        resp.append("Connection: close\r\n") # Set connection to close after response
        resp.append("Server: myserver/1.0\r\n")
        
        # Pastikan messagebody selalu dalam bentuk bytes sebelum digunakan
        if isinstance(messagebody, str):
            messagebody_as_bytes = messagebody.encode('utf-8')
        elif isinstance(messagebody, bytes):
            messagebody_as_bytes = messagebody
        else: # Untuk kasus lain yang mungkin (misal integer, dll), ubah jadi string lalu encode
            messagebody_as_bytes = str(messagebody).encode('utf-8')

        resp.append("Content-Length: {}\r\n".format(len(messagebody_as_bytes)))
        for kk in headers:
            resp.append("{}:{}\r\n".format(kk, headers[kk]))
        resp.append("\r\n") # Ini benar untuk memisahkan header dari body

        response_headers_str = ''
        for i in resp:
            response_headers_str += i
        
        # Gabungkan header yang sudah di-encode dengan body dalam bentuk bytes
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
        
        # Dekode hanya bagian header untuk parsing string
        data_string_headers = raw_data_bytes[:header_end].decode('utf-8', errors='ignore')
        # Bagian body request (jika ada) tetap dalam bentuk bytes
        # request_body_bytes = raw_data_bytes[header_end+4:] # Tidak langsung digunakan di sini, tapi di http_post

        requests_lines = data_string_headers.split("\r\n")
        baris = requests_lines[0] # Baris pertama: METHOD /path HTTP/VERSION
        all_headers = [n for n in requests_lines[1:] if n!=''] # Header lainnya

        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            object_address = j[1].strip()

            if (method == 'GET'):
                return self.http_get(object_address, all_headers)
            elif (method == 'POST'):
                # Untuk POST, kita perlu meneruskan seluruh raw_data_bytes untuk parsing body
                return self.http_post(object_address, all_headers, raw_data_bytes)
            elif (method == 'DELETE'):
                return self.http_delete(object_address, all_headers)
            else:
                return self.response(400, 'Bad Request', 'Method Not Supported', {})
        except IndexError:
            # logging.error(f"Malformed request line: '{baris}'")
            return self.response(400, 'Bad Request', 'Malformed request line', {})
        except Exception as e:
            # logging.error(f"Error during request parsing in proses: {e}", exc_info=True)
            return self.response(500, 'Internal Server Error', f'Server processing error: {e}', {})

    def http_get(self, object_address, headers):
        # Normalisasi dan sanitasi path untuk keamanan (mencegah directory traversal)
        clean_object_address = object_address[1:] if object_address.startswith('/') else object_address
        clean_object_address = os.path.normpath(clean_object_address)
        if clean_object_address.startswith('..'):
             return self.response(403, 'Forbidden', 'Directory traversal forbidden', {})

        full_path = os.path.join(self.web_root, clean_object_address)

        # Handle requests for directory listings
        if object_address == '/': # Default root directory listing (HTML)
            return self.list_directory('.')
        elif object_address.startswith('/list/'): # Specific directory listing (HTML)
            dir_to_list = object_address[len('/list/'):]
            dir_to_list = os.path.normpath(dir_to_list)
            if dir_to_list.startswith('..'):
                 return self.response(403, 'Forbidden', 'Directory traversal forbidden', {})
            return self.list_directory(dir_to_list)
        elif object_address == '/list_simple': # New: Simple text directory listing
            return self.list_directory_simple('.') # Always list current dir for simple text format
        elif os.path.isdir(full_path): # If the requested path is a directory, show its HTML listing
             return self.list_directory(clean_object_address)
        
        # Handle requests for specific files
        elif os.path.isfile(full_path):
            try:
                with open(full_path, 'rb') as fp:
                    isi = fp.read()
                fext = os.path.splitext(full_path)[1]
                content_type = self.types.get(fext.lower(), 'application/octet-stream') # Default to octet-stream if type unknown
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
                # Ekstrak boundary dari Content-Type header
                boundary_str = ""
                if "boundary=" in content_type_header:
                    boundary_str = content_type_header.split("boundary=")[1].strip()
                else:
                    return self.response(400, 'Bad Request', "Boundary not found in Content-Type header.", {})

                boundary = b'--' + boundary_str.encode('ascii') # Boundary diawali dengan --

                # Temukan awal body setelah header HTTP utama
                body_start_index = raw_data_bytes.find(b'\r\n\r\n') + 4
                if body_start_index == 3: # Jika \r\n\r\n tidak ditemukan di awal body
                    return self.response(400, 'Bad Request', "Malformed POST body.", {})

                body_bytes = raw_data_bytes[body_start_index:] # Ini adalah keseluruhan body yang mungkin berisi banyak part

                # Pisahkan body menjadi part-part multipart
                parts = body_bytes.split(boundary)

                filename = None
                file_content = None

                # Iterasi melalui part-part untuk menemukan file
                for part in parts:
                    if not part.strip(): # Lewati part kosong (biasanya yang pertama dan terakhir)
                        continue

                    # Setiap part dimulai dengan header diikuti oleh \r\n\r\n dan kemudian konten
                    part_header_end = part.find(b'\r\n\r\n')
                    if part_header_end == -1:
                        # logging.warning("Malformed multipart part: no header end.")
                        continue # Part rusak

                    part_headers = part[:part_header_end].decode('utf-8', errors='ignore')
                    part_content = part[part_header_end + 4:] # Konten file, mungkin ada \r\n di akhir

                    # Cari Content-Disposition untuk menemukan nama file
                    if "Content-Disposition:" in part_headers:
                        disposition_lines = part_headers.split('\r\n')
                        for d_line in disposition_lines:
                            if "filename=" in d_line:
                                try:
                                    # Ekstrak nama file dari string 'filename="namafile.ext"'
                                    filename = d_line.split("filename=")[1].strip('\"')
                                    
                                    # Hapus CRLF ekstra jika ada di akhir konten file
                                    if part_content.endswith(b'\r\n'):
                                        file_content = part_content[:-2]
                                    else:
                                        file_content = part_content
                                    break # Nama file ditemukan, asumsikan ini adalah bagian file
                                except IndexError:
                                    # logging.warning("Malformed filename in Content-Disposition.")
                                    pass # Nama file tidak terbentuk dengan baik
                    if filename and file_content is not None:
                        break # File ditemukan, keluar dari loop

                if filename and file_content is not None:
                    # Sanitasi nama file untuk mencegah directory traversal (e.g., ../../malicious.txt)
                    clean_filename = os.path.basename(filename) # Hanya mengambil bagian nama file
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
            # Sanitasi nama file untuk mencegah directory traversal
            clean_file_to_delete = os.path.basename(file_to_delete)
            filepath = os.path.join(self.web_root, clean_file_to_delete)
            
            # Pastikan file yang akan dihapus berada di dalam web_root
            if not os.path.normpath(filepath).startswith(os.path.normpath(self.web_root)):
                 return self.response(403, 'Forbidden', 'Deletion outside web root forbidden.', {})

            if os.path.exists(filepath):
                if os.path.isfile(filepath): # Hanya izinkan penghapusan file, bukan direktori
                    try:
                        os.remove(filepath)
                        return self.response(200, 'OK', f"File '{clean_file_to_delete}' deleted successfully.", {})
                    except Exception as e:
                        # logging.error(f"Error deleting file {filepath}: {e}", exc_info=True)
                        return self.response(500, 'Internal Server Error', f"Error deleting file: {e}", {})
                else:
                    return self.response(400, 'Bad Request', "Cannot delete directories this way.", {})
            else:
                return self.response(404, 'Not Found', "File to delete not found.", {})
        else:
            return self.response(400, 'Bad Request', 'Invalid DELETE request path.', {})

    def list_directory(self, path): # Mengembalikan daftar direktori dalam format HTML
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
        files_and_dirs.sort() # Urutkan untuk konsistensi
        html_list = f"<h1>Contents of /{clean_path}</h1><ul>"
        for item in files_and_dirs:
            item_full_path = os.path.join(full_path, item)
            relative_item_path = os.path.relpath(item_full_path, self.web_root) # Path relatif untuk URL
            if os.path.isdir(item_full_path):
                html_list += f"<li><a href=\"/list/{relative_item_path}\">{item}/</a></li>"
            else:
                html_list += f"<li><a href=\"/{relative_item_path}\">{item}</a></li>"
        html_list += "</ul>"

        # Tambahkan formulir unggah langsung ke halaman daftar direktori
        html_list += """
        <h2>Upload File</h2>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="file" name="file">
            <input type="submit" value="Upload">
        </form>
        """

        return self.response(200, 'OK', html_list, {'Content-type': 'text/html'})

    def list_directory_simple(self, path): # Mengembalikan daftar direktori dalam format teks biasa
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
        files_and_dirs.sort() # Urutkan untuk konsisten dengan screenshot
        for item in files_and_dirs:
            item_full_path = os.path.join(full_path, item)
            if os.path.isfile(item_full_path): # Hanya daftar file untuk meniru format screenshot
                text_list += f"- {item}\n"
            # Jika ingin menyertakan direktori dalam daftar teks:
            # elif os.path.isdir(item_full_path):
            #     text_list += f"- {item}/\n"

        return self.response(200, 'OK', text_list, {'Content-type': 'text/plain'})

if __name__ == "__main__":
    httpserver = HttpServer()
    # Contoh pemanggilan untuk pengujian langsung (tidak mensimulasikan penuh client_http.py)
    # Harus menyediakan raw bytes request HTTP yang valid
    
    # Contoh GET /list_simple
    print("--- Test GET /list_simple ---")
    req_simple_list = b"GET /list_simple HTTP/1.0\r\nHost: localhost\r\n\r\n"
    res_simple_list = httpserver.proses(req_simple_list)
    print(res_simple_list.decode(errors='ignore')) # Decode untuk melihat output teks

    # Contoh GET /donalbebek.jpg
    print("\n--- Test GET /donalbebek.jpg ---")
    req_image = b"GET /donalbebek.jpg HTTP/1.0\r\nHost: localhost\r\n\r\n"
    res_image = httpserver.proses(req_image)
    # Karena ini biner, mungkin hanya mencetak sebagian header dan awal body
    print(res_image[:200].decode(errors='ignore') + "...")
