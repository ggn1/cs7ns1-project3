import socket

HOST = '10.10.4.227' # Server's IP address.
PORT = 3000 # Server's port.

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect((HOST, PORT))
message = 'Hello World!'
message = message.encode('utf-8')
socket.send(message)
response = socket.recv(1024)
response = response.decode('utf-8')
print(response)
