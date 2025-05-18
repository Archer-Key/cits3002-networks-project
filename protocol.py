from enum import Enum

BUFSIZE = 516

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

class Message:
  # Stucture of a basic message to send over the socket.
  def __init__(self, id, type, expected, msg="", seq=0, packet_type=PacketType.DATA):
    self.seq = seq
    self.packet_type = packet_type # Packet type (2 bits)
    self.type = type # Type of the message being sent
    self.expected = expected # Type of message sender expects to receive, set NONE for no resposne
    self.id = id 
    self.msg = str(msg)

  def encode(self):
    head = bytearray()
    head.append(self.seq>>8)
    head.append(self.seq&255)
    head.append(self.id)
    head.append((self.packet_type.value<<6)+(self.type.value<<3)+(self.expected.value))
    if len(self.msg) > 512:
      self.msg = self.msg[0:512] # cut mesages off at 512 bytes
    pack = (head + bytearray(self.msg.encode("utf-8")))
    crc = crc32(pack)
    return bytes(pack + crc)
  
  # Decode an encoded message into a Message object
  @staticmethod
  def decode(pack):
    pack_len = len(pack)
    data = pack[0:pack_len-4]
    crc = pack[pack_len-4:]
    expected_crc = bytes(crc32(data))
    if (crc == expected_crc):
      seq = data[0]<<8 + data[1]
      id = data[2]
      packet_type = PacketType((data[3]&(3<<6))>>6)
      message_type = MessageType((data[3]&(7<<3))>>3)
      expected_type = MessageType(data[3]&(7))
      msg = ""
      if len(data) >= 4:
        msg = data[4:].decode("utf-8")
      return Message(id=id, type=message_type, expected=expected_type, msg=msg, seq=seq, packet_type=packet_type)
    else:
      print("Error detected")
      return False