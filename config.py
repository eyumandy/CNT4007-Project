"""
Configuration file parser for P2P BitTorrent Implementation
Purpose: Parse Common.cfg and PeerInfo.cfg configuration files
"""

import os
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

@dataclass
class CommonConfig:
    """
    Data class to store Common.cfg parameters
    
    Attributes:
        number_of_preferred_neighbors (int): Number of preferred neighbors (k value)
        unchoking_interval (int): Interval in seconds for recalculating preferred neighbors
        optimistic_unchoking_interval (int): Interval in seconds for optimistic unchoking
        file_name (str): Name of the file being shared
        file_size (int): Total size of the file in bytes
        piece_size (int): Size of each piece in bytes
        num_pieces (int): Calculated number of pieces (ceiling of file_size/piece_size)
        last_piece_size (int): Size of the last piece (may be smaller than piece_size)
    """
    number_of_preferred_neighbors: int
    unchoking_interval: int
    optimistic_unchoking_interval: int
    file_name: str
    file_size: int
    piece_size: int
    num_pieces: int = 0  # Calculated field
    last_piece_size: int = 0  # Calculated field
    
    def __post_init__(self):
        """Calculate derived fields after initialization"""
        # Calculate number of pieces
        self.num_pieces = (self.file_size + self.piece_size - 1) // self.piece_size
        
        # Calculate size of last piece
        self.last_piece_size = self.file_size % self.piece_size
        if self.last_piece_size == 0 and self.file_size > 0:
            self.last_piece_size = self.piece_size
        
        print(f"[DEBUG] File will be split into {self.num_pieces} pieces")
        print(f"[DEBUG] Last piece size: {self.last_piece_size} bytes")

@dataclass
class PeerInfo:
    """
    Data class to store information about a single peer
    
    Attributes:
        peer_id (int): Unique identifier for the peer
        hostname (str): Hostname or IP address of the peer
        port (int): Port number the peer listens on
        has_file (bool): Whether the peer has the complete file initially
    """
    peer_id: int
    hostname: str
    port: int
    has_file: bool
    
    def __str__(self):
        """String representation of peer info"""
        file_status = "has file" if self.has_file else "no file"
        return f"Peer {self.peer_id} at {self.hostname}:{self.port} ({file_status})"

