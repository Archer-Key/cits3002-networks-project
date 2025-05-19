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
import heapq
from enum import Enum
from random import randint

from protocol import *
from battleship import *

HOST = '127.0.0.1'
PORT = 5000

SERVER_ID = 0

#region Clients
MAX_CLIENTS = 127
clients = []
num_clients = 0
free_ids = list(range(0,127))

class ClientType(Enum):
    SPECTATOR = 0
    PLAYER = 1

class Client:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.thread = None
        self.id = None
        self.type = ClientType.SPECTATOR
        self.timeout = None
        self.username = ""
        # used for protocol
        self.incoming = bytearray()
        self.seq_s = 0
        self.send_window = []
        self.seq_r = 0
        self.recv_window = []
    def set_spectator(self):
        self.type = ClientType.SPECTATOR
    def set_player(self):
        self.type = ClientType.PLAYER
#endregion

#region Send Messages
def send_message_to(client, send_msg, new=True):
    msg = send_msg.copy() # used so that multiple users can send the same message with different seq
    if new:
        msg.seq = client.seq_s
        heapq.heappush(client.send_window, (msg.seq, msg))
        client.seq_s = (client.seq_s+1)&((1<<16)-1)
    print(f"DEBUG SENDING: seq: {msg.seq}, pck_t: {msg.packet_type}, type: {msg.type}, expected: {msg.expected}, id: {msg.id}, msg_len: {msg.msg_len}, msg: {msg.msg}\n\n\n")
    client.conn.send(msg.encode()) 

def send_message_to_all(clients, msg):
    for client in clients:
        send_message_to(client, msg)

def send_ack(client, seq):
    ack = Message(id=client.id, type=MessageType.TEXT, expected=MessageType.TEXT, msg="",\
                           seq=seq, packet_type=PacketType.ACK)
    send_message_to(client, ack, False)

def send_nack(client):
    nack = Message(id=client.id, type=MessageType.TEXT, expected=MessageType.TEXT, msg="",\
                           seq=0, packet_type=PacketType.NACK)
    send_message_to(client, nack, False)

def handle_chat(client, text):
    expected = MessageType.PLACE if game.state == GameState.PLACE else MessageType.FIRE
    msg = Message(SERVER_ID, MessageType.CHAT, expected, "[" + client.username + "]: " + text)
    ## send message to all except person sending
    send_message_to_all([x for x in clients if x!= client], msg)
    pass
#endregion

#region Timeout

## runs timers on a thread, def more elegant way to do it but odds are this wont break everything
class Timer:
    def __init__(self, client, duration):
        self.thread = None
        self.client = client
        self.active = True

        self.start_timer_thread(duration, client)
    
    def timeout(self, duration, client):
        print(f"[INFO] Starting timeout timer for Client [{client.id}]")
        time.sleep(duration)
        if self.active:
            print(f"[INFO] Client [{self.client.id}] has timed out")
            handle_disconnect(client)
    
    def start_timer_thread(self, duration, client):
        thread = threading.Thread(target=self.timeout, args=(duration, client,))
        thread.start()
        self.thread = thread
        return thread

def end_game(game):
    print("ending game")
    game.state = GameState.END

#endregion

#region Process Msg
def process_client_messages(client):
    while True:
        try:
            msg = heapq.heappop(client.recv_window)[1]
        except IndexError: # all messages sent
            return
        
        if msg.seq < client.seq_r: # skip duplicates
            continue

        if msg.seq > client.seq_r: # end if message is a future packet
            heapq.heappush(client.recv_window, (msg.seq, msg))
            send_ack(client, client.seq_r)
            return 
        
        # process the message
        try:
            try:
                ## Handles inputs out side of game world
                if msg.type == MessageType.CHAT:
                    handle_chat(client, msg.msg)
                    continue
                
                ## should be the first message the server recieves from the client
                elif msg.type == MessageType.CONNECT:
                    client.username = msg.msg
                    client.seq_r += 1
                    client.seq_r = client.seq_r&((1<<16)-1) # loop around

                    if game.disconnected_player:
                        if client.username == game.disconnected_player.username:
                            print(f"reconnecting client {client.username}")
                            game.players[game.disconnected_player_id].client = client
                            handle_reconnect(client)
                    continue

                elif msg.type == MessageType.DISCONNECT:
                    handle_disconnect(client)
                    continue
                
                if client.type == ClientType.SPECTATOR:
                    res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "Incorrect message type.")
                    send_message_to(client, res)

                player = game.get_player(msg.id)
                if player == None:
                    raise ValueError # a different type of error is probably better here
                
                # inputs during gameplay
                if game.state == GameState.WAIT:
                    game.send_waiting_message(client)
                    
            ## Needs better way to check mismatch between game state and message type
                elif game.state == GameState.PLACE:
                    if msg.type == MessageType.PLACE:
                        game.place_ship(client.id, msg.msg)
                    else:
                        res = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE, "Incorrect Command Type")
                        send_message_to(client, res)
                        
                elif game.state == GameState.BATTLE:
                    if msg.type == MessageType.FIRE:
                        game.fire(client.id, msg.msg)
                    else:
                        res = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE, "Incorrect Command Type")
                        send_message_to(client, res)

                elif game.state == GameState.END:
                    res = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT,\
                                  "Game has ended. Thank you for playing!")
                    send_message_to(client, res)

                else:
                    print("Error, game is in an unknown state.")

            except ValueError:
                # handle malformed message
                pass
          
            # all went well
            client.seq_r += 1
            client.seq_r = client.seq_r&((1<<16)-1) # loop around

        except ValueError as e:
            # needs to be handled better
            print("#####\n"*5)
            print(f"Failure decoding message, ignoring {e}")
            print("#####\n"*5)
            return
