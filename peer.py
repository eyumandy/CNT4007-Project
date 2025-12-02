"""
peer.py - Main Peer Class for P2P BitTorrent Implementation
Purpose: Orchestrate peer behavior, manage state, and handle protocol logic
"""

import threading
import time
import random
import socket
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from queue import Queue, Empty
from datetime import datetime
import os

# Rich imports for beautiful console
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box

# Project imports
from config import ConfigParser, CommonConfig, PeerInfo
from network import P2PServer, P2PClient, PeerConnection, ConnectionManager
from message import Message, HandshakeMessage, BitfieldHelper
from logger import PeerLogger
from constants import *
from file_manager import FileManager

# Console for rich output
console = Console()

@dataclass
class PeerState:
    """
    Track state for each connected peer
    
    Attributes:
        peer_id (int): ID of the peer
        am_choking (bool): True if we are choking this peer
        am_interested (bool): True if we are interested in this peer
        peer_choking (bool): True if this peer is choking us
        peer_interested (bool): True if this peer is interested in us
        bitfield (bytearray): Pieces this peer has
        download_rate (float): Download rate from this peer (bytes/sec)
        upload_rate (float): Upload rate to this peer (bytes/sec)
        last_piece_time (float): Time of last piece exchange
        bytes_downloaded (int): Total bytes downloaded from this peer
        bytes_uploaded (int): Total bytes uploaded to this peer
    """
    peer_id: int
    am_choking: bool = True
    am_interested: bool = False
    peer_choking: bool = True
    peer_interested: bool = False
    bitfield: Optional[bytearray] = None
    download_rate: float = 0.0
    upload_rate: float = 0.0
    last_piece_time: float = field(default_factory=time.time)
    bytes_downloaded: int = 0
    bytes_uploaded: int = 0
    pending_request: Optional[int] = None  # Piece index we've requested


