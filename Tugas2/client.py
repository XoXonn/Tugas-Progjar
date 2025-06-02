import socket

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', 45000))
        
        while True:
            message = input("Enter a command (TIME/QUIT): ").strip()
            
            if message.upper() == "QUIT":
                s.sendall(b'QUIT\r\n')
                break
            elif message.upper() == "TIME":
                s.sendall(b'TIME\r\n')
                response = s.recv(1024)
                print("Response from server:", response.decode('utf-8').strip())
            else:
                print("Invalid command. Please enter TIME or QUIT.")

if __name__ == "__main__":
    main()