#endregion

def handle_reconnect(client):
    if game.state == GameState.PAUSE:
        game.state = game.previous_state
        print(f"[INFO] player has reconnected and game is resuming to state [{game.state}]")
        rec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"Welcome back {client.username}, the game will now resume")
        send_message_to(client, rec_msg)
        res_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"Player has reconnected, resuming game")
        send_message_to_all(clients, res_msg)
        if game.state == GameState.BATTLE:
            for player in game.players:
                game.send_fire_prompt(player)
        if game.state == GameState.PLACE:
            for player in game.players:
                game.send_place_prompt(player)
        
        game.disconnected_players -= 1
        
        game.end_thread.cancel()
        game.end_thread = None

#region Handle Client
def handle_client(client):
    socket = client.conn
    with socket:
        # send client their client ID
        id_msg = Message(id=SERVER_ID, type=MessageType.CONNECT, expected=MessageType.CHAT, msg=client.id)
        send_message_to(client, id_msg)

        # check if clients username matchs disconnection
        reconnecting_player = False

        if game.disconnected_player:
            if client.username == game.disconnected_player.username:
                print(f"reconnecting client {client.username}")
                game.players[game.disconnected_player_id].client = client
                reconnecting_player = True

        # send client a message indicating their status
        if game.state == GameState.WAIT:
            game.send_waiting_message(client)
        elif game.state in (GameState.PLACE, GameState.BATTLE):
            spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "YOU ARE CURRENTLY SPECTATING")
            send_message_to(client, spec_msg)
        elif game.state == GameState.PAUSE:
            if reconnecting_player:
                game.state = game.previous_state
                print(f"[INFO] player has reconnected and game is resuming to state [{game.state}]")
                rec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"Welcome back {client.username}, the game will now resume")
                send_message_to(client, rec_msg)
                res_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"Player has reconnected, resuming game")
                send_message_to_all(clients, res_msg)
                if game.state == GameState.BATTLE:
                    for player in game.players:
                        game.send_fire_prompt(player)
                if game.state == GameState.PLACE:
                    for player in game.players:
                        game.send_place_prompt(player)
                
                game.disconnected_players -= 1
                
                game.end_thread.cancel()
                game.end_thread = None
                
            pass
        elif game.state == GameState.END:
            spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "WAITING FOR NEW GAME TO START")
            send_message_to(client, spec_msg)
#endregion

#region Receive Msg
        # recieve messages from client
        while True:
            try:
                raw = client.conn.recv(BUFSIZE)
            except:
                # player disconnected
                break

            ## not sure if this is needed anymore
            if not raw:
                break

            ## start timeout timer for players
            if client.type == ClientType.PLAYER:
                if client.timeout:
                    client.timeout.active = False
                client.timeout = Timer(client, 30)
            
            client.incoming += bytearray(raw)

            while len(client.incoming) >= 9:
                try:
                    msg = Message.decode(client.incoming)
                    client.incoming = client.incoming[9+msg.msg_len:]

                    if msg.packet_type == PacketType.ACK:
                        sent = heapq.heappop(client.send_window)
                        while (sent[0] < msg.seq):
                            sent = heapq.heapop(client.send_window)
                        heapq.heappush(client.send_window, sent) # push the last element popped back on
                        continue
            
                    if msg.packet_type == PacketType.NACK: # resend all messages
                        messages = client.send_window.copy()
                        while True:
                            try:
                                send_message_to(client, heapq.heappop(messages)[1], False) 
                            except IndexError:
                                break
                        continue
            
                    if (msg.seq >= client.seq_r): # queue future packets
                        heapq.heappush(client.recv_window, (msg.seq, msg))
                        continue
            
                    if (msg.seq < client.seq_r): #ignore already received packets
                        continue
                
                except NotEnoughBytesError:
                    break

                except ChecksumMismatchError:
                    send_nack(client)
                    client.incoming = bytearray()
                    break

            process_client_messages(client)

    # handle disconnect
    handle_disconnect(client) # this is still part of handle_client()
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
    PAUSE = 4