class ConfigParser:
    """
    Parser for P2P configuration files
    Handles parsing of Common.cfg and PeerInfo.cfg
    """
    
    def __init__(self):
        """Initialize the configuration parser"""
        self.common_config = None
        self.peer_info = {}
    
    def parse_common_config(self, filename: str = 'Common.cfg') -> CommonConfig:
        """
        Parse the Common.cfg file
        
        Args:
            filename (str): Path to Common.cfg file
            
        Returns:
            CommonConfig: Parsed configuration object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file has invalid format or values
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Configuration file {filename} not found")
        
        config_dict = {}
        
        try:
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip empty lines and comments
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Split on first space to handle filenames with spaces
                    parts = line.split(None, 1)
                    if len(parts) != 2:
                        raise ValueError(f"Line {line_num}: Invalid format - expected 'key value'")
                    
                    key, value = parts
                    config_dict[key] = value
            
            # Validate all required fields are present
            required_fields = [
                'NumberOfPreferredNeighbors',
                'UnchokingInterval', 
                'OptimisticUnchokingInterval',
                'FileName',
                'FileSize',
                'PieceSize'
            ]
            
            missing_fields = [field for field in required_fields if field not in config_dict]
            if missing_fields:
                raise ValueError(f"Missing required fields in {filename}: {', '.join(missing_fields)}")
            
            # Parse and validate each field
            try:
                num_preferred = int(config_dict['NumberOfPreferredNeighbors'])
                if num_preferred <= 0:
                    raise ValueError("NumberOfPreferredNeighbors must be positive")
                
                unchoking_interval = int(config_dict['UnchokingInterval'])
                if unchoking_interval <= 0:
                    raise ValueError("UnchokingInterval must be positive")
                
                opt_unchoking_interval = int(config_dict['OptimisticUnchokingInterval'])
                if opt_unchoking_interval <= 0:
                    raise ValueError("OptimisticUnchokingInterval must be positive")
                
                file_size = int(config_dict['FileSize'])
                if file_size <= 0:
                    raise ValueError("FileSize must be positive")
                
                piece_size = int(config_dict['PieceSize'])
                if piece_size <= 0:
                    raise ValueError("PieceSize must be positive")
                
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"Invalid integer value in {filename}")
                raise
            
            # Create and store config object
            self.common_config = CommonConfig(
                number_of_preferred_neighbors=num_preferred,
                unchoking_interval=unchoking_interval,
                optimistic_unchoking_interval=opt_unchoking_interval,
                file_name=config_dict['FileName'],
                file_size=file_size,
                piece_size=piece_size
            )
            
            return self.common_config
            
        except IOError as e:
            raise IOError(f"Error reading {filename}: {e}")
    
    def parse_peer_info(self, filename: str = 'PeerInfo.cfg') -> Dict[int, PeerInfo]:
        """
        Parse the PeerInfo.cfg file
        
        Args:
            filename (str): Path to PeerInfo.cfg file
            
        Returns:
            Dict[int, PeerInfo]: Dictionary mapping peer_id to PeerInfo objects
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file has invalid format or values
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Configuration file {filename} not found")
        
        peers = {}
        
        try:
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip empty lines and comments
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse peer information
                    parts = line.split()
                    if len(parts) != 4:
                        raise ValueError(
                            f"Line {line_num}: Invalid format - "
                            f"expected 'peer_id hostname port has_file', got {len(parts)} fields"
                        )
                    
                    try:
                        peer_id = int(parts[0])
                        hostname = parts[1]
                        port = int(parts[2])
                        has_file = int(parts[3])
                        
                        # Validate values
                        if peer_id <= 0:
                            raise ValueError(f"Line {line_num}: Peer ID must be positive")
                        
                        if peer_id in peers:
                            raise ValueError(f"Line {line_num}: Duplicate peer ID {peer_id}")
                        
                        if port <= 0 or port > 65535:
                            raise ValueError(f"Line {line_num}: Invalid port number {port}")
                        
                        if has_file not in [0, 1]:
                            raise ValueError(f"Line {line_num}: has_file must be 0 or 1")
                        
                        # Create PeerInfo object
                        peer_info = PeerInfo(
                            peer_id=peer_id,
                            hostname=hostname,
                            port=port,
                            has_file=(has_file == 1)
                        )
                        
                        peers[peer_id] = peer_info
                        
                    except ValueError as e:
                        if "invalid literal" in str(e):
                            raise ValueError(f"Line {line_num}: Invalid integer value")
                        raise
            
            if not peers:
                raise ValueError(f"No valid peer entries found in {filename}")
            
            self.peer_info = peers
            return peers
            
        except IOError as e:
            raise IOError(f"Error reading {filename}: {e}")
    
    def get_peers_to_connect(self, my_peer_id: int) -> List[PeerInfo]:
        """
        Get list of peers that this peer should connect to
        (all peers with lower peer IDs, as per project specification)
        
        Args:
            my_peer_id (int): ID of the current peer
            
        Returns:
            List[PeerInfo]: List of peers to connect to, sorted by peer ID
        """
        if not self.peer_info:
            raise ValueError("PeerInfo not loaded. Call parse_peer_info() first")
        
        if my_peer_id not in self.peer_info:
            raise ValueError(f"Peer ID {my_peer_id} not found in peer info")
        
        peers_to_connect = [
            peer for peer_id, peer in self.peer_info.items()
            if peer_id < my_peer_id
        ]
        
        return sorted(peers_to_connect, key=lambda p: p.peer_id)
    
    def get_all_other_peers(self, my_peer_id: int) -> List[PeerInfo]:
        """
        Get list of all peers except this one
        
        Args:
            my_peer_id (int): ID of the current peer
            
        Returns:
            List[PeerInfo]: List of all other peers
        """
        if not self.peer_info:
            raise ValueError("PeerInfo not loaded. Call parse_peer_info() first")
        
        return [
            peer for peer_id, peer in self.peer_info.items()
            if peer_id != my_peer_id
        ]
    
    def get_my_info(self, my_peer_id: int) -> PeerInfo:
        """
        Get the PeerInfo object for this peer
        
        Args:
            my_peer_id (int): ID of the current peer
            
        Returns:
            PeerInfo: Information about this peer
        """
        if not self.peer_info:
            raise ValueError("PeerInfo not loaded. Call parse_peer_info() first")
        
        if my_peer_id not in self.peer_info:
            raise ValueError(f"Peer ID {my_peer_id} not found in peer info")
        
        return self.peer_info[my_peer_id]