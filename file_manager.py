"""
file_manager.py - File Management for P2P BitTorrent Implementation
Purpose: Handle file piece storage, retrieval, and reconstruction
"""

import os
import math
import hashlib
from typing import Optional, Set, List
from dataclasses import dataclass

@dataclass
class PieceInfo:
    """
    Information about a file piece
    
    Attributes:
        index (int): Piece index (0-based)
        offset (int): Byte offset in the complete file
        size (int): Size of this piece in bytes
        is_last (bool): Whether this is the last piece
    """
    index: int
    offset: int
    size: int
    is_last: bool


class FileManager:
    """
    Manages file pieces for P2P file sharing
    
    This class handles:
    - Reading pieces from complete file (for seeders)
    - Writing pieces to temporary files (for leechers)
    - Tracking which pieces we have
    - Reconstructing complete file from pieces
    """
    
    def __init__(self, peer_id: int, file_name: str, file_size: int, piece_size: int, has_complete_file: bool = False):
        """
        Initialize the file manager
        
        Args:
            peer_id (int): ID of this peer
            file_name (str): Name of the file being shared
            file_size (int): Total size of file in bytes
            piece_size (int): Size of each piece in bytes
            has_complete_file (bool): Whether we start with complete file
        """
        self.peer_id = peer_id
        self.file_name = file_name
        self.file_size = file_size
        self.piece_size = piece_size
        self.has_complete_file = has_complete_file
        
        # Directories
        self.peer_dir = f"peer_{peer_id}"
        self.temp_dir = os.path.join(self.peer_dir, "temp_pieces")
        
        # File paths
        self.complete_file_path = os.path.join(self.peer_dir, file_name)
        
        # Calculate piece information
        self.num_pieces = math.ceil(file_size / piece_size)
        self.last_piece_size = file_size % piece_size
        if self.last_piece_size == 0 and file_size > 0:
            self.last_piece_size = piece_size
        
        # Track which pieces we have
        if has_complete_file:
            # Seeder has all pieces
            self.pieces_have = set(range(self.num_pieces))
        else:
            # Leecher starts with no pieces
            self.pieces_have = set()
            # Create temp directory for pieces
            os.makedirs(self.temp_dir, exist_ok=True)
        
        # Verify file if we're supposed to have it
        if has_complete_file:
            if not os.path.exists(self.complete_file_path):
                raise FileNotFoundError(f"Seeder {peer_id} missing file: {self.complete_file_path}")
            
            actual_size = os.path.getsize(self.complete_file_path)
            if actual_size != file_size:
                raise ValueError(f"File size mismatch: expected {file_size}, got {actual_size}")
        
        print(f"[FileManager] Peer {peer_id}: {self.num_pieces} pieces, last piece {self.last_piece_size} bytes")
        if has_complete_file:
            print(f"[FileManager] Peer {peer_id}: Starting with complete file")
        else:
            print(f"[FileManager] Peer {peer_id}: Starting with 0/{self.num_pieces} pieces")
    
    def get_piece_info(self, piece_index: int) -> PieceInfo:
        """
        Get information about a specific piece
        
        Args:
            piece_index (int): Index of the piece
            
        Returns:
            PieceInfo: Information about the piece
        """
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise ValueError(f"Invalid piece index: {piece_index}")
        
        offset = piece_index * self.piece_size
        is_last = (piece_index == self.num_pieces - 1)
        size = self.last_piece_size if is_last else self.piece_size
        
        return PieceInfo(
            index=piece_index,
            offset=offset,
            size=size,
            is_last=is_last
        )
    
    def read_piece(self, piece_index: int) -> Optional[bytes]:
        """
        Read a piece from file
        
        Args:
            piece_index (int): Index of piece to read
            
        Returns:
            bytes: Piece data, or None if we don't have it
        """
        if piece_index not in self.pieces_have:
            return None
        
        piece_info = self.get_piece_info(piece_index)
        
        if self.has_complete_file:
            # Read from complete file
            try:
                with open(self.complete_file_path, 'rb') as f:
                    f.seek(piece_info.offset)
                    data = f.read(piece_info.size)
                    return data
            except Exception as e:
                print(f"[FileManager] Error reading piece {piece_index}: {e}")
                return None
        else:
            # Read from temporary piece file
            piece_file = os.path.join(self.temp_dir, f"piece_{piece_index}.tmp")
            if os.path.exists(piece_file):
                try:
                    with open(piece_file, 'rb') as f:
                        data = f.read()
                        return data
                except Exception as e:
                    print(f"[FileManager] Error reading piece file {piece_index}: {e}")
                    return None
            return None
    
    def write_piece(self, piece_index: int, data: bytes) -> bool:
        """
        Write a piece to temporary storage
        
        Args:
            piece_index (int): Index of piece
            data (bytes): Piece data
            
        Returns:
            bool: True if successful
        """
        if piece_index in self.pieces_have:
            print(f"[FileManager] Already have piece {piece_index}")
            return False
        
        piece_info = self.get_piece_info(piece_index)
        
        # Verify size
        if len(data) != piece_info.size:
            print(f"[FileManager] Piece {piece_index} size mismatch: expected {piece_info.size}, got {len(data)}")
            return False
        
        # Write to temporary file
        piece_file = os.path.join(self.temp_dir, f"piece_{piece_index}.tmp")
        try:
            with open(piece_file, 'wb') as f:
                f.write(data)
            
            # Mark as having this piece
            self.pieces_have.add(piece_index)
            print(f"[FileManager] Saved piece {piece_index} ({len(data)} bytes). Progress: {len(self.pieces_have)}/{self.num_pieces}")
            
            return True
        
        except Exception as e:
            print(f"[FileManager] Error writing piece {piece_index}: {e}")
            return False
    
    def has_piece(self, piece_index: int) -> bool:
        """
        Check if we have a specific piece
        
        Args:
            piece_index (int): Piece index
            
        Returns:
            bool: True if we have it
        """
        return piece_index in self.pieces_have
    
    def get_pieces_have(self) -> Set[int]:
        """
        Get set of piece indices we have
        
        Returns:
            Set[int]: Set of piece indices
        """
        return self.pieces_have.copy()
    
    def get_pieces_needed(self) -> Set[int]:
        """
        Get set of piece indices we still need
        
        Returns:
            Set[int]: Set of piece indices we need
        """
        all_pieces = set(range(self.num_pieces))
        return all_pieces - self.pieces_have
    
    def is_complete(self) -> bool:
        """
        Check if we have all pieces
        
        Returns:
            bool: True if file is complete
        """
        return len(self.pieces_have) == self.num_pieces
    
    def get_progress_percentage(self) -> float:
        """
        Get download progress as percentage
        
        Returns:
            float: Progress percentage (0.0 to 100.0)
        """
        if self.num_pieces == 0:
            return 100.0
        return (len(self.pieces_have) / self.num_pieces) * 100.0
    
    def reconstruct_file(self) -> bool:
        """
        Reconstruct the complete file from pieces
        
        Returns:
            bool: True if successful
        """
        if not self.is_complete():
            print(f"[FileManager] Cannot reconstruct - only have {len(self.pieces_have)}/{self.num_pieces} pieces")
            return False
        
        if self.has_complete_file:
            print(f"[FileManager] Already have complete file")
            return True
        
        print(f"[FileManager] Reconstructing {self.file_name} from {self.num_pieces} pieces...")
        
        try:
            # Create the complete file
            with open(self.complete_file_path, 'wb') as outfile:
                for piece_index in range(self.num_pieces):
                    piece_file = os.path.join(self.temp_dir, f"piece_{piece_index}.tmp")
                    
                    if not os.path.exists(piece_file):
                        print(f"[FileManager] Missing piece file: {piece_file}")
                        return False
                    
                    with open(piece_file, 'rb') as infile:
                        data = infile.read()
                        outfile.write(data)
            
            # Verify final size
            final_size = os.path.getsize(self.complete_file_path)
            if final_size != self.file_size:
                print(f"[FileManager] Size mismatch after reconstruction: {final_size} != {self.file_size}")
                os.remove(self.complete_file_path)
                return False
            
            print(f"[FileManager] Successfully reconstructed {self.file_name} ({self.file_size:,} bytes)")
            
            # Clean up temporary pieces
            self.cleanup_temp_pieces()
            
            # Mark as having complete file
            self.has_complete_file = True
            
            return True
        
        except Exception as e:
            print(f"[FileManager] Error reconstructing file: {e}")
            if os.path.exists(self.complete_file_path):
                os.remove(self.complete_file_path)
            return False
    
    def cleanup_temp_pieces(self):
        """Remove temporary piece files after successful reconstruction"""
        if os.path.exists(self.temp_dir):
            for piece_index in range(self.num_pieces):
                piece_file = os.path.join(self.temp_dir, f"piece_{piece_index}.tmp")
                if os.path.exists(piece_file):
                    try:
                        os.remove(piece_file)
                    except:
                        pass
            
            try:
                os.rmdir(self.temp_dir)
                print(f"[FileManager] Cleaned up temporary pieces")
            except:
                pass
    
    def verify_piece(self, piece_index: int, data: bytes) -> bool:
        """
        Verify a piece's integrity (simplified - just checks size)
        
        In a real implementation, this would check SHA hash
        
        Args:
            piece_index (int): Piece index
            data (bytes): Piece data
            
        Returns:
            bool: True if piece is valid
        """
        piece_info = self.get_piece_info(piece_index)
        return len(data) == piece_info.size
    
    def get_piece_hash(self, piece_index: int) -> Optional[str]:
        """
        Get SHA1 hash of a piece (for verification)
        
        Args:
            piece_index (int): Piece index
            
        Returns:
            str: Hex digest of SHA1 hash, or None
        """
        data = self.read_piece(piece_index)
        if data:
            return hashlib.sha1(data).hexdigest()
        return None
    
    def __str__(self):
        """String representation"""
        return f"FileManager(peer={self.peer_id}, file={self.file_name}, pieces={len(self.pieces_have)}/{self.num_pieces})"
    
    def __repr__(self):
        """Representation"""
        return self.__str__()


# Test function
if __name__ == "__main__":
    """Test the FileManager"""
    print("Testing FileManager...")
    
    # Test seeder
    fm_seeder = FileManager(
        peer_id=1001,
        file_name="tree.jpg",
        file_size=24301474,
        piece_size=16384,
        has_complete_file=True
    )
    
    print(f"\nSeeder: {fm_seeder}")
    print(f"Has piece 0: {fm_seeder.has_piece(0)}")
    print(f"Has piece 1483: {fm_seeder.has_piece(1483)}")
    print(f"Is complete: {fm_seeder.is_complete()}")
    
    # Read first piece
    piece_data = fm_seeder.read_piece(0)
    if piece_data:
        print(f"First piece size: {len(piece_data)} bytes")
    
    # Test leecher
    fm_leecher = FileManager(
        peer_id=1002,
        file_name="tree.jpg",
        file_size=24301474,
        piece_size=16384,
        has_complete_file=False
    )
    
    print(f"\nLeecher: {fm_leecher}")
    print(f"Has piece 0: {fm_leecher.has_piece(0)}")
    print(f"Needs pieces: {len(fm_leecher.get_pieces_needed())}")
    print(f"Progress: {fm_leecher.get_progress_percentage():.1f}%")