class Game:
    def __init__(self):
        self.game_number = 0
        self.new_game()
    def new_game(self):
        self.state = GameState.WAIT
        self.players = [Player(0), Player(1)]
        self.previous_state = GameState.WAIT
        self.disconnected_player = None
        self.disconnected_player_id = 0
        self.disconnected_players = 0
        self.disconnect_time = None
        self.player_turn = None
        if self.game_number > 0:
            if self.end_thread:
                self.end_thread.cancel()
        self.end_thread = None
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
            send_message_to(client, msg)

    """
    Set a client as a player.
    """
    def set_player(self, player_id, client):
        client.set_player()
        self.players[player_id].client = client
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"YOU ARE PLAYER {player_id}")
        send_message_to(client, msg)

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
        for player in self.players:
            if player.client != None and player.client.id == client_id:
                return player
            
        return None
        
    def remove_player(self, client):
        for player in self.players:
            if player.client == client:
                player.client = None
                self.disconnected_player = client
                self.disconnected_player_id = player.id
                self.disconnected_players += 1
    
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
        send_message_to(player.client, msg)
        
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "Other player has decided to quit. Thanks for playing!")
        send_message_to(self.get_opponent(player).client, msg)
        
        self.state = GameState.END
        close_all_connections()
    
    """
    Handle player timeout
    """
    def handle_player_timeout(self, player):
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "You have taken to long to make a move")
        send_message_to(player.client, msg)
        
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "Other player has timed out. Thanks for playing!")
        send_message_to(self.get_opponent(player).client, msg)
        
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
        send_message_to(client, res)

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
        
        print(board_msg[17])
        return board_msg
    
    """
    Send a player a board.
    """
    def send_board(self, to_player, board, show_hidden=False):
        client = to_player.client
        board_msg = self.board_to_str(board, show_hidden)
        msg = Message(SERVER_ID, MessageType.BOARD, MessageType.PLACE, board_msg)
        send_message_to(client, msg)
        if self.state == GameState.BATTLE:
            spec_msg = Message(SERVER_ID, MessageType.BOARD, MessageType.CHAT, board_msg)
            self.announce_to_spectators(spec_msg)
    
    """
    Send a message to both players.
    """
    def announce_to_players(self, msg):
        for player in self.players:
            if player.client != None:
                send_message_to(player.client, msg)
    """
    Send a message to all spectators.
    """
    def announce_to_spectators(self, msg):
        playerids = []
        for player in self.players:
            if player.client:
                playerids.append(player.client.id)
        for client in clients:
            if (client.id not in playerids):
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
            send_message_to(player.client, msg)
            return

        self.send_board(player, player.board, show_hidden=True)
        ship_name, ship_size = SHIPS[player.ships_placed] # Next ship to place
        orientation = player.ship_orientation
        
        prompt_msg = f"Place {ship_name} (Size: {ship_size}) {self.orientation_str(orientation)}. Enter 'x' to change orientation."
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.PLACE, prompt_msg)
        send_message_to(player.client, msg)

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
            send_message_to(player.client, msg)
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
            send_message_to(player.client, msg)
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
            self.announce_to_spectators(spec_msg)
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
        send_message_to(player.client, msg)
        spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"PLAYER {player.id} FIRING")
        self.announce_to_spectators(spec_msg)
    
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
            send_message_to(player.client, msg)
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
                send_message_to(player.client, msg)
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
            send_message_to(player.client, res_msg)
            # Send result to opponent
            opp_msg = Message(SERVER_ID, MessageType.RESULT, MessageType.FIRE, opp_txt)
            send_message_to(opponent.client, opp_msg)
            # Announce result to spectators
            spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, spec_txt)
            self.announce_to_spectators(spec_msg)
            # End turn
            self.end_player_turn(player)
        
        except ValueError as e:
            msg = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE, f"Invalid input: {e}")
            send_message_to(player.client, msg)
            self.send_fire_prompt(player)
#endregion

