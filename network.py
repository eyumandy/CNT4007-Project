"""
Network layer for P2P BitTorrent Implementation
Purpose: Handle TCP server, client connections, and peer communication
Dependencies: message.py, logger.py, constants.py
"""

import socket
import threading
import time
import struct
from typing import Dict, Optional, Tuple, Callable
from dataclasses import dataclass
from queue import Queue, Empty
import select

from message import HandshakeMessage, Message, MessageReader, BitfieldHelper
from logger import PeerLogger
from constants import *

@dataclass
class PeerConnection:
    """
    Represents a connection to a peer
    
    Attributes:
        peer_id (int): ID of the connected peer
        socket (socket.socket): Socket object for this connection
        address (tuple): (hostname, port) of the peer
        is_choked (bool): Whether we are choked by this peer
        is_interested (bool): Whether we are interested in this peer
        peer_choking (bool): Whether this peer is choked by us
        peer_interested (bool): Whether this peer is interested in us
        bitfield (bytearray): Bitfield of pieces this peer has
        download_rate (float): Download rate from this peer (bytes/sec)
        upload_rate (float): Upload rate to this peer (bytes/sec)
        last_message_time (float): Timestamp of last message received
        message_reader (MessageReader): Helper to read messages from stream
        send_queue (Queue): Queue of messages to send to this peer
    """
    peer_id: int
    socket: socket.socket
    address: Tuple[str, int]
    is_choked: bool = True
    is_interested: bool = False
    peer_choking: bool = True
    peer_interested: bool = False
    bitfield: Optional[bytearray] = None
    download_rate: float = 0.0
    upload_rate: float = 0.0
    last_message_time: float = 0.0
    message_reader: MessageReader = None
    send_queue: Queue = None
    
    def __post_init__(self):
        """Initialize message reader and send queue"""
        if self.message_reader is None:
            self.message_reader = MessageReader()
        if self.send_queue is None:
            self.send_queue = Queue()
        self.last_message_time = time.time()


