"""
server.py

Serves a single-player Battleship session to one connected client.
Game logic is handled entirely on the server using battleship.py.
Client sends FIRE commands, and receives game feedback.

TODO: For Tier 1, item 1, you don't need to modify this file much. 
The core issue is in how the client handles incoming messages.
However, if you want to support multiple clients (i.e. progress through further Tiers), you'll need concurrency here too.
"""

import time
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
    def set_player(self):
        self.type = ClientType.PLAYER

def send_message_to(client, msg):
    client.wfile.write(msg + "\n") #DO NOT REMOVE THE NEW LINE CHARCTER OR ELSE IT WON'T SEND
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
            raw = rfile.readline()
            if not raw:
                break
            
            print("RECIEVED: " + raw)

            try:
                msg = Message.decode(raw)

                if msg.type == MessageType.CHAT:
                    handle_chat(client, msg)
                    continue
                
                if client.type == ClientType.SPECTATOR:
                    res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "Incorrect message type.")
                    send_message_to(client, res.encode())
                    continue

                player = game.get_player(msg.id)
                if player == None:
                    raise ValueError # a different type of error is probably better here
                
                if game.state == GameState.WAIT:
                    players = len(clients)
                    res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT,\
                                  f"Waiting for game to start... Players connected [{players}/2]")
                    send_message_to(client, res.encode())

                elif game.state == GameState.PLACE:
                    if player.ships_placed < 5:
                        handle_place(client, msg)
                    else:
                      res = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE,\
                                    "All ships placed. Waiting for opponent...")
                      send_message_to(client, res.encode())
                        
                elif game.state == GameState.BATTLE:
                    if game.player_turn == player.player_id:
                        handle_fire(client, msg)
                    else:
                      res = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE,\
                                    "Fire ignored. Waiting for opponent...")
                      send_message_to(client, res.encode())

                elif game.state == GameState.END:
                    res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT,\
                                  "Game has ended. Thank you for playing!")
                    send_message_to(client, res.encode())

                else:
                    print("Error, game is in an unknown state.")

            except ValueError:
                # handle malformed message
                pass
    
    # handle disconnect
    handle_disconnect(client)
    print("[INFO] Client disconnected.")
#endregion

#region Game
class Player:
    def __init__(self, id):
        self.id = id
        self.ships_placed = 0
        self.ship_orientation = 0
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
    
    """
    Set a client as a player.
    """
    def set_player(self, id, client):
        client.set_player()
        self.players[id].client = client

    """
    Get a player object from a client id, returns none if client id does not link to a player.
    """
    def get_player(self, client_id):
        client_ids = [self.players[0].client.id, self.players[1].client.id]
        try:
            index = client_ids.index(client_id)
            return self.players[index]
        except ValueError:
            return None

    """
    Send a player a board.
    """
    def send_board(self, to_player, board, show_hidden=False):
        client = to_player.client

        grid_to_send = board.hidden_grid if show_hidden else board.display_grid
        
        board_msg = ""
        board_msg = board_msg + "  " + " ".join(str(i+1).rjust(2) for i in range(board.size)) + '|'
        for r in range(board.size):
            row_label = chr(ord('A') + r)
            row_str = " ".join(grid_to_send[r][c] for c in range(board.size))
            board_msg = board_msg + f"{row_label:2} {row_str}" + "|"

        msg = Message(SERVER_ID, MessageType.BOARD, MessageType.PLACE, board_msg)
        send_message_to(client, msg.encode())
    """
    Send a message to both players.
    """
    def announce_to_players(self, msg):
        send_message_to(self.players[0].client, msg)
        send_message_to(self.players[1].client, msg)
    
    """
    Wait for two players to connect.
    """
    def wait_for_players(self):
        # Wait for players to connect
        while(len(clients) < 2):
            time.sleep(1)
            pass
        # Start game
        self.set_player(0, clients[0])
        self.set_player(1, clients[1])
        game.state = GameState.PLACE
        # Announce start
        start_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE, "GAME STARTING")
        self.announce_to_players(start_msg.encode())
    
    def place_ships(self):
        # Start placing phase
        self.send_place_prompt(self.players[0])
        self.send_place_prompt(self.players[1])
        # Wait for players to place all ships
        while(self.players[0].ships_placed < 5 or self.players[1].ships_placed < 5):
            time.sleep(1)
            pass
    
    def orientation_str(self, orientation):
        return "vertically" if orientation else "horizontally"
    
    def send_place_prompt(self, player):
        self.send_board(player, player.board, show_hidden=True)
        ship = SHIPS[player.ships_placed] # Next ship to place
        ship_name = ship[0]
        ship_size = ship[1]
        orientation = player.ship_orientation
        
        prompt_msg = f"Place {ship_name} (Size: {ship_size}) {self.orientation_str(orientation)}. Enter 'x' to change orientation."
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE, prompt_msg)
        send_message_to(player.client, msg.encode())
    
    def place_ship(self, ship_name, orientation, coords):
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
def handle_disconnect(client):
    pass

def close_all_connections():
    for client in clients:
        client.conn.close()

# main thread accepts clients in a loop
def main():
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))

        # start the game manager thread
        game_manager = threading.Thread(target=game.run)
        game_manager.daemon = True
        game_manager.start()
        
        num_clients = 0

        # listen for connections
        s.listen(MAX_CLIENTS)
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