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
from random import randint

from protocol import *
from battleship import *

HOST = '127.0.0.1'
PORT = 5000

SERVER_ID = 0

#region Clients
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
#endregion

#region Handle Client
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

        # send client a message indicating their status
        if game.state == GameState.WAIT:
            game.send_waiting_message(client)
        elif game.state in (GameState.PLACE, GameState.BATTLE):
            spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "YOU CURRENTLY SPECTATING")
            send_message_to(client, spec_msg.encode())
        elif game.state == GameState.END:
            spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "WAITING FOR NEW GAME TO START")
            send_message_to(client, spec_msg.encode())

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
                    game.send_waiting_message(client)
                    
                elif game.state == GameState.PLACE:
                    game.place_ship(client.id, msg.msg)
                        
                elif game.state == GameState.BATTLE:
                    game.fire(client.id, msg.msg)

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
        self.new_game()
        self.game_number = 0
    def new_game(self):
        self.state = GameState.WAIT
        self.players = [Player(0), Player(1)]
        self.player_turn = None
#endregion

#region Player Handling
    """
    Sets a client as a spectator and removes them from the player list if they were previously a player.
    """
    def set_spectator(self, client, send_msg=False):
        player_id = self.get_player(client.id)
        if (player_id != None):
            self.players[player_id] == None
        client.set_spectator()
        if (send_msg):
            msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"YOU ARE A SPECTATOR")
            send_message_to(client, msg.encode())

    """
    Set a client as a player.
    """
    def set_player(self, player_id, client):
        client.set_player()
        self.players[player_id].client = client
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"YOU ARE PLAYER {player_id}")
        send_message_to(client, msg.encode())

    """
    Decide on the next two players and set them as players.
    """
    def set_players(self):
        num_clients = len(clients)
        p0_index = (2*self.game_number)%(num_clients)
        p1_index = (p0_index + 1)%(num_clients)
        self.set_player(0, clients[p0_index])
        self.set_player(1, clients[p1_index])
    
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
    Return the opponent of player.
    """
    def get_opponent(self, player):
        return self.players[1 - player.id]
    
    """
    Handle player disconnect.
    """
    def handle_player_disconnect(self, player):
        pass
    
    """
    Handle a player quitting the match.
    """
    def handle_player_quit(self, player):
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "Thanks for playing!")
        send_message_to(player.client, msg.encode())
        
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "Other player has decided to quit. Thanks for playing!")
        send_message_to(self.get_opponent(player).client, msg.encode())
        
        self.state = GameState.END
        close_all_connections()
#endregion

#region Game Messages
    """
    Send a waiting message.
    """
    def send_waiting_message(self, client):
        num_clients = len(clients)
        res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT,\
                      f"Waiting for game to start... Clients connected [{num_clients}/2]")
        send_message_to(client, res.encode())

    """
    Convert a board into a sendable string.
    """
    def board_to_str(self, board, show_hidden=False):
        grid_to_send = board.hidden_grid if show_hidden else board.display_grid
        
        board_msg = ""
        board_msg = board_msg + "  " + " ".join(str(i+1).rjust(2) for i in range(board.size)) + '|'
        for r in range(board.size):
            row_label = chr(ord('A') + r)
            row_str = " ".join(grid_to_send[r][c] for c in range(board.size))
            board_msg = board_msg + f"{row_label:2} {row_str}" + "|"
        
        return board_msg
    
    """
    Send a player a board.
    """
    def send_board(self, to_player, board, show_hidden=False):
        client = to_player.client
        board_msg = self.board_to_str(board, show_hidden)
        msg = Message(SERVER_ID, MessageType.BOARD, MessageType.PLACE, board_msg)
        send_message_to(client, msg.encode())
        if self.state == GameState.BATTLE:
            spec_msg = Message(SERVER_ID, MessageType.BOARD, MessageType.CHAT, board_msg)
            self.announce_to_spectators(spec_msg.encode())
    
    """
    Send a message to both players.
    """
    def announce_to_players(self, msg):
        send_message_to(self.players[0].client, msg)
        send_message_to(self.players[1].client, msg)

    """
    Send a message to all spectators.
    """
    def announce_to_spectators(self, msg):
        player0id = self.players[0].client.id
        player1id = self.players[1].client.id
        for client in clients:
            if (client.id not in (player0id, player1id)):
                send_message_to(client, msg)

#endregion

#region Place Stage
    """
    Convert an orientation number code into the respective string.
    """
    def orientation_str(self, orientation):
        return "vertically" if orientation else "horizontally"
    
    """
    Send the player a prompt to place a ship.
    """
    def send_place_prompt(self, player):
        if (player.ships_placed >= 5):
            self.send_board(player, player.board, show_hidden=True)
            msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "All ships placed. Waiting for opponent...")
            send_message_to(player.client, msg.encode())
            return

        self.send_board(player, player.board, show_hidden=True)
        ship_name, ship_size = SHIPS[player.ships_placed] # Next ship to place
        orientation = player.ship_orientation
        
        prompt_msg = f"Place {ship_name} (Size: {ship_size}) {self.orientation_str(orientation)}. Enter 'x' to change orientation."
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE, prompt_msg)
        send_message_to(player.client, msg.encode())

    """
    Attempts to place a ship in the coordinates provided.
    
    Called by the client handler when a user sends a PLACE message.
    """ 
    def place_ship(self, client_id, coords):
        player = self.get_player(client_id)
        if player == None:
            # handle error if player is None
            raise ValueError
        
        board = player.board
        ship_name, ship_size = SHIPS[player.ships_placed] # Next ship to place
        orientation = player.ship_orientation

        if (player.ships_placed >= 5):
            msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "All ships placed. Waiting for opponent...")
            send_message_to(player.client, msg.encode())
            return
        
        # Get coordinates from message
        coords = coords.strip().upper()
        try:
            # Change orientation
            if coords[0] == 'X':
                player.ship_orientation = 1 - player.ship_orientation
                self.send_place_prompt(player)
                return
            # Coordinates
            row, col = parse_coordinate(coords)
        except ValueError as e:
            msg = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE, f"[!] Invalid coordinate: {e}")
            send_message_to(player.client, msg.encode())
            self.send_place_prompt(player)
            return
        
        # Check if we can place the ship
        if board.can_place_ship(row, col, ship_size, orientation):
            occupied_positions = board.do_place_ship(row, col, ship_size, orientation)
            board.placed_ships.append({
                "name": ship_name,
                "positions": occupied_positions
            })
            player.ships_placed += 1
            spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"PLAYER {player.id} PLACED THEIR {ship_name}")
            self.announce_to_spectators(spec_msg.encode())
        else:
            msg = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE,\
            f"[!] Cannot place {ship_name} at {coords} (orientation={self.orientation_str(orientation)}). Try again.")
        
        # Send player next prompt
        self.send_place_prompt(player)
#endregion

#region Fire Stage
    """
    End a players turn.
    """
    def end_player_turn(self, player):
        player.moves += 1
        self.player_turn = 1 - player.id
        opponent = self.get_opponent(player)
        # Check that the opponent hasn't lost
        if not opponent.board.all_ships_sunk():
            self.send_fire_prompt(opponent)
    
    """
    Prompt the player to fire.
    """
    def send_fire_prompt(self, player):
        # Send the opponents board
        opponent = self.get_opponent(player)
        self.send_board(player, opponent.board)
        # Prompt the player to fire
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE,\
                      f"Enter coordinate to fire at (e.g. B5): ")
        send_message_to(player.client, msg.encode())
        spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"PLAYER {player.id} FIRING")
        self.announce_to_spectators(spec_msg.encode())
    
    """
    Attempts to fire at a tile of the opponents board.

    Called by the client handler when the user sends a FIRE message.
    """
    def fire(self, client_id, coords): # Use client_id here because it comes from the message
        # Get the player who send the fire message
        player = self.get_player(client_id)
        if (player == None):
            raise ValueError
            # handle this properly
        
        # Check for quit
        coords = coords.strip().upper()
        if coords == "QUIT":
            self.handle_player_quit(player)
            return
        
        # Check that it's the player's turn
        if (player.id != self.player_turn):
            msg = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE,\
                          "Fired out turn, command ignored. Waiting for opponent to fire...")
            send_message_to(player.client, msg.encode())
            return
        
        opponent = self.get_opponent(player)
        
        # Attempt fire
        try:
            row, col = parse_coordinate(coords)
            result, sunk_name = opponent.board.fire_at(row, col)

            # Let the player fire again if already shot
            if result == "already_shot":
                msg = Message(SERVER_ID, MessageType.RESULT, MessageType.FIRE,\
                              "REPEAT You've already fired at that location.")
                send_message_to(player.client, msg.encode())
                self.send_fire_prompt(player)
                return
            
            # Otherwise will change turn
            res_txt = ""
            opp_txt = ""
            spec_txt = ""
            if result == 'hit':
                if sunk_name:
                    res_txt = f"HIT You sank the {sunk_name}!"
                    opp_txt = f"OPPONENT HIT {coords}! Opponent sunk your {sunk_name}!"
                    spec_txt = f"PLAYER {player.id} FIRED AT {coords} AND HIT! PLAYER {player.id} SANK PLAYER {opponent.id}'s {sunk_name}!"
                else:
                    res_txt = "HIT"
                    opp_txt = f"OPPONENT HIT {coords}!"
                    spec_txt = f"PLAYER {player.id} FIRED AT {coords} AND HIT!"
            elif result == 'miss':
                res_txt = "MISS"
                opp_txt = "OPPONENT MISSED"
                spec_txt = f"PLAYER {player.id} FIRED AT {coords} AND MISSED!"

            # Send result to player
            self.send_board(player, opponent.board)
            res_msg = Message(SERVER_ID, MessageType.RESULT, MessageType.FIRE, res_txt)
            send_message_to(player.client, res_msg.encode())
            # Send result to opponent
            opp_msg = Message(SERVER_ID, MessageType.RESULT, MessageType.FIRE, opp_txt)
            send_message_to(opponent.client, opp_msg.encode())
            # Announce result to spectators
            spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, spec_txt)
            self.announce_to_spectators(spec_msg.encode())
            # End turn
            self.end_player_turn(player)
        
        except ValueError as e:
            msg = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE, f"Invalid input: {e}")
            send_message_to(player.client, msg.encode())
            self.send_fire_prompt(player)
#endregion

#region Run Game
    def play_game(self):
        self.new_game()
        
        # Wait for players to connect
        while(len(clients) < 2):
            time.sleep(1)
        
        # Announce start
        start_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "GAME STARTING")
        send_message_to_all(clients, start_msg.encode())
        self.state = GameState.PLACE

        # Announce players
        self.set_players()
                
        # Announce spectators
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"YOU ARE A SPECTATOR")
        self.announce_to_spectators(msg.encode())

        # Start placing phase
        self.send_place_prompt(self.players[0])
        self.send_place_prompt(self.players[1])
        
        # Wait for players to place all ships
        while((self.players[0].ships_placed < 5 or self.players[1].ships_placed < 5) and self.state == GameState.PLACE):
            time.sleep(1)
        self.state = GameState.BATTLE

        # Start battle
        battle_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE, "BATTLE STARTING")
        self.announce_to_players(battle_msg.encode())
        self.player_turn = randint(0,1)
        # Send prompt to player who's turn is first and wait to other player
        self.send_fire_prompt(self.players[self.player_turn])
        wait_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE, "Waiting for opponent...")
        send_message_to(self.players[1 - self.player_turn].client, wait_msg.encode())

        # Wait for battle to end
        winner = None
        loser = None
        while self.state == GameState.BATTLE:
            if (self.players[0].board.all_ships_sunk()):
                winner = self.players[1]
                loser = self.players[0]
                break
            elif (self.players[1].board.all_ships_sunk()):
                winner = self.players[0]
                loser = self.players[1]
                break
            time.sleep(1)
        self.state = GameState.END
        
        # End game
        end_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "GAME OVER")
        self.announce_to_players(end_msg.encode())
        
        # Send win message
        win_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "YOU WIN!!!")
        send_message_to(winner.client, win_msg.encode())
        win_stats_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"You won in {winner.moves} moves!")
        send_message_to(winner.client, win_stats_msg.encode())
        
        # Send lose message
        loss_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "You lose")
        send_message_to(loser.client, loss_msg.encode())

        # Announce to spectators
        spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"GAME OVER! PLAYER {winner.id} WINS!")
        self.announce_to_spectators(spec_msg.encode())

        self.game_number += 1

        time.sleep(5) # Wait 5 seconds before starting new game (can be removed later)
    
    """
    Run games in a loop indefinately.
    """
    def run(self):
        while True:
            self.play_game()
        close_all_connections()


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
        while True:
            s.listen(1)
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
#end region

if __name__ == "__main__":
    main()