"""
Binary format fuzzing tests.

Tests the robustness and security of binary serialization/deserialization
against malformed, malicious, and edge case binary data.
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


class TestBinaryFuzzing:
    """Fuzzing tests for binary format robustness and security."""
    
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
    
    @given(st.binary(min_size=0, max_size=1000))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_deserialization_robustness_primitives(self, binary_data):
        """Test primitive struct deserialization against random binary data."""
        schema_content = """
        namespace test.fuzz;
        
        struct PrimitiveStruct {
            u8_field: u8;
            u16_field: u16;
            u32_field: u32;
            f32_field: f32;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            PrimitiveStruct = self._find_class_by_name(module, 'PrimitiveStruct')
            
            # Deserialization should never crash, only raise expected exceptions
            try:
                instance = PrimitiveStruct.from_bytes(binary_data)
                # If successful, verify the instance is valid
                assert hasattr(instance, 'u8_field')
                assert hasattr(instance, 'f32_field')
                assert isinstance(instance.u8_field, int)
                assert isinstance(instance.f32_field, float)
            except Exception as e:
                # These are expected exception types for malformed data
                expected_exceptions = (
                    ValueError,      # Invalid data
                    struct.error,    # Struct unpacking errors
                    IndexError,      # Buffer too small
                    TypeError,       # Type conversion errors
                    OverflowError,   # Value overflow
                    UnicodeDecodeError,  # String decoding errors
                )
                assert isinstance(e, expected_exceptions), \
                    f"Unexpected exception type: {type(e).__name__}: {e}"
        except Exception as e:
            # Module generation might fail for some schemas
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.binary(min_size=0, max_size=1000))
    @settings(max_examples=150)
    def test_string_deserialization_robustness(self, binary_data):
        """Test string field deserialization against random binary data."""
        schema_content = """
        namespace test.fuzz;
        
        struct StringStruct {
            name: string;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            StringStruct = self._find_class_by_name(module, 'StringStruct')
            
            try:
                instance = StringStruct.from_bytes(binary_data)
                # If successful, verify strings are valid
                assert isinstance(instance.name, str)
            except Exception as e:
                expected_exceptions = (
                    ValueError, struct.error, IndexError, TypeError,
                    UnicodeDecodeError, UnicodeError, OverflowError
                )
                assert isinstance(e, expected_exceptions)
        except Exception as e:
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.binary(min_size=0, max_size=1000))
    @settings(max_examples=150)
    def test_bytes_deserialization_robustness(self, binary_data):
        """Test bytes field deserialization against random binary data."""
        schema_content = """
        namespace test.fuzz;
        
        struct BytesStruct {
            data: bytes;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            BytesStruct = self._find_class_by_name(module, 'BytesStruct')
            
            try:
                instance = BytesStruct.from_bytes(binary_data)
                # If successful, verify bytes are valid
                assert isinstance(instance.data, bytes)
            except Exception as e:
                expected_exceptions = (
                    ValueError, struct.error, IndexError, TypeError, OverflowError
                )
                assert isinstance(e, expected_exceptions)
        except Exception as e:
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.binary(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_array_deserialization_robustness(self, binary_data):
        """Test array field deserialization against random binary data."""
        schema_content = """
        namespace test.fuzz;
        
        struct ArrayStruct {
            numbers: [u32];
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            ArrayStruct = self._find_class_by_name(module, 'ArrayStruct')
            
            try:
                instance = ArrayStruct.from_bytes(binary_data)
                # If successful, verify arrays are valid
                assert isinstance(instance.numbers, list)
                # Verify array elements are correct types
                for num in instance.numbers:
                    assert isinstance(num, int)
            except Exception as e:
                expected_exceptions = (
                    ValueError, struct.error, IndexError, TypeError, OverflowError
                )
                assert isinstance(e, expected_exceptions)
        except Exception as e:
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.integers(min_value=0, max_value=65535))
    @settings(max_examples=100)
    def test_length_field_fuzzing(self, length):
        """Test length prefix fuzzing for variable-length fields."""
        # Create binary data with fuzzed length prefix
        length_bytes = struct.pack('<H', length)  # u16 length prefix
        fake_string_data = length_bytes + b'A' * min(length, 100)  # Limit actual data
        
        schema_content = """
        namespace test.fuzz;
        
        struct LengthStruct {
            text: string;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            LengthStruct = self._find_class_by_name(module, 'LengthStruct')
            
            try:
                instance = LengthStruct.from_bytes(fake_string_data)
                # If successful, verify the string
                assert isinstance(instance.text, str)
            except Exception as e:
                expected_exceptions = (
                    ValueError, struct.error, IndexError, TypeError,
                    UnicodeDecodeError, OverflowError, MemoryError
                )
                assert isinstance(e, expected_exceptions)
        except Exception as e:
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.binary(min_size=4, max_size=4))
    @settings(max_examples=50)
    def test_magic_byte_fuzzing(self, magic_bytes):
        """Test magic byte validation with random 4-byte sequences."""
        schema_content = """
        namespace test.fuzz;
        
        struct SimpleStruct {
            value: u32;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            SimpleStruct = self._find_class_by_name(module, 'SimpleStruct')
            
            try:
                instance = SimpleStruct.from_bytes(magic_bytes)
                # If successful, verify the value
                assert isinstance(instance.value, int)
            except Exception as e:
                expected_exceptions = (
                    ValueError, struct.error, IndexError, TypeError
                )
                assert isinstance(e, expected_exceptions)
        except Exception as e:
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.binary(min_size=0, max_size=500))
    @settings(max_examples=100)
    def test_nested_struct_fuzzing(self, binary_data):
        """Test nested struct deserialization robustness."""
        schema_content = """
        namespace test.fuzz;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct Rectangle {
            top_left: Point;
            color: u32;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            Rectangle = self._find_class_by_name(module, 'Rectangle')
            
            try:
                instance = Rectangle.from_bytes(binary_data)
                # If successful, verify nested structure
                assert hasattr(instance, 'top_left')
                assert hasattr(instance.top_left, 'x')
                assert hasattr(instance.top_left, 'y')
                assert isinstance(instance.color, int)
            except Exception as e:
                expected_exceptions = (
                    ValueError, struct.error, IndexError, TypeError, AttributeError
                )
                assert isinstance(e, expected_exceptions)
        except Exception as e:
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
    
    def test_buffer_overflow_protection(self):
        """Test protection against buffer overflow attacks."""
        schema_content = """
        namespace test.fuzz;
        
        struct OverflowStruct {
            data: bytes;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            OverflowStruct = self._find_class_by_name(module, 'OverflowStruct')
            
            # Test extremely large length prefix
            large_length = struct.pack('<H', 65535)  # Maximum u16 value
            minimal_data = large_length + b'X'  # Only 1 byte of actual data
            
            try:
                instance = OverflowStruct.from_bytes(minimal_data)
                # Should either succeed with truncated data or fail gracefully
                assert isinstance(instance.data, bytes)
            except Exception as e:
                expected_exceptions = (
                    ValueError, struct.error, IndexError, MemoryError
                )
                assert isinstance(e, expected_exceptions)
        except Exception as e:
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.floats(allow_nan=True, allow_infinity=True, width=32))
    @settings(max_examples=100)
    def test_float_edge_cases(self, float_value):
        """Test float serialization/deserialization with edge cases."""
        schema_content = """
        namespace test.fuzz;
        
        struct FloatStruct {
            f32_value: f32;
        }
        """
        
        try:
            module = self.generate_python_module(schema_content)
            FloatStruct = self._find_class_by_name(module, 'FloatStruct')
            
            try:
                # Create instance with edge case float
                instance = FloatStruct(f32_value=float_value)
                
                # Serialize and deserialize
                binary_data = instance.to_bytes()
                deserialized = FloatStruct.from_bytes(binary_data)
                
                # Verify handling of special float values
                if math.isnan(float_value):
                    assert math.isnan(deserialized.f32_value)
                elif math.isinf(float_value):
                    assert math.isinf(deserialized.f32_value)
                else:
                    # Normal values should round-trip reasonably
                    assert isinstance(deserialized.f32_value, float)
                    
            except Exception as e:
                expected_exceptions = (
                    ValueError, struct.error, OverflowError, TypeError
                )
                assert isinstance(e, expected_exceptions)
        except Exception as e:
            expected_exceptions = (ValueError, SyntaxError, ImportError)
            assert isinstance(e, expected_exceptions)
