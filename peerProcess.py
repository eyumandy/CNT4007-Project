#!/usr/bin/env python3
"""
Main entry point for P2P BitTorrent Peer Process
Purpose: Initialize and run a peer process with given peer ID
Usage: python peerProcess.py <peer_id>
"""

import sys
import os
import signal
import logging
from config import ConfigParser
from logger import setup_logger

def main():
    """
    Main function to start peer process
    Expected usage: python peerProcess.py 1001
    """
    # Validate command line arguments
    if len(sys.argv) != 2:
        print("Usage: python peerProcess.py <peer_id>")
        sys.exit(1)
    
    try:
        peer_id = int(sys.argv[1])
    except ValueError:
        print("Error: peer_id must be an integer")
        sys.exit(1)
    
    # Setup logging for this peer
    logger = setup_logger(peer_id)
    logger.info(f"Starting peer process with ID: {peer_id}")
    
    # Load configuration files
    try:
        config_parser = ConfigParser()
        common_config = config_parser.parse_common_config('Common.cfg')
        all_peers = config_parser.parse_peer_info('PeerInfo.cfg')
        
        # Validate peer_id exists in PeerInfo.cfg
        if peer_id not in all_peers:
            logger.error(f"Peer ID {peer_id} not found in PeerInfo.cfg")
            sys.exit(1)
        
        # Get this peer's info and peers to connect to
        my_peer_info = config_parser.get_my_info(peer_id)
        peers_to_connect = config_parser.get_peers_to_connect(peer_id)
        
        logger.info(f"Configuration loaded successfully")
        logger.info(f"File: {common_config.file_name} ({common_config.file_size:,} bytes)")
        logger.info(f"Pieces: {common_config.num_pieces} x {common_config.piece_size} bytes")
        logger.info(f"This peer: {my_peer_info}")
        logger.info(f"Will connect to {len(peers_to_connect)} peer(s): {[p.peer_id for p in peers_to_connect]}")
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Create peer directory if it doesn't exist
    peer_dir = f"peer_{peer_id}"
    if not os.path.exists(peer_dir):
        os.makedirs(peer_dir)
        logger.info(f"Created directory: {peer_dir}")
    
    # TODO: Phase 2 - Initialize Peer object
    # TODO: Phase 3 - Start server thread
    # TODO: Phase 4 - Connect to previous peers
    # TODO: Phase 5 - Start message handling
    # TODO: Phase 6 - Start scheduling threads
    
    logger.info("Peer process initialization complete")
    
    # Setup graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutting down peer process...")
        # TODO: Cleanup connections and threads
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep process running (will be replaced with actual event loop)
    logger.info("Peer process running. Press Ctrl+C to stop.")
    try:
        signal.pause()  # Unix/Linux
    except AttributeError:
        # Windows doesn't have signal.pause()
        import time
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main()