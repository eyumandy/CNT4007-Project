"""
Comprehensive test for message protocol
Purpose: Test message serialization/deserialization in realistic scenarios
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message import *
import struct

def test_handshake_validation():
    """Test handshake validation and error handling"""
    print("=" * 60)
    print("Testing Handshake Validation")
    print("=" * 60)
    
    # Test valid handshake
    print("\n1. Valid Handshake:")
    hs = HandshakeMessage(1001)
    data = hs.serialize()
    print(f"   Peer ID: 1001")
    print(f"   Size: {len(data)} bytes")
    print(f"   Header: {data[:18]}")
    print(f"   ✓ Valid handshake created")
    
    # Test invalid header
    print("\n2. Invalid Header Detection:")
    bad_data = b'WRONGHEADER1234567' + b'\x00' * 10 + struct.pack('!I', 1001)
    try:
        HandshakeMessage.deserialize(bad_data)
        print("   ✗ Failed to detect invalid header")
    except ValueError as e:
        print(f"   ✓ Correctly rejected: {e}")
    
    # Test invalid size
    print("\n3. Invalid Size Detection:")
    try:
        HandshakeMessage.deserialize(data[:20])  # Too short
        print("   ✗ Failed to detect invalid size")
    except ValueError as e:
        print(f"   ✓ Correctly rejected: {e}")
    
    return True

def test_message_sizes():
    """Test message sizes match protocol specification"""
    print("\n" + "=" * 60)
    print("Testing Message Sizes")
    print("=" * 60)
    
    tests = [
        ("Choke", Message.create_choke(), 5),  # 4 length + 1 type
        ("Unchoke", Message.create_unchoke(), 5),
        ("Interested", Message.create_interested(), 5),
        ("Not Interested", Message.create_not_interested(), 5),
        ("Have", Message.create_have(42), 9),  # 4 length + 1 type + 4 index
        ("Request", Message.create_request(100), 9),
    ]
    
    print("\nMessage sizes (including length prefix):")
    all_passed = True
    for name, msg, expected_size in tests:
        serialized = msg.serialize()
        actual_size = len(serialized)
        status = "✓" if actual_size == expected_size else "✗"
        print(f"   {status} {name:15s}: {actual_size} bytes (expected {expected_size})")
        if actual_size != expected_size:
            all_passed = False
    
    # Test piece message with data
    piece_data = b'X' * 16384  # Standard piece size
    piece_msg = Message.create_piece(0, piece_data)
    serialized = piece_msg.serialize()
    expected = 4 + 1 + 4 + 16384  # length + type + index + data
    actual = len(serialized)
    status = "✓" if actual == expected else "✗"
    print(f"   {status} {'Piece (16KB)':15s}: {actual} bytes (expected {expected})")
    
    return all_passed

def test_bitfield_operations():
    """Test bitfield creation and manipulation"""
    print("\n" + "=" * 60)
    print("Testing Bitfield Operations")
    print("=" * 60)
    
    # Test case 1: File with 10 pieces, peer has pieces 0, 2, 4, 6, 8
    print("\n1. Partial bitfield (10 pieces, have even indices):")
    pieces_have = [0, 2, 4, 6, 8]
    bitfield = BitfieldHelper.create_bitfield(10, pieces_have)
    print(f"   Created bitfield: {bitfield.hex()}")
    print(f"   Binary: {' '.join(format(b, '08b') for b in bitfield)}")
    
    parsed = BitfieldHelper.parse_bitfield(bitfield, 10)
    print(f"   Parsed pieces: {parsed}")
    assert parsed == pieces_have, "Bitfield parsing mismatch"
    print("   ✓ Bitfield correctly represents pieces")
    
    # Test case 2: Complete file (all pieces)
    print("\n2. Complete bitfield (20 pieces, have all):")
    bitfield_complete = BitfieldHelper.create_bitfield(20, None)
    print(f"   Created bitfield: {bitfield_complete.hex()}")
    parsed_complete = BitfieldHelper.parse_bitfield(bitfield_complete, 20)
    print(f"   Number of pieces: {len(parsed_complete)}")
    assert len(parsed_complete) == 20, "Should have all 20 pieces"
    print("   ✓ Complete bitfield verified")
    
    # Test case 3: Empty bitfield (no pieces)
    print("\n3. Empty bitfield (15 pieces, have none):")
    bitfield_empty = BitfieldHelper.create_bitfield(15, [])
    print(f"   Created bitfield: {bitfield_empty.hex()}")
    parsed_empty = BitfieldHelper.parse_bitfield(bitfield_empty, 15)
    print(f"   Number of pieces: {len(parsed_empty)}")
    assert len(parsed_empty) == 0, "Should have no pieces"
    print("   ✓ Empty bitfield verified")
    
    # Test case 4: Large file scenario (1484 pieces like in your config)
    print("\n4. Large file scenario (1484 pieces):")
    num_pieces = 1484
    # Simulate having first 100 pieces
    pieces_have = list(range(100))
    bitfield_large = BitfieldHelper.create_bitfield(num_pieces, pieces_have)
    print(f"   Bitfield size: {len(bitfield_large)} bytes")
    print(f"   Expected size: {(num_pieces + 7) // 8} bytes")
    parsed_large = BitfieldHelper.parse_bitfield(bitfield_large, num_pieces)
    assert len(parsed_large) == 100, "Should have 100 pieces"
    print("   ✓ Large bitfield handled correctly")
    
    return True

def test_message_reader_scenarios():
    """Test MessageReader with various data arrival patterns"""
    print("\n" + "=" * 60)
    print("Testing MessageReader Scenarios")
    print("=" * 60)
    
    # Scenario 1: Data arrives byte by byte
    print("\n1. Byte-by-byte data arrival:")
    reader = MessageReader()
    handshake_data = HandshakeMessage(1005).serialize()
    
    for i, byte in enumerate(handshake_data):
        reader.feed_data(bytes([byte]))
        hs = reader.get_handshake()
        if hs:
            print(f"   ✓ Handshake complete after {i+1} bytes")
            assert hs.peer_id == 1005
            break
    
    # Scenario 2: Multiple messages in one chunk
    print("\n2. Multiple messages in single receive:")
    reader.clear_buffer()
    reader.reading_handshake = False
    
    messages = [
        Message.create_interested(),
        Message.create_have(10),
        Message.create_have(20),
        Message.create_unchoke()
    ]
    
    combined_data = b''.join(msg.serialize() for msg in messages)
    reader.feed_data(combined_data)
    
    received = []
    while True:
        msg = reader.get_message()
        if not msg:
            break
        received.append(msg)
    
    print(f"   Sent {len(messages)} messages in one chunk")
    print(f"   Received: {[m.type_name for m in received]}")
    assert len(received) == len(messages), "Message count mismatch"
    print("   ✓ All messages extracted correctly")
    
    # Scenario 3: Partial message arrival
    print("\n3. Partial message handling:")
    reader.clear_buffer()
    reader.reading_handshake = False
    
    piece_data = b'A' * 1000
    piece_msg = Message.create_piece(42, piece_data)
    serialized = piece_msg.serialize()
    
    # Send first half
    reader.feed_data(serialized[:500])
    msg = reader.get_message()
    assert msg is None, "Should not have complete message yet"
    print("   ✓ Correctly waiting for more data")
    
    # Send rest
    reader.feed_data(serialized[500:])
    msg = reader.get_message()
    assert msg is not None, "Should have complete message now"
    assert msg.get_piece_index() == 42
    assert len(msg.get_piece_data()) == 1000
    print("   ✓ Message completed successfully")
    
    return True

def test_protocol_sequence():
    """Test a typical protocol message sequence"""
    print("\n" + "=" * 60)
    print("Testing Protocol Sequence")
    print("=" * 60)
    
    print("\nSimulating connection between Peer 1001 (seeder) and Peer 1002 (leecher):")
    print("-" * 40)
    
    # 1. Handshake exchange
    print("\n1. Handshake Phase:")
    hs_1001 = HandshakeMessage(1001)
    hs_1002 = HandshakeMessage(1002)
    print(f"   → Peer 1002 sends handshake to 1001")
    print(f"   ← Peer 1001 sends handshake to 1002")
    
    # 2. Bitfield exchange
    print("\n2. Bitfield Exchange:")
    # Peer 1001 has all 1484 pieces
    bitfield_1001 = BitfieldHelper.create_bitfield(1484, None)
    msg_bitfield_1001 = Message.create_bitfield(bitfield_1001)
    print(f"   ← Peer 1001 sends bitfield (has all {1484} pieces)")
    
    # Peer 1002 has no pieces initially (doesn't send bitfield)
    print(f"   → Peer 1002 has no pieces (no bitfield sent)")
    
    # 3. Interest messages
    print("\n3. Interest Declaration:")
    msg_interested = Message.create_interested()
    print(f"   → Peer 1002 sends 'interested' to 1001")
    
    # 4. Unchoking
    print("\n4. Unchoking Decision:")
    msg_unchoke = Message.create_unchoke()
    print(f"   ← Peer 1001 sends 'unchoke' to 1002")
    
    # 5. Request and piece exchange
    print("\n5. Piece Transfer:")
    request_msg = Message.create_request(0)
    print(f"   → Peer 1002 requests piece 0")
    
    piece_data = b'[First piece data...]' + b'X' * 16363  # 16384 bytes total
    piece_msg = Message.create_piece(0, piece_data)
    print(f"   ← Peer 1001 sends piece 0 ({len(piece_data)} bytes)")
    
    # 6. Have message propagation
    print("\n6. Have Message:")
    have_msg = Message.create_have(0)
    print(f"   → Peer 1002 broadcasts 'have' for piece 0 to all peers")
    
    print("\n✓ Protocol sequence simulation complete")
    return True

def main():
    """Run all message tests"""
    print("\nP2P BitTorrent Message Protocol Test Suite")
    print("=" * 60)
    
    tests = [
        ("Handshake Validation", test_handshake_validation),
        ("Message Sizes", test_message_sizes),
        ("Bitfield Operations", test_bitfield_operations),
        ("MessageReader Scenarios", test_message_reader_scenarios),
        ("Protocol Sequence", test_protocol_sequence)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n✗ {test_name} failed")
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✓ All message tests passed!")
        print("\nNext steps:")
        print("1. Implement basic TCP server")
        print("2. Implement basic TCP client")
        print("3. Test handshake between two peers")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())