"""
server.py

Serves a single-player Battleship session to one connected client.
Game logic is handled entirely on the server using battleship.py.
Client sends FIRE commands, and receives game feedback.

TODO: For Tier 1, item 1, you don't need to modify this file much. 
The core issue is in how the client handles incoming messages.
However, if you want to support multiple clients (i.e. progress through further Tiers), you'll need concurrency here too.
"""

import socket
import threading
from battleship import run_single_player_game_online

HOST = '127.0.0.1'
PORT = 5000
MAX_CLIENTS = 2

class Client:
    def __init__(self, conn, addr, thread):
        self.conn = conn
        self.addr = addr
        self.thread = thread

def handle_client(conn):
    with conn:
        rfile = conn.makefile('r')
        wfile = conn.makefile('w')
        run_single_player_game_online(rfile, wfile)
    print("[INFO] Client disconnected.")

def main():
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(MAX_CLIENTS)
        clients = []
        num_clients = 0
        while num_clients < MAX_CLIENTS:
            conn, addr = s.accept()
            print(f"[INFO] Client connected from {addr}")
            
            thread = threading.Thread(target=handle_client, args=[conn])
            thread.start()
            
            clients.append(Client(conn, addr, thread))
            num_clients += 1
            print(f"Clients accepted [{num_clients}/2].")
        
        print("Starting game.")

if __name__ == "__main__":
    main()