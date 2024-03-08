import socket
import threading

def handle_client(client_socket, address):
    print(f"Accepted connection from {address}")
    
    while True:
        # Receive data from the client
        data = client_socket.recv(1024)
        if not data:
            break
        print(f"Received from {address}: {data.decode()}")
        
        # Echo back to the client
        client_socket.sendall(data)
    
    # Close the connection
    client_socket.close()
    print(f"Connection with {address} closed")

def main():
    # Set up the server
    server_host = 'localhost'
    server_port = 12345
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_host, server_port))
    server_socket.listen(5)
    
    print(f"Server listening on {server_host}:{server_port}")
    
    try:
        while True:
            # Accept incoming connections
            client_socket, client_address = server_socket.accept()
            
            # Create a new thread to handle the client
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
