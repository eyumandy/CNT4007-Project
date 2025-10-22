"""
Logging functionality for P2P BitTorrent Implementation
Purpose: Setup and manage logging for peer processes
"""

import logging
import sys
from datetime import datetime
from constants import LOG_FORMAT, LOG_DATE_FORMAT

def setup_logger(peer_id):
    """
    Setup logger for a specific peer
    
    Args:
        peer_id (int): The peer ID for this logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger with peer-specific name
    logger = logging.getLogger(f'peer_{peer_id}')
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Create file handler for peer's log file
    log_filename = f'log_peer_{peer_id}.log'
    file_handler = logging.FileHandler(log_filename, mode='w')
    file_handler.setLevel(logging.INFO)
    
    # Create console handler for debugging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_handler.setFormatter(formatter)
    
    # Console can have simpler format for debugging
    console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class PeerLogger:
    """
    Wrapper class for peer-specific logging with predefined message formats
    """
    
    def __init__(self, peer_id):
        """
        Initialize peer logger
        
        Args:
            peer_id (int): The ID of this peer
        """
        self.peer_id = peer_id
        self.logger = setup_logger(peer_id)
    
    def log_tcp_connection_made(self, other_peer_id):
        """Log when this peer makes a connection to another peer"""
        self.logger.info(f"Peer {self.peer_id} makes a connection to Peer {other_peer_id}.")
    
    def log_tcp_connection_received(self, other_peer_id):
        """Log when this peer receives a connection from another peer"""
        self.logger.info(f"Peer {self.peer_id} is connected from Peer {other_peer_id}.")
    
    def log_preferred_neighbors(self, neighbor_list):
        """Log the list of preferred neighbors"""
        neighbors_str = ','.join(map(str, neighbor_list))
        self.logger.info(f"Peer {self.peer_id} has the preferred neighbors {neighbors_str}.")
    
    def log_optimistic_unchoked(self, neighbor_id):
        """Log the optimistically unchoked neighbor"""
        self.logger.info(f"Peer {self.peer_id} has the optimistically unchoked neighbor {neighbor_id}.")
    
    def log_unchoked_by(self, other_peer_id):
        """Log when this peer is unchoked by another peer"""
        self.logger.info(f"Peer {self.peer_id} is unchoked by {other_peer_id}.")
    
    def log_choked_by(self, other_peer_id):
        """Log when this peer is choked by another peer"""
        self.logger.info(f"Peer {self.peer_id} is choked by {other_peer_id}.")
    
    def log_have_message(self, other_peer_id, piece_index):
        """Log when receiving a have message"""
        self.logger.info(f"Peer {self.peer_id} received the 'have' message from {other_peer_id} for the piece {piece_index}.")
    
    def log_interested_message(self, other_peer_id):
        """Log when receiving an interested message"""
        self.logger.info(f"Peer {self.peer_id} received the 'interested' message from {other_peer_id}.")
    
    def log_not_interested_message(self, other_peer_id):
        """Log when receiving a not interested message"""
        self.logger.info(f"Peer {self.peer_id} received the 'not interested' message from {other_peer_id}.")
    
    def log_piece_downloaded(self, piece_index, other_peer_id, num_pieces):
        """Log when a piece is completely downloaded"""
        self.logger.info(f"Peer {self.peer_id} has downloaded the piece {piece_index} from {other_peer_id}. Now the number of pieces it has is {num_pieces}.")
    
    def log_download_complete(self):
        """Log when the complete file has been downloaded"""
        self.logger.info(f"Peer {self.peer_id} has downloaded the complete file.")
    
    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message"""
        self.logger.error(message)