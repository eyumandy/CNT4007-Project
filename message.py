"""
Message class and serialization for P2P BitTorrent Implementation
Purpose: Handle all message types, serialization, and deserialization for the P2P protocol
Dependencies: constants.py
"""

import struct
from typing import Optional, Union, Tuple, List
from constants import *

class HandshakeMessage:
    """
    Handshake message handler
    Format: 'P2PFILESHARINGPROJ' (18 bytes) + zero bits (10 bytes) + peer_id (4 bytes)
    Total: 32 bytes
    """
    
    def __init__(self, peer_id: int):
        """
        Initialize handshake message
        
        Args:
            peer_id (int): Peer ID to include in handshake
        """
        self.peer_id = peer_id
        self.header = HANDSHAKE_HEADER
    
    def serialize(self) -> bytes:
        """
        Serialize handshake message to bytes
        
        Returns:
            bytes: 32-byte handshake message
        """
        # Create the handshake message
        # 18 bytes header + 10 bytes zeros + 4 bytes peer_id (big-endian)
        message = self.header + b'\x00' * HANDSHAKE_ZERO_BITS_LEN + struct.pack('!I', self.peer_id)
        
        if len(message) != HANDSHAKE_MSG_LEN:
            raise ValueError(f"Handshake message size error: expected {HANDSHAKE_MSG_LEN}, got {len(message)}")
        
        return message
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'HandshakeMessage':
        """
        Deserialize handshake message from bytes
        
        Args:
            data (bytes): 32-byte handshake message
            
        Returns:
            HandshakeMessage: Parsed handshake message
            
        Raises:
            ValueError: If message format is invalid
        """
        if len(data) != HANDSHAKE_MSG_LEN:
            raise ValueError(f"Invalid handshake size: expected {HANDSHAKE_MSG_LEN}, got {len(data)}")
        
        # Extract components
        header = data[:HANDSHAKE_HEADER_LEN]
        zero_bits = data[HANDSHAKE_HEADER_LEN:HANDSHAKE_HEADER_LEN + HANDSHAKE_ZERO_BITS_LEN]
        peer_id_bytes = data[HANDSHAKE_HEADER_LEN + HANDSHAKE_ZERO_BITS_LEN:]
        
        # Validate header
        if header != HANDSHAKE_HEADER:
            raise ValueError(f"Invalid handshake header: expected {HANDSHAKE_HEADER}, got {header}")
        
        # Parse peer ID (big-endian)
        peer_id = struct.unpack('!I', peer_id_bytes)[0]
        
        return cls(peer_id)
    
    def __str__(self):
        return f"HandshakeMessage(peer_id={self.peer_id})"
    
    def __repr__(self):
        return self.__str__()


