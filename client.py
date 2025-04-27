"""
client.py

Connects to a Battleship server which runs the single-player game.
Simply pipes user input to the server, and prints all server responses.

TODO: Fix the message synchronization issue using concurrency (Tier 1, item 1).
"""

import socket

HOST = '127.0.0.1'
PORT = 5000

# HINT: The current problem is that the client is reading from the socket,
# then waiting for user input, then reading again. This causes server
# messages to appear out of order.
#
# Consider using Python's threading module to separate the concerns:
# - One thread continuously reads from the socket and displays messages
# - The main thread handles user input and sends it to the server
#
import threading

from protocol import *

client_id = None
expected_response = MessageType.CHAT

def receive_messages(rfile):
    """Continuously receive and display messages from the server"""
    while (True):
        # Read from server
        line = rfile.readline()
        if not line:
            print("[INFO] Server disconnected.")
            break
        
        line.strip()
        try:
            msg = Message.decode(line)
            
            expected_response = msg.expected
            
            type = msg.type
            if type == MessageType.CONNECT:
                client_id = msg.msg

            elif type == MessageType.TEXT:
                print(f"[{msg.id}] {msg}")
            
            elif type == MessageType.CHAT:
                pass
            
            elif type == MessageType.BOARD:
                # Begin reading board lines
                print("\n[Board]")
                while True:                                                   
                    board_line = rfile.readline()                             
                    if not board_line or board_line.strip() == "":            
                        break                                                 
                    print(board_line.strip())                                 
            
            elif type == MessageType.PLACE:
                pass
            
            elif type == MessageType.RESULT:
                pass
            
            else:
                # client shouldn't receive a FIRE or NONE message
                # should probably send a NACK or something
                print("Error")

        except ValueError:
            pass

def send_messages(wfile):
    while(True):
        user_input = input(">> ")
        msg = Message(id=client_id, type=expected_response, expected=MessageType.NONE, msg=user_input)
        wfile.write(msg.encode())
        wfile.flush()

def main():
    # Set up connection
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        rfile = s.makefile('r')
        wfile = s.makefile('w')
        
        # Start a thread for receiving messages
        receiver = threading.Thread(target=receive_messages, args=[rfile])
        receiver.daemon = True # should be repalced with a cleaner exit if needed
        receiver.start()

        # Main thread handles sending user input
        try:
            send_messages(wfile)
        except KeyboardInterrupt:
            print("\n[INFO] Client exiting.")

if __name__ == "__main__":
    main()