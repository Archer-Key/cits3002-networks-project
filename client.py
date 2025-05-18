"""
client.py

Connects to a Battleship server which runs the single-player game.
Simply pipes user input to the server, and prints all server responses.
"""

import socket

HOST = '127.0.0.1'
PORT = 5000

import threading

from protocol import *

client_id = None
expected_response = MessageType.CHAT
username = ""

#region Recieve
def receive_messages(s):
    # These two have to be here otherwise they don't work properly when referenced
    global client_id
    global expected_response

    """Continuously receive and display messages from the server"""
    while (True):
        # Read from server
        line = s.recv(BUFSIZE)
        if not line:
            print("[INFO] Server disconnected.")
            break
        
        try:
            msg = Message.decode(line)
            #print(f"DEBUG: seq: {msg.seq}, pck_t: {msg.packet_type}, type: {msg.type}, expected: {msg.expected}, id: {msg.id}, msg: {msg.msg}")
            
            expected_response = msg.expected
            
            type = msg.type
            if type == MessageType.CONNECT:
                client_id = int(msg.msg)

            elif type == MessageType.TEXT:
                print(f"[{msg.id}] {msg.msg}")
            
            elif type == MessageType.CHAT:
                pass
            
            elif type == MessageType.BOARD:
                # Begin reading board lines
                print("\n[Board]")
                board_lines = msg.msg.split('|')
                for line in board_lines:
                    print(line)
            
            elif type == MessageType.PLACE:
                # these don't need to be printed
                pass
            
            elif type == MessageType.RESULT:
                print(msg.msg)
            
            elif type == MessageType.DISCONNECT:
                print("[INFO] you have been disconnected from the server")
                quit()
            
            else:
                # client shouldn't receive a FIRE or NONE message
                # should probably send a NACK or something
                print("Error unexpected message type")

        except ValueError as e:
            # needs to be handled better
            print(f"Failure decoding message, ignoring {e}")
            pass
#endregion

#region Send
def send_messages(s):
    while(True):
        user_input = input(">> ")

        ## handle word inputs to decided type then check mismatch at recieve
        command = user_input.split(" ")
        print(command)

        send_type = expected_response
        print(expected_response)

        match command[0].upper():
            case "FIRE":
                send_type = MessageType.FIRE
                command.pop(0)
            case "PLACE":
                send_type = MessageType.PLACE
                command.pop(0)
            case "CHAT":
                send_type = MessageType.CHAT
                command.pop(0)
            case "USER":
                send_type = MessageType.CONNECT
                command.pop(0)
            case "QUIT":
                send_type = MessageType.DISCONNECT
                command.pop(0)
            case default:
                pass
        
        user_msg = " ".join(command)
        print("user message: " + user_msg)

        msg = Message(id=client_id, type=send_type, expected=MessageType.TEXT, msg=user_msg)
        s.send(msg.encode())

        if send_type == MessageType.DISCONNECT:
            print("quitting")
            quit()
#endregion

#region Connect
def main():
    # set username at start
    print("Welcome to BEER, please enter a username to connect")
    username = ""
    while username == "":
        username = input(">> ")

    # Set up connection
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        
        # Start a thread for receiving messages
        receiver = threading.Thread(target=receive_messages, args=[s])
        receiver.daemon = True # should be repalced with a cleaner exit if needed
        receiver.start()

        while True:
            if client_id != None:
                msg = Message(id=client_id, type=MessageType.CONNECT, expected=MessageType.TEXT, msg=username)
                s.send(msg.encode())
                break

        # Main thread handles sending user input
        try:
            send_messages(s)
        except KeyboardInterrupt:
            print("\n[INFO] Client exiting.")
            msg = Message(id=client_id, type=MessageType.DISCONNECT, expected=MessageType.TEXT, msg=client_id)
            print(msg.encode())
            s.send(msg)
#endregion

if __name__ == "__main__":
    main()