"""
Constants and configuration values for P2P BitTorrent Implementation
Purpose: Define all protocol constants, message types, and global values
"""

# Protocol Constants
HANDSHAKE_HEADER = b'P2PFILESHARINGPROJ'
HANDSHAKE_HEADER_LEN = 18
HANDSHAKE_ZERO_BITS_LEN = 10
HANDSHAKE_PEERID_LEN = 4
HANDSHAKE_MSG_LEN = 32

# Message Types
MESSAGE_TYPES = {
    'choke': 0,
    'unchoke': 1,
    'interested': 2,
    'not_interested': 3,
    'have': 4,
    'bitfield': 5,
    'request': 6,
    'piece': 7
}

# Reverse mapping for received messages
MESSAGE_ID_TO_TYPE = {v: k for k, v in MESSAGE_TYPES.items()}

# Message Length Constants
MESSAGE_LENGTH_LEN = 4  # 4 bytes for message length
MESSAGE_TYPE_LEN = 1     # 1 byte for message type
PIECE_INDEX_LEN = 4      # 4 bytes for piece index

# Network Constants
DEFAULT_BUFFER_SIZE = 4096
CONNECTION_TIMEOUT = 30  # seconds
HANDSHAKE_TIMEOUT = 10   # seconds

# File Constants
DEFAULT_PIECE_SIZE = 16384  # Will be overridden by Common.cfg

# Logging Constants
LOG_FORMAT = '[%(asctime)s]: %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'