class Message:
    """
    Regular message handler for all message types after handshake
    Format: length (4 bytes) + type (1 byte) + payload (variable)
    """
    
    def __init__(self, message_type: Union[str, int], payload: Optional[bytes] = None):
        """
        Initialize a message
        
        Args:
            message_type (str or int): Message type name or ID
            payload (bytes, optional): Message payload
        """
        # Handle both string type names and integer type IDs
        if isinstance(message_type, str):
            if message_type not in MESSAGE_TYPES:
                raise ValueError(f"Unknown message type: {message_type}")
            self.type_id = MESSAGE_TYPES[message_type]
            self.type_name = message_type
        else:
            if message_type not in MESSAGE_ID_TO_TYPE:
                raise ValueError(f"Unknown message type ID: {message_type}")
            self.type_id = message_type
            self.type_name = MESSAGE_ID_TO_TYPE[message_type]
        
        self.payload = payload if payload is not None else b''
    
    def serialize(self) -> bytes:
        """
        Serialize message to bytes
        
        Returns:
            bytes: Serialized message with length prefix
        """
        # Calculate message length (type + payload)
        msg_length = MESSAGE_TYPE_LEN + len(self.payload)
        
        # Pack: length (4 bytes) + type (1 byte) + payload
        message = struct.pack('!I', msg_length) + struct.pack('!B', self.type_id) + self.payload
        
        return message
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'Message':
        """
        Deserialize a complete message from bytes
        
        Args:
            data (bytes): Complete message including length prefix
            
        Returns:
            Message: Parsed message object
            
        Raises:
            ValueError: If message format is invalid
        """
        if len(data) < MESSAGE_LENGTH_LEN + MESSAGE_TYPE_LEN:
            raise ValueError(f"Message too short: {len(data)} bytes")
        
        # Extract length and type
        msg_length = struct.unpack('!I', data[:MESSAGE_LENGTH_LEN])[0]
        msg_type = struct.unpack('!B', data[MESSAGE_LENGTH_LEN:MESSAGE_LENGTH_LEN + MESSAGE_TYPE_LEN])[0]
        
        # Extract payload
        payload_start = MESSAGE_LENGTH_LEN + MESSAGE_TYPE_LEN
        payload = data[payload_start:payload_start + msg_length - MESSAGE_TYPE_LEN]
        
        return cls(msg_type, payload)
    
    @classmethod
    def create_choke(cls) -> 'Message':
        """Create a choke message"""
        return cls('choke')
    
    @classmethod
    def create_unchoke(cls) -> 'Message':
        """Create an unchoke message"""
        return cls('unchoke')
    
    @classmethod
    def create_interested(cls) -> 'Message':
        """Create an interested message"""
        return cls('interested')
    
    @classmethod
    def create_not_interested(cls) -> 'Message':
        """Create a not interested message"""
        return cls('not_interested')
    
    @classmethod
    def create_have(cls, piece_index: int) -> 'Message':
        """
        Create a have message
        
        Args:
            piece_index (int): Index of the piece
            
        Returns:
            Message: Have message
        """
        payload = struct.pack('!I', piece_index)
        return cls('have', payload)
    
    @classmethod
    def create_bitfield(cls, bitfield: bytes) -> 'Message':
        """
        Create a bitfield message
        
        Args:
            bitfield (bytes): Bitfield bytes
            
        Returns:
            Message: Bitfield message
        """
        return cls('bitfield', bitfield)
    
    @classmethod
    def create_request(cls, piece_index: int) -> 'Message':
        """
        Create a request message
        
        Args:
            piece_index (int): Index of requested piece
            
        Returns:
            Message: Request message
        """
        payload = struct.pack('!I', piece_index)
        return cls('request', payload)
    
    @classmethod
    def create_piece(cls, piece_index: int, piece_data: bytes) -> 'Message':
        """
        Create a piece message
        
        Args:
            piece_index (int): Index of the piece
            piece_data (bytes): Actual piece data
            
        Returns:
            Message: Piece message
        """
        payload = struct.pack('!I', piece_index) + piece_data
        return cls('piece', payload)
    
    def get_piece_index(self) -> Optional[int]:
        """
        Extract piece index from have/request/piece messages
        
        Returns:
            int: Piece index, or None if not applicable
        """
        if self.type_name in ['have', 'request']:
            if len(self.payload) >= 4:
                return struct.unpack('!I', self.payload[:4])[0]
        elif self.type_name == 'piece':
            if len(self.payload) >= 4:
                return struct.unpack('!I', self.payload[:4])[0]
        return None
    
    def get_piece_data(self) -> Optional[bytes]:
        """
        Extract piece data from piece message
        
        Returns:
            bytes: Piece data, or None if not a piece message
        """
        if self.type_name == 'piece' and len(self.payload) > 4:
            return self.payload[4:]  # Skip piece index
        return None
    
    def get_bitfield(self) -> Optional[bytes]:
        """
        Extract bitfield from bitfield message
        
        Returns:
            bytes: Bitfield bytes, or None if not a bitfield message
        """
        if self.type_name == 'bitfield':
            return self.payload
        return None
    
    def __str__(self):
        if self.type_name in ['have', 'request']:
            piece_idx = self.get_piece_index()
            return f"Message({self.type_name}, piece_index={piece_idx})"
        elif self.type_name == 'piece':
            piece_idx = self.get_piece_index()
            data_len = len(self.payload) - 4 if len(self.payload) > 4 else 0
            return f"Message({self.type_name}, piece_index={piece_idx}, data_size={data_len})"
        elif self.type_name == 'bitfield':
            return f"Message({self.type_name}, bitfield_size={len(self.payload)})"
        else:
            return f"Message({self.type_name})"
    
    def __repr__(self):
        return self.__str__()


