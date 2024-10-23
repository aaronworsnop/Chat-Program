import argparse
import select
import socket
import sys
import signal
import ssl
from utils import *

SERVER_HOST = 'localhost'


class ChatServer(object):
    """ An example chat server using select """

    def __init__(self, port, backlog=5):
        self.clients = 0
        self.clientmap = {}
        self.outputs = []  # list output sockets
        self.username_registry = {}  # A simple user registry for authentication

        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
        self.context.load_verify_locations('cert.pem')
        self.context.set_ciphers('AES128-SHA')

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((SERVER_HOST, port))
        self.server.listen(backlog)
        self.server = self.context.wrap_socket(self.server, server_side=True)

        # Catch keyboard interrupts
        signal.signal(signal.SIGINT, self.sighandler)

        print(f'Server listening to port: {port} ...')

    def sighandler(self, signum, frame):
        """ Clean up client outputs"""
        print('Shutting down server...')

        # Close existing client sockets
        for output in self.outputs:
            output.close()

        self.server.close()

    def handle_registration_or_login(self, client):
        """ Handles user registration or login """
        send(client, 'Do you want to [register] or [login]?')
        response = receive(client).lower()

        if response == 'register':
            send(client, 'Enter a username to register:')
            username = receive(client).strip()
            if username in self.username_registry:
                send(
                    client, f'Username {username} already exists. Try logging in.')
                return self.handle_registration_or_login(client)
            else:
                self.username_registry[username] = client
                send(client, f'Registered successfully. Welcome, {username}!')
                return username

        elif response == 'login':
            send(client, 'Enter your username to log in:')
            username = receive(client).strip()
            if username in self.username_registry:
                send(
                    client, f'Logged in successfully. Welcome back, {username}!')
                return username
            else:
                send(client, 'Username not found. Please register or try again.')
                return self.handle_registration_or_login(client)

        else:
            send(
                client, 'Invalid option. Please choose [register] or [login].')
            return self.handle_registration_or_login(client)

    def run(self):
        inputs = [self.server]
        self.outputs = []
        running = True
        while running:
            try:
                readable, writeable, exceptional = select.select(
                    inputs, self.outputs, [])
            except select.error as e:
                break

            for sock in readable:
                sys.stdout.flush()
                if sock == self.server:
                    # handle the server socket
                    client, address = self.server.accept()
                    print(
                        f'Chat server: got connection {client.fileno()} from {address}')

                    # Handle registration or login
                    username = self.handle_registration_or_login(client)

                    # Save the client in the clientmap
                    self.clients += 1
                    self.clientmap[client] = (address, username)
                    inputs.append(client)

                    # Broadcast new client joined
                    msg = f'\n(Connected: New client ({self.clients}) from {username})'
                    for output in self.outputs:
                        send(output, msg)
                    self.outputs.append(client)

                else:
                    # handle all other sockets
                    try:
                        data = receive(sock)
                        if data:
                            # Send as new client's message...
                            msg = f'\n#[{self.get_client_name(sock)}]>> {data}'

                            # Send data to all except ourself
                            for output in self.outputs:
                                if output != sock:
                                    send(output, msg)
                        else:
                            print(f'Chat server: {sock.fileno()} hung up')
                            self.clients -= 1
                            sock.close()
                            inputs.remove(sock)
                            self.outputs.remove(sock)

                            # Sending client leaving information to others
                            msg = f'\n(Now hung up: Client from {self.get_client_name(sock)})'

                            for output in self.outputs:
                                send(output, msg)
                    except socket.error as e:
                        inputs.remove(sock)
                        self.outputs.remove(sock)

        self.server.close()

    def get_client_name(self, client):
        """ Return the name of the client """
        return self.clientmap[client][1]  # Returning only the username


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Socket Server Example with Select')
    parser.add_argument('--port', action="store",
                        dest="port", type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port

    server = ChatServer(port)
    server.run()
