"""
python-can Bus implementation for the Waveshare USB-CAN-A adapter.

Supports two configurable wire protocols:
  - VARIABLE: AA <type> <id> <data> 55 (compact, no hardware filtering)
  - FIXED: AA 55 ... (20-byte constant, hardware filtering available)

Both use little-endian byte order and standard can.Message interface.
The adapter is configured via configure(); defaults are VARIABLE protocol
with standard 11-bit IDs. All subsequent send()/recv() calls use the
configured protocol transparently.
"""

import time
import serial
from enum import Enum
from can import BusABC, Message
from can.exceptions import CanInitializationError, CanOperationError


# ===========================================================================
# CONSTANTS
# ===========================================================================

# Protocol framing
VARIABLE_HEADER = 0xAA
VARIABLE_TAIL = 0x55
FIXED_HEADER = bytes([0xAA, 0x55])

# Variable protocol
VARIABLE_TYPE_BASE = 0xC0           # byte[1] bits 7-6: 1
VARIABLE_TYPE_EXTENDED = 0x20       # byte[1] bit5: extended ID
VARIABLE_TYPE_REMOTE = 0x10         # byte[1] bit4: remote frame
VARIABLE_TYPE_DLC_MASK = 0x0F       # byte[1] bits 3-0: DLC

# Fixed protocol
FIXED_FRAME_SIZE = 20
FIXED_PROTOCOL_TYPE = 0x01          # byte[2]: always 0x01 for fixed-length format
FIXED_FRAME_TYPE_STANDARD = 0x01    # byte[3]: standard frame type (11-bit CAN ID)
FIXED_FRAME_TYPE_EXTENDED = 0x02    # byte[3]: extended frame type 29-bit CAN ID
FIXED_FRAME_FORMAT_DATA = 0x01      # byte[4]: data frame format
FIXED_FRAME_FORMAT_RTR = 0x02       # byte[4]: remote frame format

# CAN ID limits
STANDARD_ID_MAX = 0x7FF             # 11-bit
EXTENDED_ID_MAX = 0x1FFFFFFF        # 29-bit


# ===========================================================================
# CUSTOM DATA TYPES
# ===========================================================================

class CANProtocol(Enum):
    FIXED = 0x02
    VARIABLE = 0x12

class CANBaudRate(Enum):
    MBPS_1 = 0x01
    KBPS_800 = 0x02
    KBPS_500 = 0x03
    KBPS_400 = 0x04
    KBPS_250 = 0x05
    KBPS_200 = 0x06
    KBPS_125 = 0x07
    KBPS_100 = 0x08
    KBPS_50 = 0x09
    KBPS_20 = 0x0A
    KBPS_10 = 0x0B
    KBPS_5 = 0x0C

class CANFrameType(Enum):
    STANDARD = 0x01
    EXTENDED = 0x02

class CANMode(Enum):
    NORMAL = 0x00
    LOOPBACK = 0x01
    SILENT = 0x02
    SILENT_LOOPBACK = 0x03

# ===========================================================================
# WAVESHARE BUS CLASS
# ===========================================================================

