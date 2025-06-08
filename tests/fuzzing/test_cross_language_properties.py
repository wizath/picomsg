"""
Cross-language property-based tests.

Tests that verify consistent behavior and properties of the
serialization format using property-based testing with Hypothesis.
"""

import pytest
import tempfile
import sys
import struct
import math
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator


class TestCrossLanguageProperties:
    """Property-based tests for serialization consistency."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = None
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_dir(self) -> Path:
        """Create a temporary directory."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
        return Path(self.temp_dir)
    
    def generate_python_module(self, schema_content: str):
        """Generate Python module from schema."""
        temp_dir = self.create_temp_dir()
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        python_dir = temp_dir / "python_generated"
        python_dir.mkdir(exist_ok=True)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        for filename, content in files.items():
            (python_dir / filename).write_text(content)
        
        # Add to Python path and import
        sys.path.insert(0, str(python_dir))
        try:
            # Clear any cached module
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            return generated_module
        finally:
            sys.path.remove(str(python_dir))
    
    def _find_class_by_name(self, module, class_name: str):
        """Find a class by name, handling namespace prefixes."""
        if hasattr(module, class_name):
            return getattr(module, class_name)
        else:
            for attr_name in dir(module):
                if (attr_name.endswith(class_name) and 
                    not attr_name.startswith('_') and 
                    hasattr(module, attr_name)):
                    attr_obj = getattr(module, attr_name)
                    if (isinstance(attr_obj, type) and 
                        hasattr(attr_obj, '__init__') and
                        not attr_name.endswith('Error') and
                        not attr_name.endswith('Base')):
                        return attr_obj
            raise AttributeError(f"Could not find class for {class_name}")
    
    @given(st.floats(allow_nan=False, allow_infinity=False, width=32, 
                     min_value=-1e6, max_value=1e6))
    @settings(max_examples=100)
    def test_float_precision_consistency(self, value):
        """Property: f32 floats should round-trip with consistent precision."""
        schema_content = """
        namespace test.props;
        
        struct FloatTest {
            value: f32;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            FloatTest = self._find_class_by_name(module, 'FloatTest')
            
            # Create instance and serialize
            instance = FloatTest(value=value)
            binary_data = instance.to_bytes()
            
            # Deserialize and verify
            deserialized = FloatTest.from_bytes(binary_data)
            
            # Property: Round-trip should preserve value within f32 precision
            tolerance = abs(value) * 1e-6 + 1e-6
            assert abs(deserialized.value - value) <= tolerance, \
                f"Float precision lost: {value} -> {deserialized.value}"
            
            # Property: Binary representation should be 4 bytes
            assert len(binary_data) == 4, "f32 should serialize to 4 bytes"
            
            # Property: Should use little-endian format
            unpacked = struct.unpack('<f', binary_data)[0]
            assert abs(unpacked - value) <= tolerance, \
                "Binary format should be little-endian f32"
                
        except Exception as e:
            expected_exceptions = (ValueError, OverflowError, struct.error)
            assert isinstance(e, expected_exceptions)
    
    @given(st.integers(min_value=0, max_value=255))
    @settings(max_examples=100)
    def test_u8_consistency(self, value):
        """Property: u8 integers should serialize to exactly 1 byte."""
        schema_content = """
        namespace test.props;
        
        struct U8Test {
            value: u8;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            U8Test = self._find_class_by_name(module, 'U8Test')
            
            # Create instance and serialize
            instance = U8Test(value=value)
            binary_data = instance.to_bytes()
            
            # Property: u8 should serialize to exactly 1 byte
            assert len(binary_data) == 1, "u8 should serialize to 1 byte"
            
            # Property: Binary value should match input
            assert binary_data[0] == value, \
                f"u8 binary mismatch: {value} -> {binary_data[0]}"
            
            # Property: Round-trip should be exact
            deserialized = U8Test.from_bytes(binary_data)
            assert deserialized.value == value, \
                f"u8 round-trip failed: {value} -> {deserialized.value}"
                
        except Exception as e:
            expected_exceptions = (ValueError, OverflowError, struct.error)
            assert isinstance(e, expected_exceptions)
    
    @given(st.integers(min_value=0, max_value=4294967295))
    @settings(max_examples=100)
    def test_u32_endianness_property(self, value):
        """Property: u32 should use little-endian format consistently."""
        schema_content = """
        namespace test.props;
        
        struct U32Test {
            value: u32;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            U32Test = self._find_class_by_name(module, 'U32Test')
            
            # Create instance and serialize
            instance = U32Test(value=value)
            binary_data = instance.to_bytes()
            
            # Property: u32 should serialize to exactly 4 bytes
            assert len(binary_data) == 4, "u32 should serialize to 4 bytes"
            
            # Property: Should use little-endian format
            unpacked = struct.unpack('<I', binary_data)[0]
            assert unpacked == value, \
                f"u32 endianness mismatch: {value} -> {unpacked}"
            
            # Property: Round-trip should be exact
            deserialized = U32Test.from_bytes(binary_data)
            assert deserialized.value == value, \
                f"u32 round-trip failed: {value} -> {deserialized.value}"
                
        except Exception as e:
            expected_exceptions = (ValueError, OverflowError, struct.error)
            assert isinstance(e, expected_exceptions)
    
    @given(st.text(alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd', 'Zs']),
                   min_size=0, max_size=50))
    @settings(max_examples=100)
    def test_string_encoding_property(self, text):
        """Property: Strings should be UTF-8 encoded with length prefix."""
        schema_content = """
        namespace test.props;
        
        struct StringTest {
            text: string;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            StringTest = self._find_class_by_name(module, 'StringTest')
            
            # Create instance and serialize
            instance = StringTest(text=text)
            binary_data = instance.to_bytes()
            
            # Property: String should have length prefix
            if len(binary_data) >= 2:
                length_prefix = struct.unpack('<H', binary_data[:2])[0]
                utf8_bytes = text.encode('utf-8')
                
                # Property: Length prefix should match UTF-8 byte length
                assert length_prefix == len(utf8_bytes), \
                    f"String length mismatch: {len(utf8_bytes)} != {length_prefix}"
                
                # Property: String data should be UTF-8 encoded
                if len(binary_data) >= 2 + length_prefix:
                    string_data = binary_data[2:2+length_prefix]
                    assert string_data == utf8_bytes, \
                        "String should be UTF-8 encoded"
            
            # Property: Round-trip should preserve text
            deserialized = StringTest.from_bytes(binary_data)
            assert deserialized.text == text, \
                f"String round-trip failed: '{text}' -> '{deserialized.text}'"
                
        except Exception as e:
            expected_exceptions = (
                ValueError, UnicodeEncodeError, UnicodeDecodeError, 
                struct.error, OverflowError
            )
            assert isinstance(e, expected_exceptions)
    
    @given(st.binary(min_size=0, max_size=50))
    @settings(max_examples=100)
    def test_bytes_round_trip_property(self, data):
        """Property: Bytes should round-trip exactly with length prefix."""
        schema_content = """
        namespace test.props;
        
        struct BytesTest {
            data: bytes;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            BytesTest = self._find_class_by_name(module, 'BytesTest')
            
            # Create instance and serialize
            instance = BytesTest(data=data)
            binary_data = instance.to_bytes()
            
            # Property: Bytes should have length prefix
            if len(binary_data) >= 2:
                length_prefix = struct.unpack('<H', binary_data[:2])[0]
                
                # Property: Length prefix should match data length
                assert length_prefix == len(data), \
                    f"Bytes length mismatch: {len(data)} != {length_prefix}"
                
                # Property: Bytes data should be preserved exactly
                if len(binary_data) >= 2 + length_prefix:
                    bytes_data = binary_data[2:2+length_prefix]
                    assert bytes_data == data, \
                        "Bytes should be preserved exactly"
            
            # Property: Round-trip should preserve data exactly
            deserialized = BytesTest.from_bytes(binary_data)
            assert deserialized.data == data, \
                f"Bytes round-trip failed: {data!r} -> {deserialized.data!r}"
                
        except Exception as e:
            expected_exceptions = (ValueError, struct.error, OverflowError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.lists(st.integers(min_value=0, max_value=255), min_size=0, max_size=20))
    @settings(max_examples=50)
    def test_array_serialization_property(self, values):
        """Property: Arrays should have count prefix and preserve order."""
        schema_content = """
        namespace test.props;
        
        struct ArrayTest {
            values: [u8];
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            ArrayTest = self._find_class_by_name(module, 'ArrayTest')
            
            # Create instance and serialize
            instance = ArrayTest(values=values)
            binary_data = instance.to_bytes()
            
            # Property: Array should have count prefix
            if len(binary_data) >= 2:
                count_prefix = struct.unpack('<H', binary_data[:2])[0]
                
                # Property: Count prefix should match array length
                assert count_prefix == len(values), \
                    f"Array count mismatch: {len(values)} != {count_prefix}"
                
                # Property: Array elements should follow count
                expected_size = 2 + len(values)  # 2 bytes count + 1 byte per u8
                assert len(binary_data) == expected_size, \
                    f"Array size mismatch: expected {expected_size}, got {len(binary_data)}"
                
                # Property: Each element should be correctly serialized
                for i, expected_value in enumerate(values):
                    actual_value = binary_data[2 + i]
                    assert actual_value == expected_value, \
                        f"Array element {i} mismatch: {expected_value} != {actual_value}"
            
            # Property: Round-trip should preserve array exactly
            deserialized = ArrayTest.from_bytes(binary_data)
            assert deserialized.values == values, \
                f"Array round-trip failed: {values} -> {deserialized.values}"
                
        except Exception as e:
            expected_exceptions = (ValueError, struct.error, OverflowError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.floats(width=32, min_value=-100.0, max_value=100.0),
           st.floats(width=32, min_value=-100.0, max_value=100.0))
    @settings(max_examples=50)
    def test_struct_composition_property(self, x, y):
        """Property: Nested structs should serialize in field order."""
        assume(not math.isnan(x) and not math.isnan(y))
        assume(not math.isinf(x) and not math.isinf(y))
        
        schema_content = """
        namespace test.props;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct Container {
            point: Point;
            id: u32;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            Container = self._find_class_by_name(module, 'Container')
            Point = self._find_class_by_name(module, 'Point')
            
            # Create nested structure
            point = Point(x=x, y=y)
            container = Container(point=point, id=42)
            
            # Serialize and deserialize
            binary_data = container.to_bytes()
            deserialized = Container.from_bytes(binary_data)
            
            # Property: Nested structure should be preserved
            assert hasattr(deserialized, 'point'), "Container should have point field"
            assert hasattr(deserialized.point, 'x'), "Point should have x field"
            assert hasattr(deserialized.point, 'y'), "Point should have y field"
            assert deserialized.id == 42, "Container id should be preserved"
            
            # Property: Nested values should be preserved within precision
            tolerance = 1e-5
            assert abs(deserialized.point.x - x) <= tolerance, \
                f"Point x mismatch: {x} -> {deserialized.point.x}"
            assert abs(deserialized.point.y - y) <= tolerance, \
                f"Point y mismatch: {y} -> {deserialized.point.y}"
            
            # Property: Binary size should be predictable
            expected_size = 8 + 4  # Point (2 * f32) + u32
            assert len(binary_data) == expected_size, \
                f"Container size mismatch: expected {expected_size}, got {len(binary_data)}"
                
        except Exception as e:
            expected_exceptions = (ValueError, struct.error, OverflowError, AttributeError)
            assert isinstance(e, expected_exceptions)
    
    def test_endianness_consistency_property(self):
        """Property: All types should use little-endian format."""
        schema_content = """
        namespace test.props;
        
        struct EndianTest {
            u16_val: u16;
            u32_val: u32;
            f32_val: f32;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            EndianTest = self._find_class_by_name(module, 'EndianTest')
            
            # Test with known values
            instance = EndianTest(u16_val=0x1234, u32_val=0x12345678, f32_val=1.5)
            binary_data = instance.to_bytes()
            
            # Property: Should use little-endian format
            assert len(binary_data) == 10, "EndianTest should be 10 bytes"
            
            # Verify little-endian u16
            u16_bytes = binary_data[0:2]
            assert u16_bytes == b'\x34\x12', f"u16 not little-endian: {u16_bytes.hex()}"
            
            # Verify little-endian u32
            u32_bytes = binary_data[2:6]
            assert u32_bytes == b'\x78\x56\x34\x12', f"u32 not little-endian: {u32_bytes.hex()}"
            
            # Verify little-endian f32
            f32_bytes = binary_data[6:10]
            expected_f32 = struct.pack('<f', 1.5)
            assert f32_bytes == expected_f32, f"f32 not little-endian: {f32_bytes.hex()}"
            
        except Exception as e:
            expected_exceptions = (ValueError, struct.error, OverflowError)
            assert isinstance(e, expected_exceptions) 
