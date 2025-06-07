"""
Binary format specification and utilities for PicoMsg.
"""

import struct
from typing import Optional
from dataclasses import dataclass


@dataclass
class BinaryFormat:
    """Binary format constants and utilities for PicoMsg."""
    
    # Magic bytes to identify PicoMsg format
    MAGIC_BYTES = b'\xAB\xCD'
    
    # Current format version
    VERSION = 1
    
    # Header size in bytes
    HEADER_SIZE = 8
    
    # Default alignment for structs
    DEFAULT_ALIGNMENT = 4
    
    # Maximum message size (4GB - 1)
    MAX_MESSAGE_SIZE = 0xFFFFFFFF
    
    @classmethod
    def create_header(cls, message_type_id: int, message_length: int) -> bytes:
        """Create a binary header for a message."""
        if message_type_id < 0 or message_type_id > 255:
            raise ValueError(f"Message type ID must be 0-255, got {message_type_id}")
        
        if message_length < 0 or message_length > cls.MAX_MESSAGE_SIZE:
            raise ValueError(f"Message length must be 0-{cls.MAX_MESSAGE_SIZE}, got {message_length}")
        
        # Header layout: [magic:2][version:1][type_id:1][length:4]
        return struct.pack('<2sBBL', 
                          cls.MAGIC_BYTES, 
                          cls.VERSION, 
                          message_type_id, 
                          message_length)
    
    @classmethod
    def parse_header(cls, header_bytes: bytes) -> tuple[int, int, int]:
        """Parse a binary header and return (version, type_id, length)."""
        if len(header_bytes) < cls.HEADER_SIZE:
            raise ValueError(f"Header too short: expected {cls.HEADER_SIZE} bytes, got {len(header_bytes)}")
        
        try:
            magic, version, type_id, length = struct.unpack('<2sBBL', header_bytes[:cls.HEADER_SIZE])
        except struct.error as e:
            raise ValueError(f"Invalid header format: {e}") from e
        
        if magic != cls.MAGIC_BYTES:
            raise ValueError(f"Invalid magic bytes: expected {cls.MAGIC_BYTES!r}, got {magic!r}")
        
        return version, type_id, length
    
    @classmethod
    def validate_header(cls, header_bytes: bytes) -> bool:
        """Validate a binary header without raising exceptions."""
        try:
            cls.parse_header(header_bytes)
            return True
        except ValueError:
            return False
    
    @classmethod
    def encode_string(cls, value: str) -> bytes:
        """Encode a string with length prefix (u16 + UTF-8 bytes)."""
        utf8_bytes = value.encode('utf-8')
        if len(utf8_bytes) > 65535:
            raise ValueError(f"String too long: {len(utf8_bytes)} bytes (max 65535)")
        return struct.pack('<H', len(utf8_bytes)) + utf8_bytes
    
    @classmethod
    def decode_string(cls, data: bytes, offset: int = 0) -> tuple[str, int]:
        """Decode a string from bytes and return (string, new_offset)."""
        if len(data) < offset + 2:
            raise ValueError("Not enough data for string length")
        
        length = struct.unpack('<H', data[offset:offset+2])[0]
        if len(data) < offset + 2 + length:
            raise ValueError(f"Not enough data for string: need {length} bytes")
        
        try:
            string_value = data[offset+2:offset+2+length].decode('utf-8')
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid UTF-8 string: {e}") from e
        
        return string_value, offset + 2 + length
    
    @classmethod
    def encode_bytes(cls, value: bytes) -> bytes:
        """Encode bytes with length prefix (u16 + raw bytes)."""
        if len(value) > 65535:
            raise ValueError(f"Bytes too long: {len(value)} bytes (max 65535)")
        return struct.pack('<H', len(value)) + value
    
    @classmethod
    def decode_bytes(cls, data: bytes, offset: int = 0) -> tuple[bytes, int]:
        """Decode bytes from data and return (bytes, new_offset)."""
        if len(data) < offset + 2:
            raise ValueError("Not enough data for bytes length")
        
        length = struct.unpack('<H', data[offset:offset+2])[0]
        if len(data) < offset + 2 + length:
            raise ValueError(f"Not enough data for bytes: need {length} bytes")
        
        bytes_value = data[offset+2:offset+2+length]
        return bytes_value, offset + 2 + length
    
    @classmethod
    def encode_array_header(cls, count: int) -> bytes:
        """Encode array count prefix (u16)."""
        if count < 0 or count > 65535:
            raise ValueError(f"Array count must be 0-65535, got {count}")
        return struct.pack('<H', count)
    
    @classmethod
    def decode_array_header(cls, data: bytes, offset: int = 0) -> tuple[int, int]:
        """Decode array count and return (count, new_offset)."""
        if len(data) < offset + 2:
            raise ValueError("Not enough data for array count")
        
        count = struct.unpack('<H', data[offset:offset+2])[0]
        return count, offset + 2
    
    @classmethod
    def calculate_crc16(cls, data: bytes) -> int:
        """Calculate CRC16 checksum for data."""
        # Simple CRC16-CCITT implementation
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc 
