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
from random import randint
from battleship import Board
from multiplayer_battleship import run_multiplayer_game_online

HOST = '127.0.0.1'
PORT = 5000

from enum import Enum

class ClientType(Enum):
    SPECTATOR = 0
    PLAYER = 1

class Client:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.thread = None
        self.rfile = None
        self.wfile = None
        self.type = ClientType.SPECTATOR
        self.player_id = None
        self.board = None
    def set_spectator(self):
        self.type = ClientType.SPECTATOR
        self.player_id = None
    def set_player(self, id):
        self.type = ClientType.PLAYER
        self.player_id = id
    def set_board(self, board):
        if (self.type == ClientType.PLAYER):
            self.board = board

MAX_CLIENTS = 2
clients = []

class Game:
    def __init__(self):
        self.players = None
        self.player_turn = None
        self.active = False
    def start(self, players):
        self.active = True
        self.players = players
        print(self.players)
    def start_battle(self):
        if (self.player_turn == None): # temporary solution as currently both players call start_battle when ready
            self.player_turn = randint(0,1)
            send_message_to_all(self.players, "\n THE BATTLE BEGINS")
    def end_turn(self):
        self.player_turn = 1 - self.player_turn
    def end(self):
        self.active = False

game = Game()

# Send message from one client to another through server
def send_message_to(client, msg):
    client.wfile.write(msg + "\n")
    client.wfile.flush()

def send_message_to_all(clients=clients, msg=""):
    for client in clients:
        send_message_to(client, msg)

def handle_client(client):
    socket = client.conn
    with socket:
        client.rfile = socket.makefile('r')
        client.wfile = socket.makefile('w')

        # wait for game to start
        player_id = len(clients) - 1
        client.wfile.write(f"Waiting for game to start... [{len(clients)}/2] Players Connected...\n")
        client.wfile.flush()

        while (game.active == False):
            pass
        
        # start game
        opponent = clients[1 - player_id]
        run_multiplayer_game_online(client, opponent, game)
    
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