class MessageReader:
    """
    Helper class to read messages from a socket stream
    Handles partial reads and message boundaries
    """
    
    def __init__(self):
        """Initialize message reader with empty buffer"""
        self.buffer = b''
        self.expected_length = None
        self.reading_handshake = True
    
    def feed_data(self, data: bytes):
        """
        Add received data to buffer
        
        Args:
            data (bytes): New data from socket
        """
        self.buffer += data
    
    def get_handshake(self) -> Optional[HandshakeMessage]:
        """
        Try to read a handshake message from buffer
        
        Returns:
            HandshakeMessage if complete handshake is available, None otherwise
        """
        if len(self.buffer) >= HANDSHAKE_MSG_LEN:
            handshake_data = self.buffer[:HANDSHAKE_MSG_LEN]
            try:
                handshake = HandshakeMessage.deserialize(handshake_data)
                self.buffer = self.buffer[HANDSHAKE_MSG_LEN:]
                self.reading_handshake = False
                return handshake
            except ValueError as e:
                # Invalid handshake, might need to clear buffer or handle error
                raise e
        return None
    
    def get_message(self) -> Optional[Message]:
        """
        Try to read a regular message from buffer
        
        Returns:
            Message if complete message is available, None otherwise
        """
        # First, check if we have the length prefix
        if self.expected_length is None:
            if len(self.buffer) >= MESSAGE_LENGTH_LEN:
                self.expected_length = struct.unpack('!I', self.buffer[:MESSAGE_LENGTH_LEN])[0]
            else:
                return None
        
        # Check if we have the complete message
        total_length = MESSAGE_LENGTH_LEN + self.expected_length
        if len(self.buffer) >= total_length:
            message_data = self.buffer[:total_length]
            try:
                message = Message.deserialize(message_data)
                self.buffer = self.buffer[total_length:]
                self.expected_length = None
                return message
            except ValueError as e:
                # Invalid message
                self.expected_length = None
                raise e
        
        return None
    
    def clear_buffer(self):
        """Clear the internal buffer"""
        self.buffer = b''
        self.expected_length = None


class BitfieldHelper:
    """
    Helper class for bitfield operations
    """
    
    @staticmethod
    def create_bitfield(num_pieces: int, pieces_have: List[int] = None) -> bytes:
        """
        Create a bitfield bytes representation
        
        Args:
            num_pieces (int): Total number of pieces
            pieces_have (List[int]): List of piece indices we have (None = have all)
            
        Returns:
            bytes: Bitfield bytes
        """
        # Calculate number of bytes needed
        num_bytes = (num_pieces + 7) // 8
        
        if pieces_have is None:
            # Have all pieces
            bitfield = bytearray([0xFF] * num_bytes)
            # Clear spare bits at the end
            spare_bits = num_bytes * 8 - num_pieces
            if spare_bits > 0:
                bitfield[-1] &= (0xFF << spare_bits)
        else:
            # Start with all zeros
            bitfield = bytearray(num_bytes)
            # Set bits for pieces we have
            for piece_idx in pieces_have:
                if piece_idx < num_pieces:
                    byte_idx = piece_idx // 8
                    bit_idx = 7 - (piece_idx % 8)
                    bitfield[byte_idx] |= (1 << bit_idx)
        
        return bytes(bitfield)
    
    @staticmethod
    def parse_bitfield(bitfield: bytes, num_pieces: int) -> List[int]:
        """
        Parse bitfield bytes to get list of available pieces
        
        Args:
            bitfield (bytes): Bitfield bytes
            num_pieces (int): Total number of pieces
            
        Returns:
            List[int]: List of piece indices that are available
        """
        pieces = []
        for piece_idx in range(num_pieces):
            byte_idx = piece_idx // 8
            bit_idx = 7 - (piece_idx % 8)
            if byte_idx < len(bitfield):
                if bitfield[byte_idx] & (1 << bit_idx):
                    pieces.append(piece_idx)
        return pieces
    
    @staticmethod
    def has_piece(bitfield: bytes, piece_index: int) -> bool:
        """
        Check if a specific piece is set in bitfield
        
        Args:
            bitfield (bytes): Bitfield bytes
            piece_index (int): Piece index to check
            
        Returns:
            bool: True if piece is available
        """
        byte_idx = piece_index // 8
        bit_idx = 7 - (piece_index % 8)
        if byte_idx < len(bitfield):
            return bool(bitfield[byte_idx] & (1 << bit_idx))
        return False
    
    @staticmethod
    def set_piece(bitfield: bytearray, piece_index: int):
        """
        Set a piece bit in bitfield (modifies in place)
        
        Args:
            bitfield (bytearray): Mutable bitfield
            piece_index (int): Piece index to set
        """
        byte_idx = piece_index // 8
        bit_idx = 7 - (piece_index % 8)
        if byte_idx < len(bitfield):
            bitfield[byte_idx] |= (1 << bit_idx)