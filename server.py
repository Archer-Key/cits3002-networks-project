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
from enum import Enum

from protocol import *
from battleship import *

HOST = '127.0.0.1'
PORT = 5000

SERVER_ID = 0

#region Clients
MAX_CLIENTS = 2
clients = [] # should store this as a heap/queue/something so that we can pop random clients

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
        self.id = None
        self.type = ClientType.SPECTATOR
    def set_spectator(self):
        self.type = ClientType.SPECTATOR
    def set_player(self, id):
        self.type = ClientType.PLAYER

def send_message_to(client, msg):
    client.wfile.write(msg + "\n")
    client.wfile.flush()

def send_message_to_all(clients, msg):
    for client in clients:
        send_message_to(client, msg)

def handle_chat(client, msg):
    pass

def handle_place(client, msg):
    pass

def handle_fire(client, msg):
    pass

def handle_client(client):
    socket = client.conn
    with socket:
        rfile = socket.makefile('r')
        wfile = socket.makefile('w')
        client.rfile = rfile
        client.wfile = wfile

        # send client their client ID
        id_msg = Message(id=SERVER_ID, type=MessageType.CONNECT, expected=MessageType.CHAT, msg=client.id)
        send_message_to(client, id_msg.encode())

        # recieve messages from client
        while True:
            raw = rfile.readline().strip()
            print(raw)

            try:
                msg = Message.decode(raw)

                if msg.type == MessageType.CHAT:
                    handle_chat(client, msg)
                    continue
                
                if client.type == ClientType.SPECTATOR:
                    res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "Incorrect message type.")
                    send_message_to(client, res.encode())
                    continue
                
                if game.state == GameState.WAIT:
                    players = len(clients)
                    res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT,\
                                  f"Waiting for game to start... Players connected [{players}/2]")
                    send_message_to(client, res.encode())

                elif game.state == GameState.PLACE:
                    if client.ships_placed < 5:
                        handle_place(client, msg)
                    else:
                      res = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE, "All ships placed. Waiting for opponent...")
                      send_message_to(client, res.encode())
                        
                elif game.state == GameState.BATTLE:
                    if game.player_turn == client.player_id:
                        handle_fire(client, msg)
                    else:
                      res = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE, "Fire ignored. Waiting for opponent...")
                      send_message_to(client, res.encode())

                elif game.state == GameState.END:
                    res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "Game has ended. Thank you for playing!")
                    send_message_to(client, res.encode())

                else:
                    print("Error, game is in an unknown state.")

            except ValueError:
                # handle malformed message
                pass
    
    # handle disconnect
    print("[INFO] Client disconnected.")
#endregion

#region Game
class Player:
    def __init__(self, id):
        self.id = id
        self.ships_placed = 0
        self.board = Board()
        self.moves = 0
        self.client = None
    def set_client(self, client):
        self.client = client
        return self.id

class GameState(Enum):
    WAIT = 0
    PLACE = 1
    BATTLE = 2
    END = 3

class Game:
    def __init__(self):
        self.state = GameState.WAIT
        self.players = [Player(0), Player(1)]
        self.player_turn = None
    
    def set_player(self, id, client):
        client.set_player()
        self.players[id].client = client
    
    def send_board(self):
        pass
    
    def wait_for_players(self):
        # Wait for players to connect
        while(len(clients) < 2):
            pass
        # Start game
        self.set_player(0, clients[0])
        self.set_player(1, clients[1])
        game.state = GameState.PLACE
        # Announce start
        start_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE, "")
        send_message_to_all(self.players, start_msg.encode())
    
    def place_ships(self):
        pass

    def battle(self):
        pass
    
    def end(self):
        pass

    def run(self):
        self.wait_for_players()
        self.place_ships()
        self.battle()
        self.end()

game = Game()
game_manager = None
#endregion

#region Connections
def close_all_connections():
    for client in clients:
        client.conn.close()

# main thread accepts clients in a loop
def main():
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))

        # start the game manager thread
        #game_manager = threading.Thread(target=game.run())
        #game_manager.start()

        # listen for connections
        s.listen(MAX_CLIENTS)
        num_clients = 0
        while num_clients < MAX_CLIENTS:
            conn, addr = s.accept()
            print(f"[INFO] Client connected from {addr}")

            client = Client(conn, addr)
            clients.append(client)
            num_clients += 1
            client.id = num_clients # can probably replace this with a classmethod

            thread = threading.Thread(target=handle_client, args=[client])
            thread.daemon = True
            client.thread = thread
            thread.start()

        # Keep socket alive (This will be replaced eventually)
        print("Clients full")
        while True:
            pass
#end region

if __name__ == "__main__":
    main()