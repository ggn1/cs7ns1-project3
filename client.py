import socket

class Client:
    def __init__(self, host_server, port, name):
        self.name = name
        self.host_server = host_server
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
    
    def connect(self):
        ''' Connects to server. '''
        self.socket.connect((self.host_server, self.port))

    def send(self, data):
        ''' Sends data to server and returns response. '''
        data = data.encode('utf-8')
        self.socket.send(data)
        response = socket.recv(1024)
        response = response.decode('utf-8')
        print(f'Client ({self.name}): Response from server ({self.host_server}) is "{response}".')




