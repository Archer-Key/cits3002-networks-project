"""
server.py

Serves a single-player Battleship session to one connected client.
Game logic is handled entirely on the server using battleship.py.
Client sends FIRE commands, and receives game feedback.

TODO: For Tier 1, item 1, you don't need to modify this file much. 
The core issue is in how the client handles incoming messages.
However, if you want to support multiple clients (i.e. progress through further Tiers), you'll need concurrency here too.
"""

# standard modules
import socket
import threading

# communication
from protocol import *
from handle_client import Client, handle_client

# game related
from game import *
from battleship import Board
from multiplayer_battleship import run_multiplayer_game_online

HOST = '127.0.0.1'
PORT = 5000

MAX_CLIENTS = 2
clients = [] # should store this as a heap so that we can pop random clients

game = Game()

def close_all_connections():
    for client in clients:
        client.conn.close()

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
        
        # Start game
        print("Starting game.")
        clients[0].set_player(0)
        clients[1].set_player(1)
        game.start(players=[clients[0], clients[1]])

        # Keep socket alive, ignore any other clients
        while True:
            pass

if __name__ == "__main__":
    main()