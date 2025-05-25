import socket
import json
import base64
import logging

server_address = ('172.16.16.101', 6666)

def send_command(command_str=""):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        sock.connect(server_address)
        logging.warning(f"Connecting to {server_address}")
        

        if not command_str.endswith('\\r\\n\\r\\n'):
            command_str += '\\r\\n\\r\\n'
            
        sock.sendall(command_str.encode())
        
        data_received = b""
        while True:
            # Terima data dalam buffer yang lebih besar
            data = sock.recv(4096)
            if data:
                data_received += data
                # Cek terminator di data yang diterima
                if data_received.endswith(b'\\r\\n\\r\\n'):
                    break
            else:
                # Koneksi ditutup oleh server
                break
        
        # Proses hanya jika data diterima
        if data_received:
            # Hapus terminator sebelum parsing JSON
            hasil_str = data_received.decode().strip()
            return json.loads(hasil_str)
        else:
            # Jika tidak ada data, kembalikan dictionary error
            return {'status': 'ERROR', 'data': 'No response from server'}

    except (socket.error, json.JSONDecodeError, Exception) as e:
        logging.warning(f"Error during communication: {e}")
        # Kembalikan dictionary error, BUKAN False
        return {'status': 'ERROR', 'data': str(e)}
    finally:
        sock.close()

def remote_list():
    command_str=f"LIST\r\n\r\n"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print("daftar file : ")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print("Gagal")
        return False
    
def remote_post(filename=""):
    file = open(filename,'rb')
    isifile = base64.b64encode(file.read()).decode()
    command_str=f"POST {filename} {isifile}\r\n\r\n"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print("File berhasil dikirim")
        return True
    else:
        print("Gagal Upload")

def remote_get(filename=""):
    command_str = f"GET {filename}"
    hasil = send_command(command_str)
    if (hasil['status'] == 'OK'):
        namafile = hasil['data_namafile']
        isifile = base64.b64decode(hasil['data_file'])
        with open(namafile, 'wb+') as fp:
            fp.write(isifile)
        print(f'File saved as: {namafile}')
        return True
    else:
        print("Gagal GET")
        return False

def remote_delete(filename=""):
    command_str=f"DELETE {filename}"
    hasil = send_command(command_str)
    if hasil['status']=='OK':
        print("File berhasil dihapus")
        return True
    else:
        print("Gagal Delete")
        return False

if __name__ == '__main__':
    while True:
        cmd = input("Command (list/get/post/delete/exit): ").strip()
        if cmd == 'list':
            remote_list()
        elif cmd == 'get':
            fname = input("Filename: ")
            remote_get(fname)
        elif cmd == 'post':
            fname = input("Filename: ")
            remote_post(fname)
        elif cmd == 'delete':
            fname = input("Filename: ")
            if remote_delete(fname):
                print("File berhasil dihapus.")
            else:
                print("Gagal menghapus file.")
        elif cmd == 'exit':
            break
        else:
            print("Perintah tidak dikenali")
