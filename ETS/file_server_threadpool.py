import socket
import logging
import concurrent.futures
import argparse
from file_protocol import FileProtocol

def handle_client(connection, address):
    """Function to handle client requests with correct byte buffering"""
    logging.warning(f"handling connection from {address}")
    buffer = b""
    fp = FileProtocol()
    try:
        connection.settimeout(300)

        while True:
            data = connection.recv(1024 * 1024)
            if not data:
                break

            buffer += data
            
            while b"\r\n\r\n" in buffer:
                command_data, buffer = buffer.split(b"\r\n\r\n", 1)
                
                hasil_str = fp.proses_string(command_data.decode())
                
                response = hasil_str + "\r\n\r\n"
                connection.sendall(response.encode())
    except Exception as e:
        logging.warning(f"Error handling client {address}: {str(e)}")
    finally:
        logging.warning(f"connection from {address} closed")
        connection.close()

class Server:
    def __init__(self, ipaddress, port, pool_size):
        self.ipinfo = (ipaddress, port)
        self.pool_size = pool_size
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        logging.warning(f"ThreadPool Server running on {self.ipinfo} with {self.pool_size} workers")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(self.pool_size * 2)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.pool_size) as executor:
            while True:
                try:
                    connection, client_address = self.my_socket.accept()
                    executor.submit(handle_client, connection, client_address)
                except KeyboardInterrupt:
                    logging.warning("Server shutting down.")
                    break
        self.my_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='File Server (ThreadPool)')
    parser.add_argument('--port', type=int, default=6667, help='Server port')
    parser.add_argument('--pool-size', type=int, default=10, help='Worker pool size')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    server = Server(ipaddress='0.0.0.0', port=args.port, pool_size=args.pool_size)
    server.run()
