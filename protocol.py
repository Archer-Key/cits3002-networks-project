from enum import Enum

BUFSIZE = 516 # Maximum size of a packet

#region Errors
class NotEnoughBytesError(Exception):
  pass

class ChecksumMismatchError(Exception):
  pass
#endregion

#region Types
class PacketType(Enum):
  DATA = 0
  ACK = 1
  NACK = 2

class MessageType(Enum):
  DISCONNECT = 0 # Tells the server a player is disconnecting
  CONNECT = 1 # Gives the user their id when first connecting
  TEXT = 2 # Indicates that the msg component should be printed as plaintext.
  CHAT = 3 # Indicates that the msg should be broadcasted to all players and spectators.
  BOARD = 4 # Indicates the msg should be printed as a board
  PLACE = 5 # Message type for placing ships.
  FIRE = 6 # Message type for player to fire at coordinates during the battle section.
  RESULT = 7 # Acknowledges result of player's fire attempt.
#endregion

#region CRC32
def invert_bit_order(num):
  out = 0
  for i in range(0,8):
    bit = ((num&(1<<i))>>i)
    out += bit<<(7-i)
  return out

def crc32(pack):
  # convert bytes object to an integer for python bitwise operations
  input = 0
  total_bytes = len(pack)
  for i in range(total_bytes):
    input += invert_bit_order(pack[i]<<(8*(total_bytes-1-i)))
    
  # now we start the crc
  # this div is in LSB order hence why we inverted the bit order of the above
  div = 0xEDB88320 # 33 bit divisor will produce 32 bit remainder
  input = input<<32 # pad 32 bits
  total_bits = 8*total_bytes+32
  
  for i in range(total_bits, 31, -1): # i is the bit number we are looking at
    if ((input&(1<<(i-1)))>>(i-1)) == 1: # go to next MSB
      remaining_bits = i-32 # this is i-33 for the bit number +1 since 0 is a bit too
      unaffected = input&((1<<remaining_bits)-1) # part of the input we have not xored yet
      xor = (input>>remaining_bits)^div # only xor the section we care about
      input = (xor<<remaining_bits)+unaffected # shift back and add unaffected
  
  crc = bytearray()
  crc.append((input&(255<<24))>>24) # first 8 bits
  crc.append((input&(255<<16))>>16) # second 8 bits
  crc.append((input&(255<<8))>>8) # etc...
  crc.append(input&(255))
  return crc
#endregion

#region Message Struct
class Message:
  # Stucture of a basic message to send over the socket.
  def __init__(self, id, type, expected, msg="", seq=0, packet_type=PacketType.DATA):
    self.seq = seq
    self.packet_type = packet_type # Packet type (2 bits)
    self.type = type # Type of the message being sent
    self.expected = expected # Type of message sender expects to receive, set NONE for no resposne
    self.id = id 
    self.msg = str(msg)
    self.msg_len = len(self.msg)
#endregion

#region Encoding
  def encode(self):
    pack = bytearray()
    pack.append(self.seq>>8)
    pack.append(self.seq&255)
    pack.append((self.packet_type.value<<6)+(self.type.value<<3)+(self.expected.value))
    if self.msg_len > 511:
      self.msg = self.msg[0:511] # cut mesages off at 511 bytes
      self.msg_len = 511
    pack.append((self.id<<1)+(self.msg_len>>8))
    pack.append(self.msg_len&255)
    if len(self.msg) != 0:
      pack = (pack + bytearray(self.msg.encode("utf-8")))
    crc = crc32(pack)
    return bytes(crc + pack)
#endregion

#region Decoding
  # Decode an encoded message into a Message object
  @staticmethod
  def decode(data):
    data_len = len(data)
    if (data_len < 9):
      raise NotEnoughBytesError

    crc = data[0:4]
    seq = data[4]<<8 + data[5]
    packet_type = PacketType((data[6]&(3<<6))>>6)
    message_type = MessageType((data[6]&(7<<3))>>3)
    expected_type = MessageType(data[6]&(7))
    id = data[7]>>1
    msg_len = ((data[7]&1)<<8) + data[8]
    msg = ""
    if msg_len != 0:
      try:
        msg = data[9:9+msg_len].decode("latin-1")
      except IndexError:
        raise NotEnoughBytesError

    expected_crc = crc32(bytearray(data[4:9+msg_len]))
    if crc != expected_crc:
      raise ChecksumMismatchError
    
    return Message(id=id, type=message_type, expected=expected_type, msg=msg, seq=seq, packet_type=packet_type)
#endregion

  def copy(self): # Used to copy a packet to avoid python object shenanigans
    return Message(self.id, self.type, self.expected, self.msg, self.seq, self.packet_type)