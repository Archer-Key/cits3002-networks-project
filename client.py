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
def receive_messages(rfile):
    # These two have to be here otherwise they don't work properly when referenced
    global client_id
    global expected_response

    """Continuously receive and display messages from the server"""
    while (True):
        # Read from server
        line = rfile.readline()
        if not line:
            print("[INFO] Server disconnected.")
            break
        
        line.strip()
        #print("RECIEVED: " + line) # For debugging/testing
        try:
            msg = Message.decode(line)

            #print(f"DECODED: {msg.id} {msg.type} {msg.expected} {msg.msg}\n") # For debugging/testing
            
            expected_response = msg.expected
            
            type = msg.type
            if type == MessageType.CONNECT:
                client_id = msg.msg

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

        except ValueError:
            # needs to be handled better
            print("Failure decoding message, ignoring")
            pass
#endregion

#region Send
def send_messages(wfile):
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

        msg = Message(id=client_id, type=send_type, expected=MessageType.NONE, msg=user_msg)
        wfile.write(msg.encode() + '\n') # DO NOT REMOVE THE NEW LINE CHARACTER OR ELSE IT WON'T SEND
        wfile.flush()

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
        rfile = s.makefile('r')
        wfile = s.makefile('w')
        
        # Start a thread for receiving messages
        receiver = threading.Thread(target=receive_messages, args=[rfile])
        receiver.daemon = True # should be repalced with a cleaner exit if needed
        receiver.start()

        while True:
            if client_id != None:
                msg = Message(id=client_id, type=MessageType.CONNECT, expected=MessageType.NONE, msg=username)
                wfile.write(msg.encode() + '\n')
                wfile.flush()
                break

        # Main thread handles sending user input
        try:
            send_messages(wfile)
        except KeyboardInterrupt:
            print("\n[INFO] Client exiting.")
            msg = Message(id=client_id, type=MessageType.DISCONNECT, expected=MessageType.NONE, msg=client_id)
            print(msg.encode())
            wfile.write(msg.encode() + '\n')
            wfile.flush()
#endregion

if __name__ == "__main__":
    main()