#region Run Game

    # seperate functions for each stage to make it easier to pause and resume
    def placing_stage(self):
        # Start placing phase
        self.send_place_prompt(self.players[0])
        self.send_place_prompt(self.players[1])
        
        # Wait for players to place all ships
        while((self.players[0].ships_placed < 5 or self.players[1].ships_placed < 5) and (self.state == GameState.PLACE or self.state == GameState.PAUSE)):
            time.sleep(1)

        return True
    
    def start_battle(self):
        battle_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE, "BATTLE STARTING")
        self.announce_to_players(battle_msg)
        self.player_turn = randint(0,1)
        # Send prompt to player who's turn is first and wait to other player
        self.send_fire_prompt(self.players[self.player_turn])
        wait_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.FIRE, "Waiting for opponent...")
        send_message_to(self.players[1 - self.player_turn].client, wait_msg)

    def battle_stage(self):
        if (self.players[0].board.all_ships_sunk()):
            winner = self.players[1]
            loser = self.players[0]
            return winner, loser
        elif (self.players[1].board.all_ships_sunk()):
            winner = self.players[0]
            loser = self.players[1]
            return winner, loser
        return None, None

    def play_game(self):
        self.new_game()
        
        # Wait for players to connect
        while(len(clients) < 2):
            time.sleep(1)
        
        # Announce start
        start_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "GAME STARTING")
        send_message_to_all(clients, start_msg)
        self.state = GameState.PLACE

        # Announce players
        self.set_players()
                
        # Announce spectators
        msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"YOU ARE A SPECTATOR")
        self.announce_to_spectators(msg)

        self.placing_stage()
        
        if self.state != GameState.END:
            self.state = GameState.BATTLE

        # Start battle
        if self.state == GameState.BATTLE:
            self.start_battle()

        # Wait for battle to end
        winner = None
        loser = None
        while (self.state == GameState.BATTLE or self.state == GameState.PAUSE) and winner == None:
            winner, loser = self.battle_stage()
            time.sleep(1)
        
        self.state = GameState.END
        
        # End game
        end_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "GAME OVER")
        self.announce_to_players(end_msg)
        
        if winner:
            # Game finished with a player winning
            # Send win message
            win_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "YOU WIN!!!")
            send_message_to(winner.client, win_msg)
            win_stats_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"You won in {winner.moves} moves!")
            send_message_to(winner.client, win_stats_msg)
            
            # Send lose message
            loss_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, "You lose")
            send_message_to(loser.client, loss_msg)

            # Announce to spectators
            spec_msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"GAME OVER! PLAYER {winner.id} WINS!")
            self.announce_to_spectators(spec_msg)

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
def handle_disconnect(client : Client):
    global num_clients
    ## it looks like this is firing twice, not sure why, have to look into it
    print(f"[INFO] Client [{client.id}] disconnected.")

    if client.timeout:
        client.timeout.active = False
    if client in clients:
        heapq.heappush(free_ids, client.id)
        clients.remove(client)
        num_clients -= 1
    game.remove_player(client)

    try:
        msg = Message(SERVER_ID, MessageType.DISCONNECT, MessageType.DISCONNECT, "disconnected")
        send_message_to(client, msg)
    except:
        pass

    client.conn.close()

    ## check if all players have disconnected and end game
    if game.disconnected_players >= 2:
        game.state = GameState.END
        return

    if game.state != GameState.PAUSE:
        game.previous_state = game.state

    game.state = GameState.PAUSE
    if game.end_thread:
        return
    game.end_thread = threading.Timer(30, end_game, args=(game,))
    game.end_thread.start()

    msg = Message(SERVER_ID, MessageType.TEXT, MessageType.CHAT, f"[INFO] player [{client.id}] has disconnected, waiting for reconnect")
    game.announce_to_players(msg)


def close_all_connections():
    for client in clients:
        client.conn.close()

# main thread accepts clients in a loop
def main():
    global num_clients

    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))

        # start the game manager thread
        game_manager = threading.Thread(target=game.run)
        game_manager.daemon = True
        game_manager.start()
        
        # listen for connections
        try:
            while True: # keeps thread open when max clients is full and allows for clients to decrease
                while num_clients < MAX_CLIENTS:
                    s.listen(1)
                    conn, addr = s.accept()
                    print(f"[INFO] Client connected from {addr}")

                    client = Client(conn, addr)
                    clients.append(client)
                    num_clients += 1
                    client.id = heapq.heappop(free_ids)

                    thread = threading.Thread(target=handle_client, args=[client])
                    thread.daemon = True
                    client.thread = thread
                    thread.start()
        except KeyboardInterrupt:
            return
#end region

if __name__ == "__main__":
    main()