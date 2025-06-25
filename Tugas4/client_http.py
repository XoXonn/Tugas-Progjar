import requests
import os
import re # Import regex module
from html.parser import HTMLParser

SERVER_HOST = 'localhost'
THREAD_POOL_PORT = 8885
PROCESS_POOL_PORT = 8889

# --- Parser untuk mengidentifikasi file dari daftar HTML (tetap ada untuk daftar HTML) ---
class FileLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.files_to_get = []
        self.in_ul = False

    def handle_starttag(self, tag, attrs):
        if tag == 'ul':
            self.in_ul = True
        if self.in_ul and tag == 'a':
            for attr, value in attrs:
                if attr == 'href':
                    if value.endswith('/') or value.startswith('/list/') or value in ['./', '../', '/', '/list/']:
                        continue
                    
                    filename_from_href = os.path.basename(value)
                    if filename_from_href:
                        self.files_to_get.append(filename_from_href)
    
    def handle_endtag(self, tag):
        if tag == 'ul':
            self.in_ul = False

    def get_files(self):
        return list(set(self.files_to_get))

# --- Fungsi klien yang sudah ada (direktori HTML) ---
def get_directory_listing(port):
    print(f"\n--- Getting directory listing (HTML) from port {port} ---") # Changed print for clarity
    try:
        response = requests.get(f"http://{SERVER_HOST}:{port}/list/")
        if response.status_code == 200:
            print("Directory Listing (HTML):\n", response.text)

            parser = FileLinkParser()
            parser.feed(response.text)
            files = parser.get_files()
            
            print(f"\n--- Discovered {len(files)} files from HTML listing to download from port {port} ---")
            for f_name in files:
                get_file(port, f_name)

        else:
            print(f"Error: {response.status_code} - {response.reason}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Fungsi baru untuk daftar direktori teks sederhana ---
def get_directory_listing_simple(port):
    print(f"\n--- Getting simple text directory listing from port {port} ---") # New print
    try:
        response = requests.get(f"http://{SERVER_HOST}:{port}/list_simple") # Request new endpoint
        if response.status_code == 200:
            print("Simple Directory Listing:\n")
            print(response.text) # Print raw text response
        else:
            print(f"Error: {response.status_code} - {response.reason}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# --- Fungsi get_file yang sudah ada (untuk mengunduh file individual) ---
def get_file(port, filename):
    print(f"  --> Downloading file '{filename}' from port {port}")
    try:
        response = requests.get(f"http://{SERVER_HOST}:{port}/{filename}")
        if response.status_code == 200:
            print(f"      - Successfully downloaded '{filename}'. Content length: {len(response.content)} bytes.")
        else:
            print(f"      - Error downloading '{filename}': {response.status_code} - {response.reason}")
    except requests.exceptions.ConnectionError as e:
        print(f"      - Connection Error downloading '{filename}': {e}")
    except Exception as e:
        print(f"      - An unexpected error occurred downloading '{filename}': {e}")


# --- Fungsi upload_file yang sudah ada ---
def upload_file(port, filename_to_upload, server_filename):
    print(f"\n--- Uploading '{filename_to_upload}' to server as '{server_filename}' on port {port} ---")
    filepath = os.path.join(os.getcwd(), filename_to_upload)
    if not os.path.exists(filepath):
        print(f"Error: File '{filename_to_upload}' not found locally.")
        return

    try:
        with open(filepath, 'rb') as f:
            files = {'file': (server_filename, f, 'application/octet-stream')}
            response = requests.post(f"http://{SERVER_HOST}:{port}/upload", files=files)
            if response.status_code == 200:
                print(f"Upload successful: {response.text}")
            else:
                print(f"Error: {response.status_code} - {response.reason} - {response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Fungsi delete_file yang sudah ada ---
def delete_file(port, filename_to_delete):
    print(f"\n--- Deleting '{filename_to_delete}' from server on port {port} ---")
    try:
        response = requests.delete(f"http://{SERVER_HOST}:{port}/delete/{filename_to_delete}")
        if response.status_code == 200:
            print(f"Delete successful: {response.text}")
        else:
            print(f"Error: {response.status_code} - {response.reason} - {response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")

# --- Bagian utama eksekusi klien ---
if __name__ == "__main__":
    # Create local test files
    with open("test_upload.txt", "w") as f:
        f.write("This is a test file for upload.")
    with open("test_delete.txt", "w") as f:
        f.write("This file will be deleted.")
    with open("test_upload_proc.txt", "w") as f:
        f.write("This is a test file for upload to process pool.")
    with open("test_delete_proc.txt", "w") as f:
        f.write("This file will be deleted from process pool.")

    # --- Testing with Thread Pool Server ---
    print("\n\n=== Testing with Thread Pool Server ===")
    get_directory_listing_simple(THREAD_POOL_PORT) # NEW: Demonstrate simple text listing first
    get_directory_listing(THREAD_POOL_PORT) # Then HTML listing with download all files
    
    upload_file(THREAD_POOL_PORT, "test_upload.txt", "uploaded_test_file_thread.txt")
    get_directory_listing(THREAD_POOL_PORT) # Verify upload (and redownload everything including new file)
    delete_file(THREAD_POOL_PORT, "uploaded_test_file_thread.txt")
    get_directory_listing(THREAD_POOL_PORT) # Verify deletion

    # --- Testing with Process Pool Server ---
    print("\n\n=== Testing with Process Pool Server ===")
    get_directory_listing_simple(PROCESS_POOL_PORT) # NEW: Demonstrate simple text listing first
    get_directory_listing(PROCESS_POOL_PORT) # Then HTML listing with download all files
    
    upload_file(PROCESS_POOL_PORT, "test_upload_proc.txt", "uploaded_test_file_process.txt")
    get_directory_listing(PROCESS_POOL_PORT) # Verify upload (and redownload everything including new file)
    delete_file(PROCESS_POOL_PORT, "uploaded_test_file_process.txt")
    get_directory_listing(PROCESS_POOL_PORT) # Verify deletion

    # Clean up local test files
    for f in ["test_upload.txt", "test_delete.txt", "test_upload_proc.txt", "test_delete_proc.txt"]:
        if os.path.exists(f):
            os.remove(f)
            print(f"Cleaned up local file: {f}")
