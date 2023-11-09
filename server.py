import socket

HOST = socket.gethostbyname('CinderHeart') # Own IP
PORT = 3000

server = socket.socket( # Only for accepting connections.
    socket.AF_INET,
    socket.SOCK_STREAM
)
server.bind((HOST, PORT))

server.listen(5)

while True:
    communication_socket, address = server.accept()
    print(f'Connected to {address}.')
    message = communication_socket.recv(1024) # receive bytes
    message = message.decode('utf-8')
    print(f'Message from client is: {message}.')
    response = 'Got your message! Thank you!'
    response = response.encode('utf-8')
    communication_socket.send(response)
    communication_socket.close()
    print(f'Connection with {address} closed.')