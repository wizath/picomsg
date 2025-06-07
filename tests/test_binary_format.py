"""
Tests for PicoMsg binary format utilities.
"""

import pytest
import struct
from picomsg.format.binary import BinaryFormat


class TestBinaryFormat:
    """Test BinaryFormat class."""
    
    def test_constants(self):
        """Test binary format constants."""
        assert BinaryFormat.MAGIC_BYTES == b'\xAB\xCD'
        assert BinaryFormat.VERSION == 1
        assert BinaryFormat.HEADER_SIZE == 8
        assert BinaryFormat.DEFAULT_ALIGNMENT == 4
        assert BinaryFormat.MAX_MESSAGE_SIZE == 0xFFFFFFFF
    
    def test_create_header_valid(self):
        """Test creating valid headers."""
        header = BinaryFormat.create_header(42, 1024)
        assert len(header) == 8
        
        # Verify header structure
        magic, version, type_id, length = struct.unpack('<2sBBL', header)
        assert magic == b'\xAB\xCD'
        assert version == 1
        assert type_id == 42
        assert length == 1024
    
    def test_create_header_edge_cases(self):
        """Test creating headers with edge case values."""
        # Minimum values
        header = BinaryFormat.create_header(0, 0)
        _, _, type_id, length = struct.unpack('<2sBBL', header)
        assert type_id == 0
        assert length == 0
        
        # Maximum values
        header = BinaryFormat.create_header(255, BinaryFormat.MAX_MESSAGE_SIZE)
        _, _, type_id, length = struct.unpack('<2sBBL', header)
        assert type_id == 255
        assert length == BinaryFormat.MAX_MESSAGE_SIZE
    
    def test_create_header_invalid_type_id(self):
        """Test creating header with invalid type ID."""
        with pytest.raises(ValueError, match="Message type ID must be 0-255"):
            BinaryFormat.create_header(-1, 100)
        
        with pytest.raises(ValueError, match="Message type ID must be 0-255"):
            BinaryFormat.create_header(256, 100)
    
    def test_create_header_invalid_length(self):
        """Test creating header with invalid length."""
        with pytest.raises(ValueError, match="Message length must be"):
            BinaryFormat.create_header(1, -1)
        
        with pytest.raises(ValueError, match="Message length must be"):
            BinaryFormat.create_header(1, BinaryFormat.MAX_MESSAGE_SIZE + 1)
    
    def test_parse_header_valid(self):
        """Test parsing valid headers."""
        header = BinaryFormat.create_header(42, 1024)
        version, type_id, length = BinaryFormat.parse_header(header)
        
        assert version == 1
        assert type_id == 42
        assert length == 1024
    
    def test_parse_header_too_short(self):
        """Test parsing header that's too short."""
        short_header = b'\xAB\xCD\x01'  # Only 3 bytes
        with pytest.raises(ValueError, match="Header too short"):
            BinaryFormat.parse_header(short_header)
    
    def test_parse_header_invalid_magic(self):
        """Test parsing header with invalid magic bytes."""
        invalid_header = struct.pack('<2sBBL', b'\xFF\xFF', 1, 42, 1024)
        with pytest.raises(ValueError, match="Invalid magic bytes"):
            BinaryFormat.parse_header(invalid_header)
    
    def test_parse_header_with_extra_data(self):
        """Test parsing header with extra data after header."""
        header = BinaryFormat.create_header(42, 1024)
        header_with_extra = header + b'extra_data'
        
        version, type_id, length = BinaryFormat.parse_header(header_with_extra)
        assert version == 1
        assert type_id == 42
        assert length == 1024
    
    def test_validate_header_valid(self):
        """Test validating valid headers."""
        header = BinaryFormat.create_header(42, 1024)
        assert BinaryFormat.validate_header(header) is True
    
    def test_validate_header_invalid(self):
        """Test validating invalid headers."""
        # Too short
        assert BinaryFormat.validate_header(b'\xAB\xCD') is False
        
        # Invalid magic
        invalid_header = struct.pack('<2sBBL', b'\xFF\xFF', 1, 42, 1024)
        assert BinaryFormat.validate_header(invalid_header) is False
    
    def test_encode_string_valid(self):
        """Test encoding valid strings."""
        # Empty string
        encoded = BinaryFormat.encode_string("")
        assert encoded == b'\x00\x00'
        
        # ASCII string
        encoded = BinaryFormat.encode_string("hello")
        expected = struct.pack('<H', 5) + b'hello'
        assert encoded == expected
        
        # UTF-8 string
        encoded = BinaryFormat.encode_string("héllo")
        utf8_bytes = "héllo".encode('utf-8')
        expected = struct.pack('<H', len(utf8_bytes)) + utf8_bytes
        assert encoded == expected
    
    def test_encode_string_too_long(self):
        """Test encoding string that's too long."""
        long_string = 'x' * 65536  # Too long for u16 length
        with pytest.raises(ValueError, match="String too long"):
            BinaryFormat.encode_string(long_string)
    
    def test_decode_string_valid(self):
        """Test decoding valid strings."""
        # Empty string
        data = b'\x00\x00'
        string, offset = BinaryFormat.decode_string(data)
        assert string == ""
        assert offset == 2
        
        # ASCII string
        data = struct.pack('<H', 5) + b'hello'
        string, offset = BinaryFormat.decode_string(data)
        assert string == "hello"
        assert offset == 7
        
        # UTF-8 string
        utf8_bytes = "héllo".encode('utf-8')
        data = struct.pack('<H', len(utf8_bytes)) + utf8_bytes
        string, offset = BinaryFormat.decode_string(data)
        assert string == "héllo"
        assert offset == 2 + len(utf8_bytes)
    
    def test_decode_string_with_offset(self):
        """Test decoding string with custom offset."""
        prefix = b'prefix'
        data = prefix + struct.pack('<H', 5) + b'hello'
        
        string, new_offset = BinaryFormat.decode_string(data, offset=len(prefix))
        assert string == "hello"
        assert new_offset == len(prefix) + 7
    
    def test_decode_string_insufficient_data(self):
        """Test decoding string with insufficient data."""
        # Not enough data for length
        with pytest.raises(ValueError, match="Not enough data for string length"):
            BinaryFormat.decode_string(b'\x00')
        
        # Not enough data for string content
        data = struct.pack('<H', 10) + b'short'  # Claims 10 bytes but only has 5
        with pytest.raises(ValueError, match="Not enough data for string"):
            BinaryFormat.decode_string(data)
    
    def test_decode_string_invalid_utf8(self):
        """Test decoding string with invalid UTF-8."""
        invalid_utf8 = b'\xFF\xFE'  # Invalid UTF-8 sequence
        data = struct.pack('<H', len(invalid_utf8)) + invalid_utf8
        
        with pytest.raises(ValueError, match="Invalid UTF-8 string"):
            BinaryFormat.decode_string(data)
    
    def test_encode_bytes_valid(self):
        """Test encoding valid byte arrays."""
        # Empty bytes
        encoded = BinaryFormat.encode_bytes(b"")
        assert encoded == b'\x00\x00'
        
        # Regular bytes
        test_bytes = b'\x01\x02\x03\x04'
        encoded = BinaryFormat.encode_bytes(test_bytes)
        expected = struct.pack('<H', 4) + test_bytes
        assert encoded == expected
    
    def test_encode_bytes_too_long(self):
        """Test encoding bytes that are too long."""
        long_bytes = b'x' * 65536  # Too long for u16 length
        with pytest.raises(ValueError, match="Bytes too long"):
            BinaryFormat.encode_bytes(long_bytes)
    
    def test_decode_bytes_valid(self):
        """Test decoding valid byte arrays."""
        # Empty bytes
        data = b'\x00\x00'
        bytes_value, offset = BinaryFormat.decode_bytes(data)
        assert bytes_value == b""
        assert offset == 2
        
        # Regular bytes
        test_bytes = b'\x01\x02\x03\x04'
        data = struct.pack('<H', 4) + test_bytes
        bytes_value, offset = BinaryFormat.decode_bytes(data)
        assert bytes_value == test_bytes
        assert offset == 6
    
    def test_decode_bytes_with_offset(self):
        """Test decoding bytes with custom offset."""
        prefix = b'prefix'
        test_bytes = b'\x01\x02\x03'
        data = prefix + struct.pack('<H', 3) + test_bytes
        
        bytes_value, new_offset = BinaryFormat.decode_bytes(data, offset=len(prefix))
        assert bytes_value == test_bytes
        assert new_offset == len(prefix) + 5
    
    def test_decode_bytes_insufficient_data(self):
        """Test decoding bytes with insufficient data."""
        # Not enough data for length
        with pytest.raises(ValueError, match="Not enough data for bytes length"):
            BinaryFormat.decode_bytes(b'\x00')
        
        # Not enough data for bytes content
        data = struct.pack('<H', 10) + b'short'  # Claims 10 bytes but only has 5
        with pytest.raises(ValueError, match="Not enough data for bytes"):
            BinaryFormat.decode_bytes(data)
    
    def test_encode_array_header_valid(self):
        """Test encoding valid array headers."""
        # Empty array
        encoded = BinaryFormat.encode_array_header(0)
        assert encoded == b'\x00\x00'
        
        # Regular array
        encoded = BinaryFormat.encode_array_header(1024)
        expected = struct.pack('<H', 1024)
        assert encoded == expected
        
        # Maximum array size
        encoded = BinaryFormat.encode_array_header(65535)
        expected = struct.pack('<H', 65535)
        assert encoded == expected
    
    def test_encode_array_header_invalid(self):
        """Test encoding invalid array headers."""
        with pytest.raises(ValueError, match="Array count must be 0-65535"):
            BinaryFormat.encode_array_header(-1)
        
        with pytest.raises(ValueError, match="Array count must be 0-65535"):
            BinaryFormat.encode_array_header(65536)
    
    def test_decode_array_header_valid(self):
        """Test decoding valid array headers."""
        # Empty array
        data = b'\x00\x00'
        count, offset = BinaryFormat.decode_array_header(data)
        assert count == 0
        assert offset == 2
        
        # Regular array
        data = struct.pack('<H', 1024)
        count, offset = BinaryFormat.decode_array_header(data)
        assert count == 1024
        assert offset == 2
    
    def test_decode_array_header_with_offset(self):
        """Test decoding array header with custom offset."""
        prefix = b'prefix'
        data = prefix + struct.pack('<H', 42)
        
        count, new_offset = BinaryFormat.decode_array_header(data, offset=len(prefix))
        assert count == 42
        assert new_offset == len(prefix) + 2
    
    def test_decode_array_header_insufficient_data(self):
        """Test decoding array header with insufficient data."""
        with pytest.raises(ValueError, match="Not enough data for array count"):
            BinaryFormat.decode_array_header(b'\x00')
    
    def test_calculate_crc16(self):
        """Test CRC16 calculation."""
        # Empty data
        crc = BinaryFormat.calculate_crc16(b"")
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
        
        # Known test vectors
        test_data = b"123456789"
        crc = BinaryFormat.calculate_crc16(test_data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
        
        # Different data should produce different CRC
        crc1 = BinaryFormat.calculate_crc16(b"hello")
        crc2 = BinaryFormat.calculate_crc16(b"world")
        assert crc1 != crc2
        
        # Same data should produce same CRC
        crc3 = BinaryFormat.calculate_crc16(b"hello")
        assert crc1 == crc3
    
    def test_round_trip_string(self):
        """Test string encoding/decoding round trip."""
        test_strings = [
            "",
            "hello",
            "héllo wörld",
            "🚀 emoji test",
            "a" * 1000,  # Long string
        ]
        
        for original in test_strings:
            encoded = BinaryFormat.encode_string(original)
            decoded, offset = BinaryFormat.decode_string(encoded)
            assert decoded == original
            assert offset == len(encoded)
    
    def test_round_trip_bytes(self):
        """Test bytes encoding/decoding round trip."""
        test_bytes = [
            b"",
            b"hello",
            b"\x00\x01\x02\x03\xFF",
            bytes(range(256)),  # All byte values
            b"x" * 1000,  # Long bytes
        ]
        
        for original in test_bytes:
            encoded = BinaryFormat.encode_bytes(original)
            decoded, offset = BinaryFormat.decode_bytes(encoded)
            assert decoded == original
            assert offset == len(encoded)
    
    def test_round_trip_header(self):
        """Test header creation/parsing round trip."""
        test_cases = [
            (0, 0),
            (42, 1024),
            (255, BinaryFormat.MAX_MESSAGE_SIZE),
        ]
        
        for type_id, length in test_cases:
            header = BinaryFormat.create_header(type_id, length)
            version, parsed_type_id, parsed_length = BinaryFormat.parse_header(header)
            
            assert version == BinaryFormat.VERSION
            assert parsed_type_id == type_id
            assert parsed_length == length 
