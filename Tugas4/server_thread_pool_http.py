from socket import *
import socket
import time
import sys
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from my_http_server import HttpServer

httpserver = HttpServer()

#untuk menggunakan threadpool executor, karena tidak mendukung subclassing pada process,
#maka class ProcessTheClient dirubah dulu menjadi function, tanpda memodifikasi behaviour didalamnya

def ProcessTheClient(connection,address):
    print(f"[{address}] New client connection accepted.") # DEBUG print
    rcv_buffer = b"" # Use bytes for buffer to handle raw incoming data
    while True:
        try:
            # Read larger chunks to get the full request faster
            data = connection.recv(8192) # Ensure this is 8192, not 32
            if not data: # Client closed connection (or no more data)
                print(f"[{address}] Client disconnected or recv returned empty data. Breaking loop.") # DEBUG print
                break
            
            rcv_buffer += data
            print(f"[{address}] Received {len(data)} bytes. Total in buffer: {len(rcv_buffer)} bytes.") # DEBUG print
            
            # Find the end of the HTTP headers (\r\n\r\n)
            header_end_index = rcv_buffer.find(b'\r\n\r\n')

            if header_end_index != -1:
                print(f"[{address}] End of headers detected at index {header_end_index}.") # DEBUG print
                
                # Decode headers to string for parsing (method, content-length)
                headers_raw_string = rcv_buffer[:header_end_index].decode('utf-8', errors='ignore')
                first_line = headers_raw_string.split('\r\n')[0]
                method = first_line.split(' ')[0].upper()
                
                content_length = 0
                if method == 'POST':
                    for line in headers_raw_string.split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            try:
                                content_length = int(line.split(':')[1].strip())
                                break
                            except ValueError:
                                pass # Malformed Content-Length header

                # Calculate the total expected length of the entire HTTP request
                # (Headers + CRLFCRLF + Body)
                total_request_length = header_end_index + 4 + content_length

                # Check if we have received the complete request
                if len(rcv_buffer) >= total_request_length:
                    print(f"[{address}] Full request received ({len(rcv_buffer)}/{total_request_length} bytes). Passing to HttpServer.proses...") # DEBUG print
                    # Pass the full raw request bytes to HttpServer.proses
                    hasil = httpserver.proses(rcv_buffer)
                    
                    print(f"[{address}] HttpServer.proses returned response (length: {len(hasil)} bytes). First 100 bytes: {hasil[:100]}") # DEBUG print
                    connection.sendall(hasil) # Send the complete response back
                    print(f"[{address}] Response sent via sendall. Closing connection.") # DEBUG print
                    connection.close() # Close connection after sending response
                    return # Thread/process finished, return

        except OSError as e:
            print(f"[{address}] Socket error in ProcessTheClient: {e}") # DEBUG print
            break # Exit loop on socket error
        except Exception as e:
            print(f"[{address}] UNEXPECTED ERROR in ProcessTheClient: {e}") # DEBUG print
            import traceback # For more detailed error info
            traceback.print_exc() # Print full stack trace
            break # Exit loop on other errors

    print(f"[{address}] ProcessTheClient: Connection closed at end of function.") # DEBUG print
    connection.close() # Ensure connection is closed if loop breaks naturally
    return


def Server():
	the_clients = []
	my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	my_socket.bind(('0.0.0.0', 8885))
	my_socket.listen(1)

	with ThreadPoolExecutor(20) as executor:
		while True:
				connection, client_address = my_socket.accept()
				#logging.warning("connection from {}".format(client_address))
				p = executor.submit(ProcessTheClient, connection, client_address)
				the_clients.append(p)
				#menampilkan jumlah process yang sedang aktif
				jumlah = ['x' for i in the_clients if i.running()==True]
				print(jumlah)





def main():
	Server()

if __name__=="__main__":
	main()

