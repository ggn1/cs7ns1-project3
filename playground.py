# Stepping stone to success.
import socket
from server import Server

N_CLIENTS = 1

if __name__ == '__main__':
    server = Server(host=socket.gethostbyname(socket.gethostname()), port=5050)
    for client in N_CLIENTS