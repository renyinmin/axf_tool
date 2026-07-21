# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Windows desktop tool for parsing AXF/ELF firmware files and reading/writing embedded device memory over Modbus. Supports both serial (Modbus RTU) and WebSocket (cloud relay) transports. Built with Python 3.13 and tkinter.

## Build & Run Commands

```bash
# Install dependencies (project uses a .venv virtualenv)
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# Run the GUI (run.bat does this via the .venv interpreter)
.venv\Scripts\python.exe main.py

# CLI: list all global variables in an AXF file
python main.py parse <file.axf> --list

# CLI: search for a specific variable
python main.py parse <file.axf> --search <variable_name>

# CLI: read memory via Modbus serial
python main.py read --port COM3 --address 0x20000000

# Build standalone Windows EXE (entry point is main_simple.py, NOT main.py)
pyinstaller ModbusAXFTool.spec
```

No test suite exists — testing is done manually against real hardware or WebSocket servers.

## Architecture

There are **two separate apps** in this repo; the main app is the tkinter one, and `modbus_tool/` is an older/alternative PyQt5-based tool.

### Main App — Data Flow

```
run.bat → main.py           ← normal launch (uses .venv\Scripts\python.exe)
PyInstaller spec → main_simple.py  ← EXE entry point (deferred pymodbus import)
Both call gui_fixed.main()  ← tkinter GUI, ~820 lines
       ├─ axf_parser.py      ← AXFParser: reads ELF symbol tables + DWARF debug info
       ├─ modbus_client.py   ← ModbusMemoryClient: dual-transport Modbus comm
       │    └─ websocket_client.py  ← WebSocketClient: cloud relay protocol
       └─ config_fixed.json  ← persisted user settings (port, baud, WS params, history)
```

**AXF parsing** (`axf_parser.py`): Uses `pyelftools` to extract the symbol table (`SHT_SYMTAB`) and DWARF debug info. Variable paths support dotted struct members (`a.b.c`) and array indexing (`a[0].b`). DWARF type resolution follows chains through typedef/const/volatile/pointer wrappers. Member offsets use ULEB128-decoded `DW_AT_data_member_location` expressions.

**Modbus transport** (`modbus_client.py`): `ModbusMemoryClient` abstracts over serial (pymodbus) and WebSocket. The device uses a custom register-based memory access protocol:
- Write a 32-bit memory address to registers **43507/43509/43511/43513** (4 groups)
- Read the 32-bit value from registers **43515/43517/43519/43521** (4 groups)
- Batch read writes all 4 addresses at once (function code 0x10 to 43507), then reads all 4 values (function code 0x03 from 43515, count=8)

**WebSocket protocol** (`websocket_client.py`): Communicates with cloud relay servers (test/production). Custom binary framing:
- Header: `7F 7F` | Function: `0x11` (H3PLUS) / `0x12` (X7) | 4-byte sequence | 2-byte data length | Modbus payload | CRC16 (over function..payload) | Footer: `F7 F7`
- X7 devices add `00 01` after the length field
- Messages are JSON-wrapped: `{"cmd":"send"/"listen", "resource":"...", "token":"...", "parameters":{"sn":"...", "content":"<hex>"}}`
- Response function bytes: `0x91` (H3PLUS), `0x92` (X7)
- Server URLs differ by server type (测试服/欧服) and device type (H3PLUS/X7)

**GUI threading** (`gui_fixed.py`): File loading and Modbus I/O run in daemon threads. Results are posted to the main thread via a `queue.Queue` polled at 100ms intervals (`_start_queue_processor`). The packet callback (`_on_packet`) only displays WebSocket frames whose hex starts with `7F 7F 91` or `7F 7F 92`.

**Auto-read timer**: Uses `root.after()` for non-blocking recurring batch reads at configurable intervals (500ms / 1S / 2S / 5S / 10S / 20S). `_toggle_auto_read()` starts/stops; `_auto_read_callback()` executes `_batch_read()` and reschedules itself. Changing the interval mid-run restarts the timer.

### modbus_tool/ (PyQt5, separate app)

A standalone PyQt5 serial Modbus tool with custom frame building, radix converter, and IEEE 754 converter. Built from `main_window.ui` via `pyuic5`. Not required for the main app.

## Key Implementation Details

- **Lazy pymodbus import**: `modbus_client.py` uses `_ensure_pymodbus()` to defer importing pymodbus until serial mode is actually used, avoiding asyncio event loop conflicts with tkinter.
- **Config file**: `config_fixed.json` is loaded/saved relative to the executable directory (handles PyInstaller `sys.frozen`). Persists comm settings, variable history (last 10), and recent AXF files (last 5).
- **Display types**: hex, float, int32, uint32, int16, uint16, int8, uint8 — both forward (`_convert_value`) and reverse (`_value_to_raw`) conversions using `struct.pack`/`unpack`.
- **CRC16**: Modbus RTU CRC (polynomial `0xA001`) is implemented in both `modbus_client.py` and `websocket_client.py`.
- **WebSocket auth**: Hardcoded JWT-style tokens per server environment. The `set_connection_params()` method recomputes `ws_url` from server type + device type.
- **Device offline detection**: WebSocket info responses with `content: "offline"` set `_device_offline = True`, which the GUI uses for user-facing error messages.
- **Serial port refresh**: `_refresh_ports()` repopulates the port dropdown on demand via a "刷新" button next to the selector.
- **Server type persistence**: The server type (测试服/欧服) is saved to `config["server"]` on change and applied to `ws_client.server_type` immediately — no reconnect needed.
- **Batch read/write**: The batch region supports both read and an independent write button per row. Each row uses a dedicated register pair:
  - Group 1: write addr → 43507, data → 43515
  - Group 2: write addr → 43509, data → 43517
  - Group 3: write addr → 43511, data → 43519
  - Group 4: write addr → 43513, data → 43521
  - `write_memory()` accepts optional `write_addr`/`read_addr` parameters for per-group targeting.
  - Small-type writes (int16/uint16/int8/uint8) merge new low bytes with previously-read high bytes; if never read, the GUI prompts the user to read first.
  - A custom `_confirm_write` dialog (Toplevel) shows old→new values before committing.

## Dependencies

| Package | Used By |
|---|---|
| `pyelftools>=0.30` | AXF/ELF parsing, DWARF debug info |
| `pymodbus>=3.6.8` | Serial Modbus RTU (lazy imported) |
| `pyserial>=3.5` | Serial port enumeration |
| `websocket-client>=1.8.0` | WebSocket cloud relay |
| `pyusb>=1.2.1` | Declared but not actively used |
| `python-dotenv>=1.0.0` | Declared but not used in source |
