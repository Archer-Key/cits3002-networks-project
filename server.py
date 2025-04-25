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
from battleship import Board
from multiplayer_battleship import run_multiplayer_game_online

HOST = '127.0.0.1'
PORT = 5000

class Client:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.thread = None
        self.rfile = None
        self.wfile = None

clients = []
MAX_CLIENTS = 2

# Game related globals
game_started = threading.Event()

# Send message from one client to another through server
def send_message_to(dest, msg):
    dest.wfile.write(msg + "\n")
    dest.wfile.flush()

def handle_client(client):
    socket = client.conn
    with socket:
        client.rfile = socket.makefile('r')
        client.wfile = socket.makefile('w')

        # wait for game to start
        player_id = len(clients) - 1
        client.wfile.write(f"Waiting for game to start... [{len(clients)}/2] Players Connected...\n")
        client.wfile.flush()
        while (game_started.is_set() == False):
            pass
        
        # start game
        opponent = clients[1 - player_id]
        run_multiplayer_game_online(client.rfile, client.wfile, opponent)
    
    print("[INFO] Client disconnected.")

# main thread accepts clients in a loop
def main():
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(MAX_CLIENTS)
        num_clients = 0
        while num_clients < MAX_CLIENTS:
            conn, addr = s.accept()
            print(f"[INFO] Client connected from {addr}")

            client = Client(conn, addr)
            
            thread = threading.Thread(target=handle_client, args=[client])
            thread.daemon = True
            client.thread= thread
            
            clients.append(client)
            num_clients += 1
            print(f"Clients accepted [{num_clients}/2].")

            thread.start()
        
        print("Starting game.")
        game_started.set()

        # Keep socket alive once max players reached (to be replaced with accept spectators)
        while(True):
            pass

if __name__ == "__main__":
    main()