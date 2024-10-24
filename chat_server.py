import argparse
import select
import socket
import sys
import signal
import ssl
from utils import *

SERVER_HOST = 'localhost'


class ChatServer(object):
    """Chat server using select for managing multiple client connections."""

    def __init__(self, port, backlog=5):
        self.clients = 0  # Counter for connected clients
        self.clientmap = {}  # Dictionary of client addresses
        self.outputs = []  # List of output sockets for broadcasting messages
        self.username_registry = {}  # Dictionary of registered usernames
        self.currently_chatting = {}  # Dictionary of clients currently in chat

        # Set up SSL context for secure communication
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
        self.context.load_verify_locations('cert.pem')
        self.context.set_ciphers('AES128-SHA')

        # Create and configure the server socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((SERVER_HOST, port))
        self.server.listen(backlog)
        self.server = self.context.wrap_socket(self.server, server_side=True)

        # Catch keyboard interrupts to shut down gracefully
        signal.signal(signal.SIGINT, self.sighandler)

        print(f'Server listening to port: {port} ...')

    def sighandler(self, signum, frame):
        """Clean up client outputs and close the server on interrupt."""
        print('Shutting down server...')

        # Close all client sockets before shutting down
        for output in self.outputs:
            output.close()

        self.server.close()

    def handle_registration_or_login(self, client):
        """Handles user registration or login processes."""
        try:
            send(client, 'Do you want to [register] or [login]?')
            response = receive(client).lower()

            if not response:
                raise ConnectionError(
                    "Client disconnected during registration/login process.")

            if response == 'register':
                # Handle user registration
                send(client, 'Enter a username to register:')
                username = receive(client).strip()

                if not username:
                    raise ConnectionError(
                        "Client disconnected during username input.")

                if username in self.username_registry:
                    send(
                        client, f'Username "{username}" already exists. Try logging in.')
                    return self.handle_registration_or_login(client)
                else:
                    self.username_registry[username] = client
                    self.currently_chatting[username] = client
                    send(
                        client, f'Registered successfully. Welcome, {username}!')

                    # Notify the client of the number of online users
                    self.notify_online_users(client)
                    return username

            elif response == 'login':
                # Handle user login
                send(client, 'Enter your username to log in:')
                username = receive(client).strip()

                if not username:
                    raise ConnectionError(
                        "Client disconnected during username input.")

                if username in self.username_registry:
                    if username in self.currently_chatting:
                        send(
                            client, f'User "{username}" is already logged in. ')
                        return self.handle_registration_or_login(client)
                    else:
                        send(
                            client, f'Logged in successfully. Welcome back, {username}!')
                        self.currently_chatting[username] = client

                        # Notify the client of the number of online users
                        self.notify_online_users(client)
                        return username
                else:
                    send(client, 'Username not found. Please register or try again.')
                    return self.handle_registration_or_login(client)

            else:
                send(client, 'Invalid option. Please try again.')
                return self.handle_registration_or_login(client)
            
        except (ConnectionError, ssl.SSLError) as e:
            print(f"Error: {e}")
            return None

    def notify_online_users(self, client):
        """Sends a message to the client about the number of online users."""
        count = len(self.currently_chatting) - 1
        if (len(self.currently_chatting) - 1) == 0:
            send(client, 'You are the only user online.')
        elif (len(self.currently_chatting) - 1) == 1:
            send(client, f'There is 1 other user online.')
        else:
            send(
                client, f'There are {len(self.currently_chatting) - 1} other users online.')

    def run(self):
        """Main server loop that handles incoming connections and messages."""
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
                    # Handle new client connections
                    client, address = self.server.accept()
                    print(f'Chat Application server: got connection {client.fileno()} from {address}')

                    # Handle registration or login for the new client
                    username = self.handle_registration_or_login(client)

                    # Registration or login failed
                    if not username: 
                        client.close()
                        continue

                    # Save the client in the clientmap
                    self.clients += 1
                    self.clientmap[client] = (address, username)
                    inputs.append(client)

                    # Broadcast the new client
                    msg = f'\n(Connected: New client connected with username: "{username}")\n'
                    for output in self.outputs:
                        send(output, msg)
                    self.outputs.append(client)

                else:
                    # Handle messages from connected clients
                    try:
                        data = receive(sock)
                        if data:
                            # Check if the message exceeds the character limit
                            if len(data) > 500:
                                warning_msg = "***WARNING*** Your message exceeds the 500 character limit and was not sent."
                                # Inform the user their message is too long
                                send(sock, warning_msg)

                            else:
                                # Send as new client's message
                                msg = f'| [{self.get_client_name(sock)}]: {data}'

                                # Broadcast the message
                                for output in self.outputs:
                                    if output != sock:
                                        send(output, msg)
                        else:
                            username = self.get_client_name(sock)
                            print(f'Chat server: {sock.fileno()} ("{username}") hung up')
                            self.clients -= 1
                            sock.close()
                            inputs.remove(sock)
                            self.outputs.remove(sock)

                            # Remove the user from the currently chatting list
                            if username in self.currently_chatting:
                                del self.currently_chatting[username]

                            # Broadcast the disconnection
                            msg = f'\n(Disconnected: Client "{username}" disconnected from the chat)\n'
                            for output in self.outputs:
                                send(output, msg)

                    except socket.error as e:
                        # Handle socket errors and clean up
                        inputs.remove(sock)
                        self.outputs.remove(sock)

        self.server.close()

    def get_client_name(self, client):
        """Return the name of the client"""
        return self.clientmap[client][1]  


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Socket Server Example with Select')
    parser.add_argument('--port', action="store",
                        dest="port", type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port

    server = ChatServer(port)
    server.run()
