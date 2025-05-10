from enum import Enum

class MessageType(Enum):
  NONE = 0 # Indicates that no message is expected in response.
  CONNECT = 1 # Gives the user their id when first connecting
  TEXT = 2 # Indicates that the msg component should be printed as plaintext.
  CHAT = 3 # Indicates that the msg should be broadcasted to all players and spectators.
  BOARD = 4 # Indicates the msg should be printed as a board
  PLACE = 5 # Message type for placing ships.
  FIRE = 6 # Message type for player to fire at coordinates during the battle section.
  RESULT = 7 # Acknowledges result of player's fire attempt.
  DISCONNECT = 8 # Tells the server a player is disconnecting

class Message:
  # Stucture of a basic message to send over the socket.
  def __init__(self, id, type, expected, msg=""):
    self.id = id 
    self.type = type 
    self.expected = expected # Type of message sender expects to receive, set NONE for no resposne
    self.msg = msg 

  # Encode the message into a string.
  def encode(self):
    return str(self.id) + " " + str(self.type.value) + " " + str(self.expected.value) + " " + str(self.msg)
  
  # Decode and encoded message into a Message object
  @staticmethod
  def decode(encoded):
    encoded = encoded.strip().split(" ")

    # should check these for Index Errors
    id = int(encoded.pop(0))
    type = MessageType(int(encoded.pop(0)))
    expected = MessageType(int(encoded.pop(0)))
    
    msg = ""
    while True:
      try:
        msg = msg + encoded.pop(0) + " "
      except IndexError:
        break
    msg = msg.strip()

    return Message(id, type, expected, msg)