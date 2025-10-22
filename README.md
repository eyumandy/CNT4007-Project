# P2P BitTorrent Implementation - Midpoint Submission
Yumandy Espinosa
Ethan Durand
Sebastian Sosa

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     peerProcess.py                           │
│                    (Main Entry Point)                        │
│  • Parses command line args (peer ID)                       │
│  • Loads configurations                                      │
│  • Creates peer directory                                    │
│  • [TODO] Orchestrates all components                       │
└──────────────┬───────────────────────────────────────────────┘
               │
               ├──────────────┬──────────────┬──────────────┐
               ▼              ▼              ▼              ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   config.py      │ │  network.py  │ │  message.py  │ │  logger.py   │
├──────────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
│ • CommonConfig   │ │ • P2PServer  │ │ • Handshake  │ │ • PeerLogger │
│   - File info    │ │   - Listen   │ │   - 32 bytes │ │   - Events   │
│   - Piece size   │ │   - Accept   │ │              │ │   - Files    │
│   - Intervals    │ │              │ │ • Messages   │ │   - Format   │
│                  │ │ • P2PClient  │ │   - 8 types  │ └──────────────┘
│ • PeerInfo       │ │   - Connect  │ │   - Serialize│
│   - ID/Host/Port │ │   - Retry    │ │              │ ┌──────────────┐
│   - Has file?    │ │              │ │ • Bitfield   │ │ constants.py │
│                  │ │ • Connection │ │   - Pieces   │ ├──────────────┤
│ • ConfigParser   │ │   Manager    │ │   - Helper   │ │ • Protocol   │
│   - Parse files  │ │   - Queues   │ │              │ │   constants  │
│   - Get peers    │ │   - Threads  │ │ • Reader     │ │ • Timeouts   │
└──────────────────┘ └──────────────┘ │   - Buffer   │ │ • Sizes      │
                                       └──────────────┘ └──────────────┘
```

---

## 📁 Project Structure

```
CNT4007_Project/
├── peerProcess.py      # Main entry point (96 lines)
├── config.py           # Configuration file parser (310 lines)
├── message.py          # Protocol message handling (451 lines)
├── network.py          # TCP networking layer (532 lines)
├── logger.py           # Logging functionality (128 lines)
├── constants.py        # Protocol constants (46 lines)
├── Common.cfg          # Common configuration file
├── PeerInfo.cfg        # Peer network information
├── peer_XXXX/          # Peer-specific directories (created at runtime)
└── test/               # Test suite
    ├── test_config.py
    ├── test_messages.py
    ├── test_peer_process.py
    └── test_handshake.py
```

---

## Quick Start Instructions
### Basic Usage

1. **Start a single peer:**
```bash
python peerProcess.py <peer_id>

# Example:
python peerProcess.py 1001
```

2. **Run tests to verify functionality:**
```bash
# Test configuration parsing
python test/test_config.py

# Test message protocol
python test/test_messages.py

# Test network handshake
python test/test_handshake.py

# Test peer process initialization
python test/test_peer_process.py
```

## ✅ Implemented Features (Midpoint)

### Phase 1 Components (Complete)

1. **Configuration Management** (`config.py`)
   - Parses Common.cfg and PeerInfo.cfg
   - Calculates piece counts and sizes
   - Determines peer connection topology

2. **Message Protocol** (`message.py`)
   - All 8 BitTorrent message types implemented
   - Handshake protocol (32-byte format)
   - Bitfield management for piece tracking
   - Message serialization/deserialization

3. **Network Layer** (`network.py`)
   - TCP server for accepting connections
   - TCP client for initiating connections
   - Automatic handshake exchange
   - Connection management with threading

4. **Logging System** (`logger.py`)
   - Per-peer log files
   - Protocol-compliant event logging
   - All required log message formats

5. **Testing Suite** (`test/` directory)
   - 17 comprehensive tests
   - All tests passing
   - Covers config, messages, network, and processes

---

## 🔄 Current Implementation Status

### Working Features ✅
- Configuration file parsing
- TCP connection establishment
- Handshake protocol between peers
- Message serialization/deserialization
- Multi-threaded connection handling
- Comprehensive logging
- Peer directory creation

### TODO Features (Phase 2) ❌
- File piece management
- Actual file transfer
- Choking/unchoking algorithm
- Piece selection strategy
- Download/upload rate calculation
- Termination detection
- Complete peer orchestration
