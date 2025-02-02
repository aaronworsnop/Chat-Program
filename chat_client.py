import argparse
import select
import socket
import sys
import threading
import ssl
from utils import *

SERVER_HOST = 'localhost'

stop_thread = False


def get_and_send(client):
    """Get user input and send to server."""
    while not stop_thread:
        data = sys.stdin.readline().strip()
        if data:
            send(client.sock, data)


class ChatClient():
    """Chat client using select"""

    def __init__(self, port, host=SERVER_HOST):
        self.connected = False
        self.host = host
        self.port = port

        # Set up SSL context for secure communication
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.set_ciphers('AES128-SHA')

        # Connect to server at given host and port
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
            self.sock.connect((host, self.port))
            print(f'Now connected to chat server@ port {self.port}')
            self.connected = True

            # Register or login
            data = receive(self.sock)
            print(data)
            choice = input('> ').strip().lower()
            send(self.sock, choice)

            # Process username input
            username_prompt = receive(self.sock)

            # Check if client selected "register" or "login" correctly
            if 'Invalid' in username_prompt:
                print(username_prompt)
                self.connected = False
                self.sock.close()
                return
            else:
                print(username_prompt)
                username = input('> ').strip()
                send(self.sock, username)

            # Check if registration/login was successful before setting the username
            msg = receive(self.sock)
            print(msg)

            if 'Welcome' in msg:  
                # The user is now logged in
                self.prompt = f''
                threading.Thread(target=get_and_send, args=(self,)).start()
            else:
                # The user failed to log in or register
                print("Failed to log in or register. Exiting.")
                self.connected = False
                self.sock.close()

        except socket.error as e:
            print(f'Failed to connect to chat server @ port {self.port}')
            sys.exit(1)

    def cleanup(self):
        """Close the connection and wait for the thread to terminate."""
        self.sock.close()

    def run(self):
        """Chat client main loop."""
        while self.connected:
            try:
                sys.stdout.write(self.prompt)
                sys.stdout.flush()

                readable, _, _ = select.select([self.sock], [], [])

                # Handle incoming messages
                for sock in readable:
                    if sock == self.sock:
                        data = receive(self.sock)
                        if not data:
                            print('Client shutting down.')
                            self.connected = False
                            break
                        else:
                            sys.stdout.write(data + '\n')
                            sys.stdout.flush()

            # Handle keyboard interrupts
            except KeyboardInterrupt:
                print(" Client interrupted.")
                self.cleanup()
                break


if __name__ == "__main__":
    """Parse command line arguments and start the chat client."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', action="store",
                        dest="port", type=int, required=True)
    given_args = parser.parse_args()

    port = given_args.port

    client = ChatClient(port=port)
    client.run()