class Peer:
    """
    Main Peer class that orchestrates all P2P operations
    """
    
    def __init__(self, peer_id: int, config: CommonConfig, peer_info: Dict[int, PeerInfo]):
        """
        Initialize a peer
        
        Args:
            peer_id (int): This peer's ID
            config (CommonConfig): Common configuration
            peer_info (Dict[int, PeerInfo]): All peer information
        """
        self.peer_id = peer_id
        self.config = config
        self.all_peers = peer_info
        self.my_info = peer_info[peer_id]
        
        # Logging
        self.logger = PeerLogger(peer_id)
        
        # Network components
        self.server = None
        self.client = P2PClient(peer_id, self.logger)
        self.connections = {}  # peer_id -> PeerConnection
        self.peer_states = {}  # peer_id -> PeerState
        
        # Rich console components
        self.console = console
        
        # File management with FileManager
        self.peer_dir = f"peer_{peer_id}"
        self.has_file = self.my_info.has_file
        
        # Initialize FileManager
        self.file_manager = FileManager(
            peer_id=peer_id,
            file_name=config.file_name,
            file_size=config.file_size,
            piece_size=config.piece_size,
            has_complete_file=self.has_file
        )
        
        # Use FileManager's piece tracking
        self.completed_pieces = self.file_manager.get_pieces_have()
        self.pieces_needed = self.file_manager.get_pieces_needed()
        self.my_bitfield = self._initialize_bitfield()
        
        # Track pending requests
        self.pending_requests = {}  # peer_id -> piece_index
        
        # Choking state
        self.preferred_neighbors = []
        self.optimistic_unchoked = None
        
        # Threading
        self.running = False
        self.lock = threading.Lock()
        
        # Progress bar
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        
        # Statistics
        self.start_time = time.time()
        self.total_downloaded = 0
        self.total_uploaded = 0
        
    def _initialize_bitfield(self) -> bytearray:
        """
        Initialize our bitfield based on what pieces we have
        
        Returns:
            bytearray: Our bitfield
        """
        num_pieces = self.config.num_pieces
        
        # Use FileManager's piece tracking
        pieces_have = self.file_manager.get_pieces_have()
        
        if self.has_file:
            self.console.print(f"[green]Peer {self.peer_id}: Starting with complete file[/green]")
            bitfield = BitfieldHelper.create_bitfield(num_pieces, list(pieces_have))
        else:
            self.console.print(f"[yellow]Peer {self.peer_id}: Starting with no file[/yellow]")
            bitfield = BitfieldHelper.create_bitfield(num_pieces, [])
        
        return bytearray(bitfield)

    
    def start(self):
        """
        Start the peer process
        """
        self.running = True
        
        # Create peer directory if it doesn't exist
        if not os.path.exists(self.peer_dir):
            os.makedirs(self.peer_dir)
            self.logger.debug(f"Created directory: {self.peer_dir}")
        
        # Display startup panel
        self._show_startup_info()
        
        # Start server
        self.server = P2PServer(
            self.peer_id,
            '0.0.0.0',  # Bind to all interfaces
            self.my_info.port,
            self._handle_incoming_connection,
            self.logger
        )
        self.server.start()
        
        # Connect to previous peers
        self._connect_to_peers()
        
        # Start scheduler threads
        self._start_schedulers()
        
        # Start UI update thread
        ui_thread = threading.Thread(target=self._update_ui, daemon=True)
        ui_thread.start()
        
        # Main loop
        try:
            while self.running:
                time.sleep(1)
                
                # Check if all peers have the file
                if self._check_termination():
                    self.console.print("[bold green]All peers have completed download![/bold green]")
                    self.logger.log_download_complete()
                    break
        
        except KeyboardInterrupt:
            self.console.print("[red]Shutting down peer...[/red]")
        
        finally:
            self.stop()
    
    def _show_startup_info(self):
        """Display startup information using rich"""
        startup_info = Table(title=f"Peer {self.peer_id} Starting", box=box.ROUNDED)
        startup_info.add_column("Property", style="cyan")
        startup_info.add_column("Value", style="green")
        
        startup_info.add_row("Peer ID", str(self.peer_id))
        startup_info.add_row("Host", self.my_info.hostname)
        startup_info.add_row("Port", str(self.my_info.port))
        startup_info.add_row("Has File", "✓ Yes" if self.has_file else "✗ No")
        startup_info.add_row("File Name", self.config.file_name)
        startup_info.add_row("File Size", f"{self.config.file_size:,} bytes")
        startup_info.add_row("Total Pieces", str(self.config.num_pieces))
        startup_info.add_row("Piece Size", f"{self.config.piece_size:,} bytes")
        
        self.console.print(startup_info)
    
    def _connect_to_peers(self):
        """Connect to all peers with lower IDs"""
        peers_to_connect = [
            p for pid, p in self.all_peers.items()
            if pid < self.peer_id
        ]
        
        if peers_to_connect:
            self.console.print(f"[cyan]Connecting to {len(peers_to_connect)} peers...[/cyan]")
            
            for peer_info in peers_to_connect:
                conn = self.client.connect_to_peer(
                    peer_info.peer_id,
                    peer_info.hostname,  # Use hostname from config
                    peer_info.port,
                    self._handle_outgoing_connection
                )
                
                if conn:
                    self.console.print(f"[green]✓[/green] Connected to Peer {peer_info.peer_id}")
                else:
                    self.console.print(f"[red]✗[/red] Failed to connect to Peer {peer_info.peer_id}")
    
    def _handle_incoming_connection(self, peer_conn: PeerConnection, is_incoming: bool):
        """Handle a new incoming connection"""
        peer_id = peer_conn.peer_id
        
        with self.lock:
            self.connections[peer_id] = peer_conn
            self.peer_states[peer_id] = PeerState(peer_id)
        
        # Send bitfield
        self._send_bitfield(peer_conn)
        
        # Start message handler for this peer
        handler_thread = threading.Thread(
            target=self._handle_peer_messages,
            args=(peer_conn,),
            daemon=True
        )
        handler_thread.start()
    
    def _handle_outgoing_connection(self, peer_conn: PeerConnection, is_incoming: bool):
        """Handle a new outgoing connection"""
        peer_id = peer_conn.peer_id
        
        with self.lock:
            self.connections[peer_id] = peer_conn
            self.peer_states[peer_id] = PeerState(peer_id)
        
        # Send bitfield
        self._send_bitfield(peer_conn)
        
        # Start message handler for this peer
        handler_thread = threading.Thread(
            target=self._handle_peer_messages,
            args=(peer_conn,),
            daemon=True
        )
        handler_thread.start()
    
    def _send_bitfield(self, peer_conn: PeerConnection):
        """Send our bitfield to a peer"""
        # Always send bitfield, even if empty (protocol requirement)
        bitfield_msg = Message.create_bitfield(bytes(self.my_bitfield))
        try:
            peer_conn.socket.send(bitfield_msg.serialize())
            self.logger.debug(f"Sent bitfield to peer {peer_conn.peer_id}")
            self.console.print(f"[cyan]→ Sent bitfield to Peer {peer_conn.peer_id}[/cyan]")
        except Exception as e:
            self.logger.error(f"Failed to send bitfield to peer {peer_conn.peer_id}: {e}")
    
    def _handle_peer_messages(self, peer_conn: PeerConnection):
        """
        Handle incoming messages from a peer
        
        Args:
            peer_conn (PeerConnection): Connection to handle
        """
        peer_id = peer_conn.peer_id
        
        try:
            while self.running and peer_id in self.connections:
                try:
                    peer_conn.socket.settimeout(5.0)  # Increased timeout
                    data = peer_conn.socket.recv(DEFAULT_BUFFER_SIZE)
                    
                    if not data:
                        self.logger.debug(f"Connection closed by peer {peer_id}")
                        break
                    
                    peer_conn.message_reader.feed_data(data)
                    
                    # Process complete messages
                    while True:
                        msg = peer_conn.message_reader.get_message()
                        if msg is None:
                            break
                        
                        self._process_message(peer_id, msg)
                
                except socket.timeout:
                    # Timeout is OK, just continue
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error handling peer {peer_id}: {e}")
                    break
        
        finally:
            self._remove_peer(peer_id)
    
    def _process_message(self, peer_id: int, msg: Message):
        """
        Process a message from a peer
        
        Args:
            peer_id (int): ID of peer who sent the message
            msg (Message): Message to process
        """
        state = self.peer_states.get(peer_id)
        if not state:
            return
        
        msg_type = msg.type_name
        
        # Create rich formatted log entry
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.print(f"[dim]{timestamp}[/dim] [blue]Peer {peer_id}[/blue] → [yellow]{msg_type}[/yellow]")
        
        if msg_type == 'bitfield':
            self._handle_bitfield(peer_id, msg)
        elif msg_type == 'interested':
            self._handle_interested(peer_id)
        elif msg_type == 'not_interested':
            self._handle_not_interested(peer_id)
        elif msg_type == 'choke':
            self._handle_choke(peer_id)
        elif msg_type == 'unchoke':
            self._handle_unchoke(peer_id)
        elif msg_type == 'have':
            self._handle_have(peer_id, msg)
        elif msg_type == 'request':
            self._handle_request(peer_id, msg)
        elif msg_type == 'piece':
            self._handle_piece(peer_id, msg)
    
    def _handle_bitfield(self, peer_id: int, msg: Message):
        """Handle bitfield message"""
        bitfield_bytes = msg.get_bitfield()
        if bitfield_bytes:
            state = self.peer_states[peer_id]
            state.bitfield = bytearray(bitfield_bytes)
            
            # Check if we should be interested
            pieces_they_have = set(BitfieldHelper.parse_bitfield(bitfield_bytes, self.config.num_pieces))
            interesting_pieces = pieces_they_have & self.pieces_needed
            
            if interesting_pieces:
                self._send_interested(peer_id)
                state.am_interested = True
                self.console.print(f"[green]→ Interested in Peer {peer_id} ({len(interesting_pieces)} pieces)[/green]")
            else:
                self._send_not_interested(peer_id)
                state.am_interested = False
                self.console.print(f"[yellow]→ Not interested in Peer {peer_id}[/yellow]")
    
    def _handle_interested(self, peer_id: int):
        """Handle interested message"""
        state = self.peer_states[peer_id]
        state.peer_interested = True
        self.logger.log_interested_message(peer_id)
        self.console.print(f"[cyan]Peer {peer_id} is interested in us[/cyan]")
    
    def _handle_not_interested(self, peer_id: int):
        """Handle not interested message"""
        state = self.peer_states[peer_id]
        state.peer_interested = False
        self.logger.log_not_interested_message(peer_id)
        self.console.print(f"[dim]Peer {peer_id} is not interested[/dim]")
    
    def _handle_choke(self, peer_id: int):
        """Handle choke message"""
        state = self.peer_states[peer_id]
        state.peer_choking = True
        state.pending_request = None
        self.logger.log_choked_by(peer_id)
        self.console.print(f"[red]Choked by Peer {peer_id}[/red]")
    
    def _handle_unchoke(self, peer_id: int):
        """Handle unchoke message"""
        state = self.peer_states[peer_id]
        state.peer_choking = False
        self.logger.log_unchoked_by(peer_id)
        self.console.print(f"[green]Unchoked by Peer {peer_id}[/green]")
        
        # Request a piece if we're interested
        if state.am_interested:
            self._request_piece(peer_id)
    
    def _handle_have(self, peer_id: int, msg: Message):
        """Handle have message"""
        piece_index = msg.get_piece_index()
        if piece_index is not None:
            state = self.peer_states[peer_id]
            if state.bitfield:
                BitfieldHelper.set_piece(state.bitfield, piece_index)
            
            self.logger.log_have_message(peer_id, piece_index)
            
            # Update interest
            if piece_index in self.pieces_needed and not state.am_interested:
                self._send_interested(peer_id)
                state.am_interested = True
    
    def _handle_request(self, peer_id: int, msg: Message):
        """Handle request message - send the piece if we have it and peer is unchoked"""
        piece_index = msg.get_piece_index()
        if piece_index is None:
            return
        
        self.console.print(f"[yellow]← Request for piece {piece_index} from Peer {peer_id}[/yellow]")
        
        state = self.peer_states.get(peer_id)
        if not state:
            return
        
        # Check if peer is unchoked
        if state.am_choking:
            self.console.print(f"[red]Peer {peer_id} is choked, ignoring request[/red]")
            return
        
        # Check if we have the piece
        if not self.file_manager.has_piece(piece_index):
            self.console.print(f"[red]Don't have piece {piece_index}[/red]")
            return
        
        # Read the piece
        piece_data = self.file_manager.read_piece(piece_index)
        if piece_data:
            # Send the piece
            piece_msg = Message.create_piece(piece_index, piece_data)
            self.connections[peer_id].socket.send(piece_msg.serialize())
            
            # Update upload stats
            state.bytes_uploaded += len(piece_data)
            state.upload_rate = state.bytes_uploaded / max(1, time.time() - self.start_time)
            
            self.console.print(f"[green]→ Sent piece {piece_index} to Peer {peer_id} ({len(piece_data)} bytes)[/green]")
    
    def _handle_piece(self, peer_id: int, msg: Message):
        """Handle piece message - save the received piece"""
        piece_index = msg.get_piece_index()
        piece_data = msg.get_piece_data()
        
        if piece_index is None or piece_data is None:
            return
        
        self.console.print(f"[green]← Received piece {piece_index} from Peer {peer_id} ({len(piece_data)} bytes)[/green]")
        
        # Clear pending request
        if peer_id in self.pending_requests:
            del self.pending_requests[peer_id]
        
        state = self.peer_states.get(peer_id)
        if state:
            state.pending_request = None
            # Update download stats
            state.bytes_downloaded += len(piece_data)
            state.download_rate = state.bytes_downloaded / max(1, time.time() - self.start_time)
        
        # Save the piece
        if self.file_manager.write_piece(piece_index, piece_data):
            # Update our tracking
            self.completed_pieces = self.file_manager.get_pieces_have()
            self.pieces_needed = self.file_manager.get_pieces_needed()
            
            # Update our bitfield
            BitfieldHelper.set_piece(self.my_bitfield, piece_index)
            
            # Log the download
            num_pieces = len(self.completed_pieces)
            self.logger.log_piece_downloaded(piece_index, peer_id, num_pieces)
            
            # Show progress
            progress = self.file_manager.get_progress_percentage()
            self.console.print(f"[bold cyan]Progress: {progress:.1f}% ({num_pieces}/{self.config.num_pieces} pieces)[/bold cyan]")
            
            # Send have message to all peers
            self._broadcast_have(piece_index)
            
            # Check if download is complete
            if self.file_manager.is_complete():
                self.console.print("[bold green]Download complete! Reconstructing file...[/bold green]")
                if self.file_manager.reconstruct_file():
                    self.logger.log_download_complete()
                    self.has_file = True
                    self.console.print(f"[bold green]✓ File saved to {self.peer_dir}/{self.config.file_name}[/bold green]")
            
            # Update interest in peers
            self._update_interests()
            
            # Request next piece if still unchoked
            if state and not state.peer_choking and state.am_interested:
                self._request_piece(peer_id)
    
    def _send_interested(self, peer_id: int):
        """Send interested message to a peer"""
        if peer_id in self.connections:
            msg = Message.create_interested()
            self.connections[peer_id].socket.send(msg.serialize())
    
    def _send_not_interested(self, peer_id: int):
        """Send not interested message to a peer"""
        if peer_id in self.connections:
            msg = Message.create_not_interested()
            self.connections[peer_id].socket.send(msg.serialize())
    
    def _send_choke(self, peer_id: int):
        """Send choke message to a peer"""
        if peer_id in self.connections:
            msg = Message.create_choke()
            self.connections[peer_id].socket.send(msg.serialize())
            self.peer_states[peer_id].am_choking = True
    
    def _send_unchoke(self, peer_id: int):
        """Send unchoke message to a peer"""
        if peer_id in self.connections:
            msg = Message.create_unchoke()
            self.connections[peer_id].socket.send(msg.serialize())
            self.peer_states[peer_id].am_choking = False
    
    def _broadcast_have(self, piece_index: int):
        """Broadcast have message to all connected peers"""
        have_msg = Message.create_have(piece_index)
        for peer_id in self.connections:
            try:
                self.connections[peer_id].socket.send(have_msg.serialize())
            except:
                pass
        self.console.print(f"[magenta]→ Broadcasted have for piece {piece_index}[/magenta]")
    
    def _update_interests(self):
        """Update interest status for all peers based on what pieces they have"""
        for peer_id, state in self.peer_states.items():
            if state.bitfield:
                peer_pieces = set(BitfieldHelper.parse_bitfield(state.bitfield, self.config.num_pieces))
                interesting_pieces = peer_pieces & self.pieces_needed
                
                if interesting_pieces and not state.am_interested:
                    # Became interested
                    self._send_interested(peer_id)
                    state.am_interested = True
                elif not interesting_pieces and state.am_interested:
                    # No longer interested
                    self._send_not_interested(peer_id)
                    state.am_interested = False
    
    def _request_piece(self, peer_id: int):
        """Request a piece from a peer"""
        state = self.peer_states.get(peer_id)
        if not state or not state.bitfield:
            return
        
        # Find pieces this peer has that we need
        peer_pieces = set(BitfieldHelper.parse_bitfield(state.bitfield, self.config.num_pieces))
        needed_from_peer = peer_pieces & self.pieces_needed
        
        if not needed_from_peer:
            # No pieces we need from this peer
            self._send_not_interested(peer_id)
            state.am_interested = False
            return
        
        # Don't request if we already have a pending request with this peer
        if peer_id in self.pending_requests:
            return
        
        # Select a random piece we need (as per project spec)
        piece_index = random.choice(list(needed_from_peer))
        
        # Send request
        request_msg = Message.create_request(piece_index)
        self.connections[peer_id].socket.send(request_msg.serialize())
        
        # Track pending request
        self.pending_requests[peer_id] = piece_index
        state.pending_request = piece_index
        
        self.console.print(f"[cyan]→ Requesting piece {piece_index} from Peer {peer_id}[/cyan]")
    
    def _start_schedulers(self):
        """Start the choking/unchoking scheduler threads"""
        # Preferred neighbors scheduler
        pref_thread = threading.Thread(
            target=self._preferred_neighbors_scheduler,
            daemon=True
        )
        pref_thread.start()
        
        # Optimistic unchoking scheduler
        opt_thread = threading.Thread(
            target=self._optimistic_unchoking_scheduler,
            daemon=True
        )
        opt_thread.start()
    
    def _preferred_neighbors_scheduler(self):
        """
        Recalculate preferred neighbors every p seconds
        """
        while self.running:
            time.sleep(self.config.unchoking_interval)
            self._recalculate_preferred_neighbors()
    
    def _optimistic_unchoking_scheduler(self):
        """
        Select optimistically unchoked neighbor every m seconds
        """
        while self.running:
            time.sleep(self.config.optimistic_unchoking_interval)
            self._select_optimistic_unchoked()
    
    def _recalculate_preferred_neighbors(self):
        """Recalculate preferred neighbors based on download rates"""
        with self.lock:
            k = self.config.number_of_preferred_neighbors
            
            # Get interested peers
            interested_peers = [
                (pid, state) for pid, state in self.peer_states.items()
                if state.peer_interested
            ]
            
            if not interested_peers:
                return
            
            # Sort by download rate if we're downloading, randomly if we have complete file
            if self.has_file:
                # Random selection for seeders
                random.shuffle(interested_peers)
                new_preferred = [pid for pid, _ in interested_peers[:k]]
            else:
                # Sort by download rate for leechers
                interested_peers.sort(key=lambda x: x[1].download_rate, reverse=True)
                new_preferred = [pid for pid, _ in interested_peers[:k]]
            
            # Update choking status
            old_preferred = set(self.preferred_neighbors)
            new_preferred_set = set(new_preferred)
            
            # Choke peers no longer preferred
            for pid in old_preferred - new_preferred_set:
                if pid != self.optimistic_unchoked:
                    self._send_choke(pid)
            
            # Unchoke newly preferred peers
            for pid in new_preferred_set - old_preferred:
                self._send_unchoke(pid)
            
            self.preferred_neighbors = new_preferred
            
            if new_preferred:
                self.logger.log_preferred_neighbors(new_preferred)
                self.console.print(f"[magenta]Preferred neighbors: {new_preferred}[/magenta]")
    
    def _select_optimistic_unchoked(self):
        """Select a random choked but interested peer for optimistic unchoking"""
        with self.lock:
            # Find choked but interested peers
            candidates = [
                pid for pid, state in self.peer_states.items()
                if state.peer_interested and state.am_choking and pid not in self.preferred_neighbors
            ]
            
            if not candidates:
                return
            
            # Choke previous optimistic unchoked if it exists
            if self.optimistic_unchoked and self.optimistic_unchoked not in self.preferred_neighbors:
                self._send_choke(self.optimistic_unchoked)
            
            # Select new optimistic unchoked
            self.optimistic_unchoked = random.choice(candidates)
            self._send_unchoke(self.optimistic_unchoked)
            
            self.logger.log_optimistic_unchoked(self.optimistic_unchoked)
            self.console.print(f"[cyan]Optimistically unchoked: Peer {self.optimistic_unchoked}[/cyan]")
    
    def _update_ui(self):
        """Update the rich UI periodically"""
        while self.running:
            time.sleep(2)
            self._display_status()
    
    def _display_status(self):
        """Display current peer status"""
        status_table = Table(title=f"Peer {self.peer_id} Status", box=box.MINIMAL)
        status_table.add_column("Peer", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("Interest", style="yellow")
        status_table.add_column("Choked", style="red")
        
        for pid, state in self.peer_states.items():
            status = "Connected"
            interest = f"{'↑' if state.peer_interested else '-'} / {'↓' if state.am_interested else '-'}"
            choked = f"{'✗' if state.am_choking else '✓'} / {'✗' if state.peer_choking else '✓'}"
            status_table.add_row(str(pid), status, interest, choked)
        
        self.console.print(status_table)
    
    def _check_termination(self) -> bool:
        """Check if all peers have completed download"""
        # TODO: Implement termination detection
        return False
    
    def _remove_peer(self, peer_id: int):
        """Remove a disconnected peer"""
        with self.lock:
            if peer_id in self.connections:
                del self.connections[peer_id]
            if peer_id in self.peer_states:
                del self.peer_states[peer_id]
            if peer_id in self.preferred_neighbors:
                self.preferred_neighbors.remove(peer_id)
            if self.optimistic_unchoked == peer_id:
                self.optimistic_unchoked = None
    
    def stop(self):
        """Stop the peer"""
        self.running = False
        if self.server:
            self.server.stop()
        
        # Close all connections
        for peer_id in list(self.connections.keys()):
            try:
                self.connections[peer_id].socket.close()
            except:
                pass
        
        self.console.print(f"[bold red]Peer {self.peer_id} stopped[/bold red]")