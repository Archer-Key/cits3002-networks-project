from enum import Enum

from protocol import *
from handle_client import Client, send_message_to, send_message_to_all
from battleship import Board

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