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
from peer import Peer

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
    
    # Setup logging for this peer (but suppress console output since we use rich)
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
        
        logger.info(f"Configuration loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Initialize and start the peer
    peer = None
    try:
        peer = Peer(peer_id, common_config, all_peers)
        
        # Setup graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Shutting down peer process...")
            if peer:
                peer.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start the peer (this will block until complete)
        peer.start()
        
    except Exception as e:
        logger.error(f"Peer process failed: {e}")
        if peer:
            peer.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()