"""
Test script for configuration parser
Purpose: Verify configuration parser works with actual config files
"""

import sys
import os

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ConfigParser, CommonConfig, PeerInfo

def test_common_config():
    """Test parsing of Common.cfg"""
    print("=" * 60)
    print("Testing Common.cfg Parser")
    print("=" * 60)
    
    parser = ConfigParser()
    
    try:
        config = parser.parse_common_config('Common.cfg')
        
        # Display parsed values
        print("\n✓ Successfully parsed Common.cfg")
        print("\nConfiguration Values:")
        print(f"  • Number of Preferred Neighbors: {config.number_of_preferred_neighbors}")
        print(f"  • Unchoking Interval: {config.unchoking_interval} seconds")
        print(f"  • Optimistic Unchoking Interval: {config.optimistic_unchoking_interval} seconds")
        print(f"  • File Name: {config.file_name}")
        print(f"  • File Size: {config.file_size:,} bytes ({config.file_size / (1024*1024):.2f} MB)")
        print(f"  • Piece Size: {config.piece_size:,} bytes ({config.piece_size / 1024:.1f} KB)")
        
        print("\nCalculated Values:")
        print(f"  • Total Number of Pieces: {config.num_pieces}")
        print(f"  • Last Piece Size: {config.last_piece_size:,} bytes")
        
        # Verify calculations
        expected_pieces = (config.file_size + config.piece_size - 1) // config.piece_size
        assert config.num_pieces == expected_pieces, "Piece calculation error"
        print("\n✓ Piece calculations verified")
        
        return True
        
    except FileNotFoundError:
        print("\n✗ Error: Common.cfg not found in current directory")
        print("  Make sure Common.cfg exists in the project root directory")
        return False
    except Exception as e:
        print(f"\n✗ Error parsing Common.cfg: {e}")
        return False

def test_peer_info():
    """Test parsing of PeerInfo.cfg"""
    print("\n" + "=" * 60)
    print("Testing PeerInfo.cfg Parser")
    print("=" * 60)
    
    parser = ConfigParser()
    
    try:
        peers = parser.parse_peer_info('PeerInfo.cfg')
        
        print(f"\n✓ Successfully parsed PeerInfo.cfg")
        print(f"  Found {len(peers)} peers\n")
        
        # Group peers by whether they have the file
        seeders = []
        leechers = []
        
        for peer_id in sorted(peers.keys()):
            peer = peers[peer_id]
            if peer.has_file:
                seeders.append(peer)
            else:
                leechers.append(peer)
        
        print(f"Seeders (peers with complete file): {len(seeders)}")
        for peer in seeders:
            print(f"  • Peer {peer.peer_id:4d} at {peer.hostname:30s} port {peer.port}")
        
        print(f"\nLeechers (peers without file): {len(leechers)}")
        for peer in leechers:
            print(f"  • Peer {peer.peer_id:4d} at {peer.hostname:30s} port {peer.port}")
        
        # Test connection logic
        print("\n" + "-" * 40)
        print("Testing Connection Logic")
        print("-" * 40)
        
        # Test for peer 1003
        test_peer_id = 1003
        peers_to_connect = parser.get_peers_to_connect(test_peer_id)
        
        print(f"\nPeer {test_peer_id} should connect to:")
        for peer in peers_to_connect:
            print(f"  → Peer {peer.peer_id} (connect to {peer.hostname}:{peer.port})")
        
        # Verify the connection logic
        expected_connections = [p for pid, p in peers.items() if pid < test_peer_id]
        assert len(peers_to_connect) == len(expected_connections), "Connection logic error"
        print(f"\n✓ Connection logic verified for peer {test_peer_id}")
        
        return True
        
    except FileNotFoundError:
        print("\n✗ Error: PeerInfo.cfg not found in current directory")
        print("  Make sure PeerInfo.cfg exists in the project root directory")
        return False
    except Exception as e:
        print(f"\n✗ Error parsing PeerInfo.cfg: {e}")
        return False

def test_integration():
    """Test integration of both config files"""
    print("\n" + "=" * 60)
    print("Integration Test")
    print("=" * 60)
    
    parser = ConfigParser()
    
    try:
        # Parse both files
        common = parser.parse_common_config('Common.cfg')
        peers = parser.parse_peer_info('PeerInfo.cfg')
        
        print("\n✓ Both configuration files parsed successfully")
        
        # Simulate startup sequence
        print("\nSimulating Peer Startup Sequence:")
        print("-" * 40)
        
        for peer_id in sorted(peers.keys()):
            peer_info = peers[peer_id]
            connections = parser.get_peers_to_connect(peer_id)
            
            print(f"\nPeer {peer_id} starts:")
            print(f"  • Listens on port {peer_info.port}")
            
            if peer_info.has_file:
                print(f"  • Has complete file '{common.file_name}' ({common.file_size:,} bytes)")
            else:
                print(f"  • Needs to download '{common.file_name}'")
            
            if connections:
                print(f"  • Connects to {len(connections)} peer(s): {[p.peer_id for p in connections]}")
            else:
                print(f"  • First peer - waits for incoming connections")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\nP2P BitTorrent Configuration Parser Test Suite")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 3
    
    # Run tests
    if test_common_config():
        tests_passed += 1
    
    if test_peer_info():
        tests_passed += 1
    
    if test_integration():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Passed: {tests_passed}/{tests_total} tests")
    
    if tests_passed == tests_total:
        print("✓ All tests passed! Configuration parser is working correctly.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())