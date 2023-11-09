import socket

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
        self.connections = []
        self.listening = True
        self.socket.bind((self.host, self.port))
        self.listen()
        
    def listen(self):
        ''' Listens on given port. '''
        self.socket.listen()
        print(f'Server ({self.host}): Listening on port {self.port}.')
        
        while self.listening:
            socket_communication, address = self.socket.accept()
            print(f'Server ({self.host}): Connected to {address}.')
            
            data = socket_communication.recv(1024) # receive bytes
            self.connections.append(address)
            self.handle_received(data, socket_communication, len(self.connections)-1)

    def handle_received(self, data, socket, connection_index):
        ''' Handle received data and send appropriate response. '''
        sender = self.connections[connection_index]
        data = data.decode('utf-8')
        print(f'Server ({self.host}): Message from client is "{data}".')

        response = f'Server ({self.host}): Dear {sender}, got your message. Thank you!'
        response = response.encode('utf-8')
        socket.send(response)
        socket.close()
        print(f'Server ({self.host}): Connection with {sender} closed.')
        self.listening = False
