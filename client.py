"""
client.py

Connects to a Battleship server which runs the single-player game.
Simply pipes user input to the server, and prints all server responses.
"""

import socket

HOST = '127.0.0.1'
PORT = 5000

import threading

import heapq

from protocol import *

client_id = None
expected_response = MessageType.CHAT
username = ""

seq_s = 0
send_window = []

seq_r = 0
recv_window = []

#region Recieve
def process_messages(s):
    global client_id
    global expected_response
    global recv_window
    global seq_r
    global send_window
    global seq_s

    while True:
        try:
            msg = heapq.heappop(recv_window)[1]
        except IndexError: # all messages sent
            return
        
        if msg.seq < seq_r: # skip duplicates
            continue

        if msg.seq > seq_r: # end if message is a future packet
            heapq.heappush(recv_window, (msg.seq, msg))
            send_ack(s, seq_r)
            return 
        
        # process the message
        try:
            type = msg.type
            expected_response = msg.expected

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
                print("Error unexpected message type")
                send_nack(s)
                return
            
            # all went well
            seq_r += 1

        except ValueError as e:
            # needs to be handled better
            print("#####\n"*5)
            print(f"Failure decoding message, ignoring {e}")
            print("#####\n"*5)
            return

def receive_messages(s):
    # These have to be here otherwise they don't work properly when referenced
    global client_id
    global expected_response
    global recv_window
    global seq_r
    global send_window
    global seq_s

    """Continuously receive and display messages from the server"""
    while (True):
        # Read from server
        raw = s.recv(BUFSIZE)
        
        if not raw:
            print("[INFO] Server disconnected.")
            break
        
        try:
            msg = Message.decode(raw)
            #print(f"DEBUG: seq: {msg.seq}, pck_t: {msg.packet_type}, type: {msg.type}, expected: {msg.expected}, id: {msg.id}, msg: {msg.msg}\n\n\n")

            if msg.packet_type == PacketType.ACK:
                sent = heapq.heappop(send_window)
                while (sent[0] < msg.seq):
                    sent = heapq.heapop(send_window)
                heapq.heappush(send_window, sent) # push the last element popped back on
                continue
            
            if msg.packet_type == PacketType.NACK: # resend all messages
                messages = send_window.copy()
                while True:
                    try:
                        send_msg(s, heapq.heappop(messages)[1], False) 
                    except IndexError:
                        break
                continue
            
            if (msg.seq > seq_r): # queue future packets
                heapq.heappush(recv_window, (msg.seq, msg))
                continue
            
            if (msg.seq < seq_r): #ignore already received packets
                continue

            process_messages(s)
                    
        except ChecksumMismatchError:
            send_nack(s)
#endregion

#region Send
def send_msg(s, msg, new=True):
    encoded = msg.encode()
    s.send(encoded)
    if new:
        send_window.headpush(send_window, (msg.seq, msg))
        seq_s += 1

def send_ack(s, seq):
    ack = Message(id=client_id, type=MessageType.TEXT, expected=MessageType.TEXT, msg="",\
                           seq=seq, packet_type=PacketType.ACK)
    send_msg(s, ack, False)

def send_nack(s):
    nack = Message(id=client_id, type=MessageType.TEXT, expected=MessageType.TEXT, msg="",\
                           seq=0, packet_type=PacketType.NACK)
    send_msg(s, nack, False)

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

        msg = Message(id=client_id, type=send_type, expected=MessageType.TEXT, msg=user_msg, seq=seq_s)
        send_msg(s, msg)
        
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
                send_msg(s, msg)
                break

        # Main thread handles sending user input
        try:
            send_messages(s)
        except KeyboardInterrupt:
            print("\n[INFO] Client exiting.")
            msg = Message(id=client_id, type=MessageType.DISCONNECT, expected=MessageType.TEXT, msg=client_id)
            send_msg(s, msg)
#endregion

if __name__ == "__main__":
    main()