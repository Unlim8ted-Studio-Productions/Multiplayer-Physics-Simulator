import socket

def main():
    # Connect to the server
    server_host = 'localhost'
    server_port = 12345
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_host, server_port))
    
    try:
        while True:
            # Send data to the server
            message = input("Enter message to send: ")
            client_socket.sendall(message.encode())
            
            # Receive response from the server
            data = client_socket.recv(1024)
            print("Received from server:", data.decode())
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
