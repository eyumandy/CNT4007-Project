"""
Test actual file piece transfer between peers
This demonstrates the complete file exchange functionality
"""

import sys
import os
import time
import subprocess
import signal

def test_file_transfer():
    """
    Test file transfer between peers
    """
    print("\n" + "="*60)
    print("P2P BitTorrent File Transfer Test")
    print("="*60)
    print("\nThis test will demonstrate:")
    print("1. Peer 1001 (seeder) has tree.jpg")
    print("2. Peer 1002 (leecher) starts with empty directory")
    print("3. Peer 1002 downloads pieces from 1001")
    print("4. Progress tracking and file reconstruction")
    print("\nNOTE: Actual transfer will happen when peers unchoke each other")
    print("="*60)
    
    # Check initial state
    print("\nInitial State:")
    print("-" * 40)
    
    # Look in parent directory for peer folders
    parent_dir = os.path.dirname(os.getcwd())
    peer_1001_file = os.path.join(parent_dir, "peer_1001", "tree.jpg")
    peer_1002_file = os.path.join(parent_dir, "peer_1002", "tree.jpg")
    peer_1002_dir = os.path.join(parent_dir, "peer_1002")
    
    if os.path.exists(peer_1001_file):
        size = os.path.getsize(peer_1001_file)
        print(f"✓ peer_1001/tree.jpg exists ({size:,} bytes)")
    else:
        print(f"✗ peer_1001/tree.jpg missing!")
        print(f"  Looking for: {peer_1001_file}")
        print(f"  Current dir: {os.getcwd()}")
        print("\n  Make sure to run this from the project root directory,")
        print("  or copy this script to the main project folder.")
        return
    
    if not os.path.exists(peer_1002_file):
        print("✓ peer_1002/ is empty (ready to download)")
        # Make sure peer_1002 directory exists
        os.makedirs(peer_1002_dir, exist_ok=True)
    else:
        print("✗ peer_1002/ already has file (removing...)")
        os.remove(peer_1002_file)
    
    print("\n" + "="*60)
    input("Press Enter to start the test...")
    
    processes = []
    
    try:
        # Start Peer 1001
        print("\n[1] Starting Peer 1001 (seeder)...")
        p1 = subprocess.Popen(
            [sys.executable, "peerProcess.py", "1001"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        processes.append(p1)
        time.sleep(2)
        
        # Start Peer 1002
        print("[2] Starting Peer 1002 (leecher)...")
        p2 = subprocess.Popen(
            [sys.executable, "peerProcess.py", "1002"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        processes.append(p2)
        
        print("\n" + "="*60)
        print("Peers are running!")
        print("\nWhat's happening:")
        print("- Peer 1002 connects to 1001")
        print("- Exchanges bitfields")
        print("- 1002 sends 'interested' to 1001")
        print("- After unchoking (5-10 seconds):")
        print("  - 1002 requests pieces")
        print("  - 1001 sends pieces")
        print("  - Progress shown in console")
        print("\nWait 15-20 seconds for transfer...")
        print("="*60)
        
        # Let it run for a bit
        time.sleep(20)
        
        # Check if file was created
        print("\n" + "="*60)
        print("Checking Results:")
        print("-" * 40)
        
        # Use parent directory paths
        if os.path.exists(peer_1002_file):
            size = os.path.getsize(peer_1002_file)
            expected = 24301474
            if size == expected:
                print(f"✓ SUCCESS! peer_1002/tree.jpg created ({size:,} bytes)")
                print("✓ File transfer WORKING!")
            else:
                print(f"⚠ File created but wrong size: {size} != {expected}")
        else:
            # Check for temp pieces
            temp_dir = os.path.join(parent_dir, "peer_1002", "temp_pieces")
            if os.path.exists(temp_dir):
                pieces = len([f for f in os.listdir(temp_dir) if f.endswith('.tmp')])
                print(f"⚠ Transfer in progress: {pieces} pieces downloaded")
                print("  (Need more time for complete transfer)")
            else:
                print("✗ No file transfer occurred")
                print("  (Peers may need to unchoke first)")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    finally:
        print("\nStopping peers...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        
        print("Peers stopped")

if __name__ == "__main__":
    test_file_transfer()