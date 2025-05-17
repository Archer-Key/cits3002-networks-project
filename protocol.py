from enum import Enum

class PacketType(Enum):
  DATA = 0
  ACK = 1
  NACK = 2

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
  USERNAME = 9

class Message:
  # Stucture of a basic message to send over the socket.
  def __init__(self, seq, packet_type, id, type, expected, msg=""):
    self.seq = seq
    self.packet_type = packet_type # Packet type (2 bits)
    self.type = type # Type of the message being sent
    self.expected = expected # Type of message sender expects to receive, set NONE for no resposne
    self.id = id 
    self.msg = msg 

  def encode(self):
    msg_len = len(self.msg)
    full_packets = msg_len//255
    if msg_len%255 == 0:
      full_packets -= 1
    packets = []
    off = 0

    while off < full_packets:
      packets.append(self.encodePacket(1, off, self.msg[255*off:255*(off+1)]))
      self.seq += 1
      off += 1
    packets.append(self.encodePacket(1, off, self.msg[255*off:]))
    
    return packets

  def encodePacket(self, frag, off, msg):
    msg_len = len(msg)
    
    head = bytearray()
    # sequence number
    head.append(self.seq>>8) # first 8 bits
    head.append(self.seq&255) # second 8 bits
    # type frag and off
    head.append((self.packet_type.value<<6) + (frag<<5) + off)
    head.append(msg_len) # len
    # msg_t and exp_t
    head.append((self.type.value<<4) + self.expected.value)
    head.append(self.id)
    # msg
    pack = head + bytearray(msg.encode("utf-8"))
    #TODO: CRC32

    return bytes(pack)
  
  # Decode and encoded message into a Message object
  @staticmethod
  def decode(pack):
    read = 0
    # decode seq
    seq = int(pack[read])<<8 + int(pack[read+1])
    read += 2
    # decode packet type, frag, and offset
    info = int(pack[read])
    packet_type = info>>6
    frag = info&(1<<5)
    off = info&((1<<5)-1)
    read += 1
    # decode msg len
    msg_len = int(pack[read])
    read += 1
    # decode msg type and expected
    types = int(pack[read])
    msg_type = types>>4
    exp_type = types&((1<<5)-1)
    read += 1
    # decode id
    client_id = int(pack[read])
    read += 1
    # rest of the packet is the message
    msg = bytes(pack[read:]).decode("utf-8")
    return(Message(seq, PacketType(packet_type), client_id, MessageType(msg_type), MessageType(exp_type), msg), frag, off)