class WaveshareCANBus(BusABC):
    """
    python-can Bus backend for the Waveshare USB-CAN-A adapter.

    Wraps the adapter's serial protocol (variable-length or fixed 20-byte
    framing, see module docstring) behind the standard python-can BusABC
    interface, so it's a drop-in replacement for socketcan/pcan/slcan etc.

    On construction, the adapter is configured with sensible defaults
    (variable-length protocol, standard 11-bit frames). Call `configure()`
    again afterwards to change protocol, baud rate, or hardware filters.
    """

    def __init__(
        self,
        channel,
        baudrate=2000000,
        can_filters=None,
        serial_timeout=0.001,
        **kwargs,
    ):
        """
        Open the serial connection and configure the adapter.

        Args:
            channel: Serial port (e.g. "COM6" on Windows, "/dev/ttyUSB0" on Linux)
            baudrate: Serial link speed to the adapter (not the CAN bus speed)
            can_filters: Standard python-can filter list (applied by BusABC,
                separate from the adapter's own hardware filtering)
            serial_timeout: Read timeout for the underlying serial port
        """
        self.channel = channel

        try:
            self.serial = serial.Serial(
                port=channel,
                baudrate=baudrate,
                timeout=serial_timeout,
            )
        except serial.SerialException as exc:
            raise CanInitializationError(
                f"Could not open Waveshare adapter on {channel!r}: {exc}"
            ) from exc

        super().__init__(channel=channel, can_filters=can_filters, **kwargs)

        self.configure()

    def configure(
        self,
        protocol: CANProtocol = CANProtocol.VARIABLE,
        can_baudrate: CANBaudRate = CANBaudRate.KBPS_250,
        frame_type: CANFrameType = CANFrameType.STANDARD,
        filter_id=0x00000000,
        block_id=0x00000000,
        can_mode: CANMode = CANMode.NORMAL,
        auto_retransmit=0x00,
        settle_s=0.1,
    ):
        """
        Send the adapter's 20-byte configuration frame.

        This always uses the fixed 20-byte framing on the wire (the config
        frame format is separate from the CANProtocol being configured for
        subsequent send/recv traffic).

        Args:
            protocol: CANProtocol to use for send()/recv() after this call
            can_baudrate: Adapter's CAN bus speed code (adapter-specific enum,
                not the serial baudrate)
            frame_type: Standard (11-bit) or extended (29-bit) CAN IDs
            filter_id / block_id: Hardware acceptance filter (FIXED protocol
                only; ignored by the adapter in VARIABLE mode)
            can_mode: Adapter CAN mode (0x00 = normal; see adapter datasheet
                for loopback/silent/etc. codes)
            auto_retransmit: 0x00 = enabled, 0x01 = disabled (per adapter spec)
            settle_s: Time to wait after writing the config frame before
                returning. The adapter needs to internally reprogram its CAN
                controller after this write; it does not ack completion, so
                sending real traffic immediately after can be dropped or
                corrupted. This is a pragmatic delay, not a protocol
                requirement — lower it at your own risk, or raise it if you
                still see missed frames right after reconfiguration.
        """
        self._protocol = protocol
        self._can_baudrate = can_baudrate
        self._frame_type = frame_type
        
        frame = bytearray(FIXED_FRAME_SIZE)

        # Header
        frame[0:2] = FIXED_HEADER

        # Type
        frame[2] = protocol.value

        # Baud rate
        frame[3] = can_baudrate.value

        # Frame type
        frame[4] = frame_type.value

        # Filter ID / Block ID (bytes 5-8, 9-12): little-endian, matching the
        # ID byte order used everywhere else in the fixed 20-byte protocol
        # (see _encode_fixed / _parse_fixed).
        frame[5:9] = filter_id.to_bytes(4, "little")
        frame[9:13] = block_id.to_bytes(4, "little")

        # CAN mode
        frame[13] = can_mode.value

        # Auto retransmit
        frame[14] = auto_retransmit

        # Bytes 15-18 reserved (already 0)

        # Checksum (byte 19): sum of bytes 2-18, low 8 bits
        checksum = sum(frame[2:19]) & 0xFF
        frame[19] = checksum

        try:
            self.serial.write(frame)
            self.serial.flush()
            time.sleep(settle_s)
        except serial.SerialException as exc:
            raise CanOperationError(f"Error configuring adapter: {exc}") from exc
        
        

    def send(self, msg: Message, timeout=None):
        """Encode and write a can.Message using the configured protocol."""
        if msg.is_fd:
            raise CanOperationError("CAN FD not supported")

        if msg.dlc > 8:
            raise CanOperationError("Max DLC is 8")

        if self._protocol == CANProtocol.VARIABLE:
            frame = self._encode_variable(msg)
        elif self._protocol == CANProtocol.FIXED:
            frame = self._encode_fixed(msg)
        else:
            raise ValueError(f"Unknown protocol: {self._protocol}")

        try:
            t0 = time.time()
            self.serial.write(frame)
            self.serial.flush()
            t1 = time.time()

        except serial.SerialException as exc:
            raise CanOperationError(f"Serial write failed: {exc}") from exc

    def shutdown(self):
        """Close the underlying serial port."""
        super().shutdown()
        if getattr(self, "serial", None) and self.serial.is_open:
            self.serial.close()
    
    def _encode_variable(self, msg: Message) -> bytes:
        """Build a variable-length AA <type> <id> <data> 55 frame."""
        type_byte = VARIABLE_TYPE_BASE | (msg.dlc & VARIABLE_TYPE_DLC_MASK)

        if msg.is_extended_id:
            type_byte |= VARIABLE_TYPE_EXTENDED
            id_bytes = msg.arbitration_id.to_bytes(4, "little")
        else:
            id_bytes = msg.arbitration_id.to_bytes(2, "little")

        if msg.is_remote_frame:
            type_byte |= VARIABLE_TYPE_REMOTE
            payload = b""
        else:
            payload = bytes(msg.data[:msg.dlc])
        
        return bytes(
            [VARIABLE_HEADER, type_byte]
        ) + id_bytes + payload + bytes([VARIABLE_TAIL])

    
    def _encode_fixed(self, msg: Message) -> bytes:
        """Build a fixed 20-byte AA 55 ... frame."""
        frame_type = FIXED_FRAME_TYPE_EXTENDED if msg.is_extended_id else FIXED_FRAME_TYPE_STANDARD
        frame_format = FIXED_FRAME_FORMAT_RTR if msg.is_remote_frame else FIXED_FRAME_FORMAT_DATA

        id_bytes = msg.arbitration_id.to_bytes(4, "little")
        data = bytes(msg.data[:msg.dlc]).ljust(8, b"\x00")

        body = (
            bytes([FIXED_PROTOCOL_TYPE, frame_type, frame_format])
            + id_bytes
            + bytes([msg.dlc])
            + data
            + bytes([0x00])  # reserved
        )

        checksum = sum(body) & 0xFF
        frame = FIXED_HEADER + body + bytes([checksum])
        
        if len(frame) != FIXED_FRAME_SIZE:
            raise CanOperationError("Fixed frame must be 20 bytes")

        return frame

    def _recv_internal(self, timeout):
        """
        BusABC hook: block up to `timeout` seconds for the next frame.

        Uses a state-machine framer that reads the minimum number of bytes at
        each step, so each serial.read() call blocks for exactly as long as it
        takes to receive the bytes it asked for — no more.

        Variable protocol  (AA <type> <id_2or4> <data_0to8> 55):
          1. Read 1 byte at a time until 0xAA header.
          2. Read 1 byte: type byte encodes ext/rtr/dlc.
          3. Read (id_len + data_len) bytes: rest of payload.
          4. Read 1 byte: verify 0x55 tail.

        Fixed protocol  (AA 55 <18 bytes>):
          1. Read 1 byte at a time until 0xAA header.
          2. Read 1 byte: must be 0x55 (second header byte); retry if not.
          3. Read remaining 18 bytes to complete the 20-byte frame.
          4. Validate checksum; retry from step 1 if it fails.
        """
        deadline = None if timeout is None else time.time() + timeout

        if self._protocol == CANProtocol.VARIABLE:
            return self._recv_variable(deadline), False
        else:
            return self._recv_fixed(deadline), False

    def _read_exact(self, n: int, deadline) -> bytes:
        """
        Read exactly ``n`` bytes from the serial port, respecting ``deadline``.

        Each call to serial.read() is bounded by the time remaining so we
        never block past the caller's timeout.  Raises CanOperationError on a
        serial fault and returns b"" if the deadline expires before all bytes
        arrive (the caller treats that as a timeout / None frame).
        """
        buf = b""
        while len(buf) < n:
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return b""
            try:
                chunk = self.serial.read(n - len(buf))
            except serial.SerialException as exc:
                raise CanOperationError(f"Serial read failed: {exc}") from exc
            if not chunk:
                return b""   # timeout expired inside serial.read()
            buf += chunk
        return buf

    def _recv_variable(self, deadline):
        """Read and parse one variable-length frame, or return None on timeout."""
        while True:
            # Step 1: hunt for 0xAA header one byte at a time
            b = self._read_exact(1, deadline)
            if not b:
                return None
            if b[0] != VARIABLE_HEADER:
                continue
            
            # Step 2: read type byte
            b = self._read_exact(1, deadline)
            if not b:
                return None
            type_byte = b[0]
            
            is_ext = bool(type_byte & VARIABLE_TYPE_EXTENDED)
            is_rtr = bool(type_byte & VARIABLE_TYPE_REMOTE)
            dlc    = type_byte & VARIABLE_TYPE_DLC_MASK

            id_len   = 4 if is_ext else 2
            data_len = 0 if is_rtr else dlc

            # Step 3: read ID + data in one shot
            payload = self._read_exact(id_len + data_len, deadline)
            if len(payload) < id_len + data_len:
                return None

            # Step 4: read and verify tail byte
            tail = self._read_exact(1, deadline)
            if not tail:
                return None
            if tail[0] != VARIABLE_TAIL:
                # Corrupted frame — discard and resync from next 0xAA
                continue

            can_id = int.from_bytes(payload[:id_len], "little")
            data   = payload[id_len:]

            return Message(
                arbitration_id=can_id,
                data=data,
                dlc=dlc,
                is_extended_id=is_ext,
                is_remote_frame=is_rtr,
                timestamp=time.time(),
            )

    def _recv_fixed(self, deadline):
        """Read and parse one fixed 20-byte frame, or return None on timeout."""
        while True:
            # Step 1: hunt for 0xAA header one byte at a time
            b = self._read_exact(1, deadline)
            if not b:
                return None
            if b[0] != FIXED_HEADER[0]:
                continue

            # Step 2: read second header byte; must be 0x55
            b = self._read_exact(1, deadline)
            if not b:
                return None
            if b[0] != FIXED_HEADER[1]:
                # Not a valid fixed-frame header; the byte we just read might
                # itself be 0xAA, so loop back and re-examine it — but since
                # we can't push it back, just restart the hunt.
                continue

            # Step 3: read the remaining 18 bytes
            rest = self._read_exact(FIXED_FRAME_SIZE - 2, deadline)
            if len(rest) < FIXED_FRAME_SIZE - 2:
                return None

            frame = bytes(FIXED_HEADER) + rest

            # Step 4: validate checksum (bytes 2–18, low 8 bits)
            if sum(frame[2:19]) & 0xFF != frame[19]:
                continue   # bad checksum — resync from next 0xAA

            dlc = frame[9]
            if dlc > 8:
                continue   # invalid DLC — resync

            can_id      = int.from_bytes(frame[5:9], "little")
            is_extended = frame[3] == FIXED_FRAME_TYPE_EXTENDED
            is_remote   = frame[4] == FIXED_FRAME_FORMAT_RTR

            return Message(
                arbitration_id=can_id,
                data=bytes(frame[10:10 + dlc]),
                dlc=dlc,
                is_extended_id=is_extended,
                is_remote_frame=is_remote,
                timestamp=time.time(),
            )