class P2PServer(threading.Thread):
    """
    TCP Server that listens for incoming peer connections
    Runs in a separate thread
    """
    
    def __init__(self, peer_id: int, hostname: str, port: int, 
                 connection_handler: Callable, logger: PeerLogger):
        """
        Initialize the P2P server
        
        Args:
            peer_id (int): ID of this peer
            hostname (str): Hostname/IP to bind to
            port (int): Port to listen on
            connection_handler (Callable): Function to handle new connections
            logger (PeerLogger): Logger instance
        """
        super().__init__(daemon=True)
        self.peer_id = peer_id
        self.hostname = hostname
        self.port = port
        self.connection_handler = connection_handler
        self.logger = logger
        self.server_socket = None
        self.running = False
        self.connections = {}  # peer_id -> PeerConnection
        
    def run(self):
        """Main server loop - accepts incoming connections"""
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to address and port
            # For testing on localhost, use '0.0.0.0' or 'localhost'
            bind_address = '0.0.0.0'  # Listen on all interfaces
            self.server_socket.bind((bind_address, self.port))
            self.server_socket.listen(10)  # Allow up to 10 pending connections
            
            self.logger.info(f"Server listening on {bind_address}:{self.port}")
            self.running = True
            
            while self.running:
                try:
                    # Set timeout for accept() so we can check self.running periodically
                    self.server_socket.settimeout(1.0)
                    client_socket, client_address = self.server_socket.accept()
                    
                    self.logger.debug(f"Incoming connection from {client_address}")
                    
                    # Handle new connection in separate thread
                    handler_thread = threading.Thread(
                        target=self._handle_incoming_connection,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    handler_thread.start()
                    
                except socket.timeout:
                    # Timeout is normal - just check if we should stop
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error accepting connection: {e}")
                    
        except Exception as e:
            self.logger.error(f"Server failed to start: {e}")
        finally:
            self.stop()
    
    def _handle_incoming_connection(self, client_socket: socket.socket, 
                                   client_address: Tuple[str, int]):
        """
        Handle an incoming connection - perform handshake
        
        Args:
            client_socket (socket.socket): Socket for the new connection
            client_address (tuple): Address of the connecting peer
        """
        try:
            # Set socket timeout for handshake
            client_socket.settimeout(HANDSHAKE_TIMEOUT)
            
            # Receive handshake
            handshake_data = client_socket.recv(HANDSHAKE_MSG_LEN)
            if len(handshake_data) != HANDSHAKE_MSG_LEN:
                self.logger.warning(f"Invalid handshake size from {client_address}")
                client_socket.close()
                return
            
            # Parse handshake
            try:
                incoming_handshake = HandshakeMessage.deserialize(handshake_data)
                remote_peer_id = incoming_handshake.peer_id
                self.logger.debug(f"Received handshake from peer {remote_peer_id}")
            except ValueError as e:
                self.logger.warning(f"Invalid handshake from {client_address}: {e}")
                client_socket.close()
                return
            
            # Send our handshake
            our_handshake = HandshakeMessage(self.peer_id)
            client_socket.send(our_handshake.serialize())
            
            # Log successful connection
            self.logger.log_tcp_connection_received(remote_peer_id)
            
            # Create PeerConnection object
            peer_conn = PeerConnection(
                peer_id=remote_peer_id,
                socket=client_socket,
                address=client_address
            )
            
            # Store connection
            self.connections[remote_peer_id] = peer_conn
            
            # Call the connection handler (implemented in main peer process)
            if self.connection_handler:
                self.connection_handler(peer_conn, is_incoming=True)
            
        except socket.timeout:
            self.logger.warning(f"Handshake timeout from {client_address}")
            client_socket.close()
        except Exception as e:
            self.logger.error(f"Error handling incoming connection: {e}")
            client_socket.close()
    
    def stop(self):
        """Stop the server and close all connections"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.logger.info("Server stopped")


class P2PClient:
    """
    TCP Client for connecting to other peers
    """
    
    def __init__(self, peer_id: int, logger: PeerLogger):
        """
        Initialize the P2P client
        
        Args:
            peer_id (int): ID of this peer
            logger (PeerLogger): Logger instance
        """
        self.peer_id = peer_id
        self.logger = logger
        self.connections = {}  # peer_id -> PeerConnection
    
    def connect_to_peer(self, remote_peer_id: int, hostname: str, port: int,
                       connection_handler: Callable = None) -> Optional[PeerConnection]:
        """
        Connect to another peer and perform handshake
        
        Args:
            remote_peer_id (int): ID of peer to connect to
            hostname (str): Hostname/IP of peer
            port (int): Port of peer
            connection_handler (Callable): Optional handler for established connection
            
        Returns:
            PeerConnection: Connection object if successful, None otherwise
        """
        try:
            # Create socket and connect
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(CONNECTION_TIMEOUT)
            
            self.logger.debug(f"Connecting to peer {remote_peer_id} at {hostname}:{port}")
            
            # For localhost testing, replace hostname if needed
            if hostname.startswith("lin114"):
                hostname = "localhost"
            
            peer_socket.connect((hostname, port))
            
            # Send handshake
            our_handshake = HandshakeMessage(self.peer_id)
            peer_socket.send(our_handshake.serialize())
            
            # Receive handshake
            handshake_data = peer_socket.recv(HANDSHAKE_MSG_LEN)
            if len(handshake_data) != HANDSHAKE_MSG_LEN:
                self.logger.warning(f"Invalid handshake size from peer {remote_peer_id}")
                peer_socket.close()
                return None
            
            # Parse and validate handshake
            incoming_handshake = HandshakeMessage.deserialize(handshake_data)
            if incoming_handshake.peer_id != remote_peer_id:
                self.logger.warning(
                    f"Peer ID mismatch: expected {remote_peer_id}, got {incoming_handshake.peer_id}"
                )
                peer_socket.close()
                return None
            
            # Log successful connection
            self.logger.log_tcp_connection_made(remote_peer_id)
            
            # Create PeerConnection object
            peer_conn = PeerConnection(
                peer_id=remote_peer_id,
                socket=peer_socket,
                address=(hostname, port)
            )
            
            # Store connection
            self.connections[remote_peer_id] = peer_conn
            
            # Call connection handler if provided
            if connection_handler:
                connection_handler(peer_conn, is_incoming=False)
            
            return peer_conn
            
        except socket.timeout:
            self.logger.warning(f"Connection timeout to peer {remote_peer_id}")
            return None
        except ConnectionRefusedError:
            self.logger.debug(f"Connection refused by peer {remote_peer_id} (may not be started yet)")
            return None
        except Exception as e:
            self.logger.error(f"Error connecting to peer {remote_peer_id}: {e}")
            return None
    
    def connect_to_peers(self, peer_list: list, connection_handler: Callable = None) -> Dict[int, PeerConnection]:
        """
        Connect to multiple peers
        
        Args:
            peer_list (list): List of PeerInfo objects to connect to
            connection_handler (Callable): Optional handler for each connection
            
        Returns:
            dict: Dictionary of peer_id -> PeerConnection for successful connections
        """
        successful_connections = {}
        
        for peer_info in peer_list:
            conn = self.connect_to_peer(
                peer_info.peer_id,
                peer_info.hostname,
                peer_info.port,
                connection_handler
            )
            if conn:
                successful_connections[peer_info.peer_id] = conn
            else:
                # Retry logic could be added here
                self.logger.debug(f"Failed to connect to peer {peer_info.peer_id}")
        
        self.logger.info(f"Connected to {len(successful_connections)}/{len(peer_list)} peers")
        return successful_connections


class ConnectionManager:
    """
    Manages all peer connections for message handling
    """
    
    def __init__(self, peer_id: int, logger: PeerLogger):
        """
        Initialize connection manager
        
        Args:
            peer_id (int): ID of this peer
            logger (PeerLogger): Logger instance
        """
        self.peer_id = peer_id
        self.logger = logger
        self.connections = {}  # peer_id -> PeerConnection
        self.connection_threads = {}  # peer_id -> threading.Thread
        self.running = False
    
    def add_connection(self, peer_conn: PeerConnection):
        """
        Add a new peer connection and start handling it
        
        Args:
            peer_conn (PeerConnection): Connection to add
        """
        peer_id = peer_conn.peer_id
        self.connections[peer_id] = peer_conn
        
        # Start message handler thread for this connection
        handler_thread = threading.Thread(
            target=self._handle_peer_messages,
            args=(peer_conn,),
            daemon=True
        )
        handler_thread.start()
        self.connection_threads[peer_id] = handler_thread
        
        # Start sender thread for this connection
        sender_thread = threading.Thread(
            target=self._handle_peer_sending,
            args=(peer_conn,),
            daemon=True
        )
        sender_thread.start()
    
    def _handle_peer_messages(self, peer_conn: PeerConnection):
        """
        Handle incoming messages from a peer
        
        Args:
            peer_conn (PeerConnection): Connection to handle
        """
        peer_id = peer_conn.peer_id
        self.logger.debug(f"Starting message handler for peer {peer_id}")
        
        try:
            while peer_id in self.connections:
                # Try to receive data
                try:
                    peer_conn.socket.settimeout(1.0)
                    data = peer_conn.socket.recv(DEFAULT_BUFFER_SIZE)
                    
                    if not data:
                        # Connection closed by peer
                        self.logger.info(f"Peer {peer_id} closed connection")
                        break
                    
                    # Feed data to message reader
                    peer_conn.message_reader.feed_data(data)
                    
                    # Process any complete messages
                    while True:
                        msg = peer_conn.message_reader.get_message()
                        if msg is None:
                            break
                        
                        # Update last message time
                        peer_conn.last_message_time = time.time()
                        
                        # Handle the message (this would be implemented in peer.py)
                        self._process_message(peer_conn, msg)
                        
                except socket.timeout:
                    # Check if connection is still alive
                    if time.time() - peer_conn.last_message_time > CONNECTION_TIMEOUT:
                        self.logger.warning(f"Peer {peer_id} timed out")
                        break
                except Exception as e:
                    self.logger.error(f"Error receiving from peer {peer_id}: {e}")
                    break
        
        finally:
            # Clean up connection
            self.remove_connection(peer_id)
    
    def _handle_peer_sending(self, peer_conn: PeerConnection):
        """
        Handle sending messages to a peer
        
        Args:
            peer_conn (PeerConnection): Connection to handle
        """
        peer_id = peer_conn.peer_id
        
        while peer_id in self.connections:
            try:
                # Get message from send queue (timeout allows checking if connection still exists)
                msg = peer_conn.send_queue.get(timeout=1.0)
                
                # Send the message
                peer_conn.socket.send(msg)
                
            except Empty:
                # No messages to send, continue
                continue
            except Exception as e:
                self.logger.error(f"Error sending to peer {peer_id}: {e}")
                break
    
    def _process_message(self, peer_conn: PeerConnection, msg: Message):
        """
        Process a received message (placeholder - actual implementation in peer.py)
        
        Args:
            peer_conn (PeerConnection): Connection that received the message
            msg (Message): Message to process
        """
        # Log the message type
        self.logger.debug(f"Received {msg.type_name} from peer {peer_conn.peer_id}")
        
        # This is where message processing would happen
        # Will be implemented when we create peer.py
        pass
    
    def send_message(self, peer_id: int, message: Message):
        """
        Send a message to a specific peer
        
        Args:
            peer_id (int): ID of peer to send to
            message (Message): Message to send
        """
        if peer_id in self.connections:
            serialized = message.serialize()
            self.connections[peer_id].send_queue.put(serialized)
        else:
            self.logger.warning(f"Cannot send message to disconnected peer {peer_id}")
    
    def broadcast_message(self, message: Message, exclude_peer: int = None):
        """
        Send a message to all connected peers
        
        Args:
            message (Message): Message to broadcast
            exclude_peer (int): Optional peer ID to exclude from broadcast
        """
        serialized = message.serialize()
        for peer_id, conn in self.connections.items():
            if peer_id != exclude_peer:
                conn.send_queue.put(serialized)
    
    def remove_connection(self, peer_id: int):
        """
        Remove a peer connection
        
        Args:
            peer_id (int): ID of peer to disconnect
        """
        if peer_id in self.connections:
            try:
                self.connections[peer_id].socket.close()
            except:
                pass
            del self.connections[peer_id]
            self.logger.debug(f"Removed connection to peer {peer_id}")
    
    def stop_all(self):
        """Stop all connections and threads"""
        self.running = False
        peer_ids = list(self.connections.keys())
        for peer_id in peer_ids:
            self.remove_connection(peer_id)
        self.logger.info("Connection manager stopped")
