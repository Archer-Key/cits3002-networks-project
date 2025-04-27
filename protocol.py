class Message:
  """
  Stucture of a basic message to send over the socket.
  """
  def __init__(self, type="", opts=[], msg=""):
    self.type = type
    self.opts = opts 
    self.msg = msg
  """
  Encode the message into a string.
  """
  def encode(self):
    encoded = ""
    encoded = encoded + self.type + " "
    for opt in self.opts:
      encoded = encoded + opt + " "
    encoded = encoded + self.msg
    return encoded
  """
  Decode and encoded message into a Message object
  """
  @staticmethod
  # Needs error handling
  def decode(self, encoded):
    encoded = encoded.strip().split(" ")

    type = encoded.pop(0)
    
    num_opts = 0
    if type in ["GAME", "FIRE", "RESULT"]:
      num_opts = 1
    elif type == "PLACE":
      num_opts = 2

    opts = []
    for i in range(0, num_opts):
      opts.append(encoded.pop(0))
    
    msg = ""
    while True:
      try:
        msg = msg + encoded.pop(0) + " "
      except IndexError:
        break
    msg = msg.strip()

    return Message(type, opts, msg)
"""
Message type used for sending plaintext messages.

Example: TEXT Waiting for opponent... prints -> Waiting for opponent...
"""
class TextMsg(Message):
  def __init__(self, msg):
    super().__init__(type="TEXT", opts=[], msg=msg)

"""
Message type for inidicating change in game stage.
Used to inidicate what type of message the client should send.

1 Option: Game Stage
msg: gives player message to print

Example: GAME WAIT, GAME PLACE, GAME BATTLE, GAME END
"""
class GameMsg(Message):
  def __init__(self, stage, msg):
    super().__init__("GAME", opts=[stage], msg="")

"""
Message type for placing ships.

2 Options: SHIP_TYPE, ORIENTATION
msg contains the cooridnates specified by the client

Example: PLACE SHIP_TYPE ORIENTATION COORDINATES
"""
class PlaceMsg(Message):
  def __init__(self, ship_type, orientation, msg):
    super().__init__("PLACE", opts=[ship_type, orientation], msg=msg)

"""
Message type for player to fire at coordinates during the battle section.

1 Option: PLAYER_ID indicates the player sending the fire command
msg: contains the coordinates to fire at

Example: FIRE PLAYER_ID COORDINATES
"""
class FireMsg(Message):
  def __init__(self, msg):
    super().__init__("FIRE", msg)

"""
Message type to acknowledge result of player's fire attempt.

1 Option: Result Type
msg: optional component, only used to indicate which ship was sunk

Example: RESULT HIT, RESULT MISS, RESULT REPEAT, RESULT SANK SHIP_NAME
"""
class ResultMsg(Message):
  def __init__(self, result_type, ship_name=""):
    super().__init__("RESULT", opts=[result_type], msg=ship_name)