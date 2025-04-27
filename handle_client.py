from enum import Enum

from protocol import *
from game import *
from server import clients, game

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
    def set_spectator(self):
        self.type = ClientType.SPECTATOR
        self.player_id = None
    def set_player(self, id):
        self.type = ClientType.PLAYER
        self.player_id = id

def send_message_to(client, msg):
    client.wfile.write(msg + "\n")
    client.wfile.flush()

def send_message_to_all(msg, clients=clients):
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

        # recieve messages from client
        while True:
            raw = rfile.readline().strip()
            try:
                msg = Message.decode(raw)

                if msg.type == "CHAT":
                    handle_chat(client, msg)
                    continue
                
                if client.type == ClientType.SPECTATOR:
                    send_message_to(client, "")
                    continue
                
                if game.state == GameState.WAIT:
                    players = len(clients)
                    send_message_to(client, f"Waiting for game to start... Players connected [{players}/2]")

                elif game.state == GameState.PLACE:
                    if client.ships_placed < 5:
                        handle_place(client, msg)
                    else:
                      send_message_to(client, f"All ships placed. Waiting for opponent...")
                        
                elif game.state == GameState.BATTLE:
                    if game.player_turn == client.player_id:
                        handle_fire(client, msg)
                    else:
                      send_message_to(client, f"Fire ignored. Waiting for opponent...")

                elif game.state == GameState.END:
                    send_message_to(client, f"Game has ended. Thank you for playing!")

                else:
                    print("Error, game is in an unknown state.")

            except ValueError:
                # handle malformed message
                pass
    
    # handle disconnect
    print("[INFO] Client disconnected.")
