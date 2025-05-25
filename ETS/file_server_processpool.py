import socket
import logging
import concurrent.futures
import argparse
import multiprocessing
import threading
import os
import json
import time
from file_protocol import FileProtocol

def process_data_task(data_string):
    pid = os.getpid()
    try:
        fp_local = FileProtocol()
        result = fp_local.proses_string(data_string)
        return result
    except Exception as e:
        logging.error(f"Error in process_data_task (pid={pid}): {e}", exc_info=True)
        return json.dumps({'status': 'ERROR', 'data': f'Worker PID={pid} failed: {str(e)}'})

def handle_connection(conn, addr, pool):
    thread_id = threading.get_ident()
    logging.warning(f"Handling connection from {addr} (thread {thread_id})")
    buffer = b""

    try:
        conn.settimeout(60.0)
        while True:
            try:
                data = conn.recv(1024 * 1024)
                if not data:
                    break
                buffer += data
            except socket.timeout:
                break
            except Exception as e:
                logging.error(f"Recv error: {e}", exc_info=True)
                break

            while b"\r\n\r\n" in buffer:
                command_data, buffer = buffer.split(b"\r\n\r\n", 1)
                command_str = command_data.decode()

                future = pool.submit(process_data_task, command_str)
                try:
                    result = future.result(timeout=50)
                except Exception as e:
                    logging.error(f"Future error: {e}")
                    result = json.dumps({'status': 'ERROR', 'data': 'Task failed'})

                conn.sendall((result + "\r\n\r\n").encode())

    except Exception as e:
        logging.error(f"Connection error: {e}", exc_info=True)
    finally:
        conn.close()
        logging.warning(f"Connection from {addr} closed.")

class Server:
    def __init__(self, ip, port, pool_size):
        self.addr = (ip, port)
        self.pool_size = pool_size
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        self.sock.bind(self.addr)
        self.sock.listen(self.pool_size * 5)
        logging.warning(f"Server running at {self.addr} with {self.pool_size} process workers")

        with concurrent.futures.ProcessPoolExecutor(max_workers=self.pool_size) as proc_pool:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.pool_size * 5) as io_pool:
                while True:
                    try:
                        conn, addr = self.sock.accept()
                        io_pool.submit(handle_connection, conn, addr, proc_pool)
                    except KeyboardInterrupt:
                        logging.warning("Shutting down server...")
                        break
                    except Exception as e:
                        logging.error(f"Accept failed: {e}", exc_info=True)
                        break
        self.sock.close()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=6667)
    parser.add_argument('--pool-size', type=int, default=5)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    server = Server('0.0.0.0', args.port, args.pool_size)
    server.run()

