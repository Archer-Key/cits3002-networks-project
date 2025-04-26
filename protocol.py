class Message:
  """
  Stucture of a basic message to send over the socket.
  """
  def __init__(self, type="", msg="", opts=[]):
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
  def decode(self, encoded):
    encoded = encoded.strip().split(" ")

    type = encoded.pop(0)
    
    num_opts = 0
    if type == "PLACE":
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

    self.type = type
    self.opts = opts 
    self.msg = msg

"""
Message type used for sending plaintext messages.

Example: TEXT Waiting for opponent... prints -> Waiting for opponent...
"""
class TEXT(Message):
  def __init__(self, msg):
    super().__init__("TEXT", msg)

"""
Message type for inidicating change in game stage.
Used to inidicate what type of message the client should send.

1 Option: Game Stage
msg: gives player message to print

Example: GAME START, GAME PLACE, GAME BATTLE, GAME END
"""
class GameMsg(Message):
  def __init__(self, stage, msg):
    super().__init__("GAME", msg="", opts=[stage])

"""
Message type for placing ships.

2 Options: SHIP_TYPE, ORIENTATION
msg contains the cooridnates specified by the client

Example: PLACE SHIP_TYPE ORIENTATION COORDINATES
"""
class PlaceMsg(Message):
  def __init__(self, ship_type, orientation, msg):
    super().__init__("PLACE", msg, [ship_type, orientation])

"""
Message type for player to fire at coordinates during the battle section.

Example: FIRE A1
"""
class FireMsg(Message):
  def __init__(self, msg):
    super().__init__("FIRE", msg)

"""
Message type to acknowledge result of player's fire attempt.

1 Option: Result Type

Example: RESULT HIT, RESULT MISS, RESULT REPEAT
"""
class ResultMsg(Message):
  def __init__(self, result_type):
    super().__init__("RESULT", msg="", opts=[result_type])