"""
Cross-platform binary compatibility tests.

This module tests binary format compatibility between different language
implementations (C, Rust, Python) to ensure data can be exchanged reliably.
"""

import pytest
import tempfile
import shutil
import struct
from pathlib import Path
from typing import Dict, List, Any, Tuple

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator


class TestCrossPlatformBinary:
    """Test binary format compatibility across platforms."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = None
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_dir(self) -> Path:
        """Create a temporary directory."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
        return Path(self.temp_dir)
    
    def create_schema_file(self, content: str, filename: str = "test.pico") -> Path:
        """Create a schema file."""
        temp_dir = self.create_temp_dir()
        schema_file = temp_dir / filename
        schema_file.write_text(content)
        return schema_file
    
    def generate_python_code(self, schema_file: Path) -> Path:
        """Generate Python code for the schema."""
        temp_dir = self.create_temp_dir()
        
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        python_dir = temp_dir / "python_generated"
        python_dir.mkdir(exist_ok=True)
        python_generator = PythonCodeGenerator(schema)
        python_files = python_generator.generate()
        for filename, content in python_files.items():
            (python_dir / filename).write_text(content)
        
        return python_dir
    
    def _find_class_by_name(self, module, class_name: str):
        """Find a class by name, handling namespace prefixes."""
        if hasattr(module, class_name):
            return getattr(module, class_name)
        else:
            # Try with namespace prefixes - look for classes that end with the class name
            # and are actual class types (not modules, functions, etc.)
            for attr_name in dir(module):
                if (attr_name.endswith(class_name) and 
                    not attr_name.startswith('_') and 
                    hasattr(module, attr_name)):
                    attr_obj = getattr(module, attr_name)
                    # Check if it's a class type (not a module or function)
                    if (isinstance(attr_obj, type) and 
                        hasattr(attr_obj, '__init__') and
                        not attr_name.endswith('Error') and  # Skip error classes
                        not attr_name.endswith('Base')):     # Skip base classes
                        return attr_obj
            raise AttributeError(f"Could not find class for {class_name}")
    
    def test_primitive_binary_format(self):
        """Test that primitive types follow the expected binary format."""
        schema_content = """
        namespace test.binary;
        
        struct PrimitiveBinary {
            u8_val: u8;
            u16_val: u16;
            u32_val: u32;
            u64_val: u64;
            i8_val: i8;
            i16_val: i16;
            i32_val: i32;
            i64_val: i64;
            f32_val: f32;
            f64_val: f64;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            PrimitiveBinary = self._find_class_by_name(generated_module, 'PrimitiveBinary')
            
            # Test known values
            test_instance = PrimitiveBinary(
                u8_val=0x42,
                u16_val=0x1234,
                u32_val=0x12345678,
                u64_val=0x123456789ABCDEF0,
                i8_val=-42,
                i16_val=-1234,
                i32_val=-123456789,
                i64_val=-1234567890123456789,
                f32_val=3.14159,
                f64_val=2.718281828459045
            )
            
            binary_data = test_instance.to_bytes()
            
            # Verify we can deserialize
            deserialized = PrimitiveBinary.from_bytes(binary_data)
            
            # Check exact values
            assert deserialized.u8_val == 0x42
            assert deserialized.u16_val == 0x1234
            assert deserialized.u32_val == 0x12345678
            assert deserialized.u64_val == 0x123456789ABCDEF0
            assert deserialized.i8_val == -42
            assert deserialized.i16_val == -1234
            assert deserialized.i32_val == -123456789
            assert deserialized.i64_val == -1234567890123456789
            assert abs(deserialized.f32_val - 3.14159) < 1e-6
            assert abs(deserialized.f64_val - 2.718281828459045) < 1e-15
            
            # Test that binary format is deterministic
            binary_data2 = test_instance.to_bytes()
            assert binary_data == binary_data2
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_string_binary_format(self):
        """Test string binary format (u16 length + UTF-8 bytes)."""
        schema_content = """
        namespace test.strings;
        
        struct StringBinary {
            short_str: string;
            empty_str: string;
            unicode_str: string;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            StringBinary = self._find_class_by_name(generated_module, 'StringBinary')
            
            test_instance = StringBinary(
                short_str="hello",
                empty_str="",
                unicode_str="🚀🌟"
            )
            
            binary_data = test_instance.to_bytes()
            
            # Manually verify string format
            # Each string should be: u16 length (little-endian) + UTF-8 bytes
            
            # "hello" = 5 bytes
            hello_bytes = "hello".encode('utf-8')
            assert len(hello_bytes) == 5
            
            # "" = 0 bytes
            empty_bytes = "".encode('utf-8')
            assert len(empty_bytes) == 0
            
            # "🚀🌟" = variable bytes (UTF-8 encoded)
            unicode_bytes = "🚀🌟".encode('utf-8')
            
            # Verify deserialization
            deserialized = StringBinary.from_bytes(binary_data)
            assert deserialized.short_str == "hello"
            assert deserialized.empty_str == ""
            assert deserialized.unicode_str == "🚀🌟"
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_array_binary_format(self):
        """Test array binary format (u16 count + elements)."""
        schema_content = """
        namespace test.arrays;
        
        struct ArrayBinary {
            u32_array: [u32];
            string_array: [string];
            empty_array: [u8];
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            ArrayBinary = self._find_class_by_name(generated_module, 'ArrayBinary')
            
            test_instance = ArrayBinary(
                u32_array=[1, 2, 3, 4],
                string_array=["a", "bb", "ccc"],
                empty_array=[]
            )
            
            binary_data = test_instance.to_bytes()
            
            # Verify deserialization
            deserialized = ArrayBinary.from_bytes(binary_data)
            assert deserialized.u32_array == [1, 2, 3, 4]
            assert deserialized.string_array == ["a", "bb", "ccc"]
            assert deserialized.empty_array == []
            
            # Test deterministic serialization
            binary_data2 = test_instance.to_bytes()
            assert binary_data == binary_data2
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_endianness_consistency(self):
        """Test that multi-byte values use consistent little-endian encoding."""
        schema_content = """
        namespace test.endian;
        
        struct EndiannessTest {
            u16_val: u16;
            u32_val: u32;
            u64_val: u64;
            i16_val: i16;
            i32_val: i32;
            i64_val: i64;
            f32_val: f32;
            f64_val: f64;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            EndiannessTest = self._find_class_by_name(generated_module, 'EndiannessTest')
            
            # Test specific values that would show endianness issues
            test_instance = EndiannessTest(
                u16_val=0x1234,      # Should be 0x34, 0x12 in little-endian
                u32_val=0x12345678,  # Should be 0x78, 0x56, 0x34, 0x12
                u64_val=0x123456789ABCDEF0,
                i16_val=-1,          # Should be 0xFF, 0xFF
                i32_val=-1,          # Should be 0xFF, 0xFF, 0xFF, 0xFF
                i64_val=-1,          # Should be all 0xFF bytes
                f32_val=1.0,         # IEEE 754 little-endian
                f64_val=1.0          # IEEE 754 little-endian
            )
            
            binary_data = test_instance.to_bytes()
            
            # Verify round-trip consistency
            deserialized = EndiannessTest.from_bytes(binary_data)
            assert deserialized.u16_val == 0x1234
            assert deserialized.u32_val == 0x12345678
            assert deserialized.u64_val == 0x123456789ABCDEF0
            assert deserialized.i16_val == -1
            assert deserialized.i32_val == -1
            assert deserialized.i64_val == -1
            assert abs(deserialized.f32_val - 1.0) < 1e-6
            assert abs(deserialized.f64_val - 1.0) < 1e-15
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_alignment_and_padding(self):
        """Test struct alignment and padding behavior."""
        schema_content = """
        namespace test.align;
        
        struct AlignmentTest {
            u8_field: u8;
            u32_field: u32;
            u8_field2: u8;
            u64_field: u64;
            u16_field: u16;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            AlignmentTest = self._find_class_by_name(generated_module, 'AlignmentTest')
            
            test_instance = AlignmentTest(
                u8_field=0x11,
                u32_field=0x22334455,
                u8_field2=0x66,
                u64_field=0x778899AABBCCDDEE,
                u16_field=0xFF00
            )
            
            binary_data = test_instance.to_bytes()
            
            # Verify round-trip
            deserialized = AlignmentTest.from_bytes(binary_data)
            assert deserialized.u8_field == 0x11
            assert deserialized.u32_field == 0x22334455
            assert deserialized.u8_field2 == 0x66
            assert deserialized.u64_field == 0x778899AABBCCDDEE
            assert deserialized.u16_field == 0xFF00
            
            # Test that serialization is deterministic
            binary_data2 = test_instance.to_bytes()
            assert binary_data == binary_data2
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_complex_mixed_data(self):
        """Test complex mixed data structures for binary compatibility."""
        schema_content = """
        namespace test.mixed;
        
        struct ComplexMixed {
            header: u32;
            name: string;
            values: [f64];
            flags: [u8];
            metadata: string;
            count: u16;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            ComplexMixed = self._find_class_by_name(generated_module, 'ComplexMixed')
            
            test_cases = [
                {
                    'name': 'empty_arrays',
                    'data': {
                        'header': 0x12345678,
                        'name': 'test',
                        'values': [],
                        'flags': [],
                        'metadata': '',
                        'count': 0
                    }
                },
                {
                    'name': 'filled_arrays',
                    'data': {
                        'header': 0xDEADBEEF,
                        'name': 'complex test',
                        'values': [1.1, 2.2, 3.3],
                        'flags': [0, 1, 255],
                        'metadata': 'some metadata',
                        'count': 42
                    }
                },
                {
                    'name': 'unicode_data',
                    'data': {
                        'header': 0x00000001,
                        'name': '测试 🚀',
                        'values': [3.14159, -2.71828],
                        'flags': [128, 64, 32],
                        'metadata': 'Unicode: ñ ü 中文',
                        'count': 65535
                    }
                }
            ]
            
            for test_case in test_cases:
                instance = ComplexMixed(**test_case['data'])
                binary_data = instance.to_bytes()
                deserialized = ComplexMixed.from_bytes(binary_data)
                
                # Verify all fields
                assert deserialized.header == test_case['data']['header']
                assert deserialized.name == test_case['data']['name']
                assert len(deserialized.values) == len(test_case['data']['values'])
                for orig, deser in zip(test_case['data']['values'], deserialized.values):
                    assert abs(orig - deser) < 1e-15
                assert deserialized.flags == test_case['data']['flags']
                assert deserialized.metadata == test_case['data']['metadata']
                assert deserialized.count == test_case['data']['count']
                
                # Test deterministic serialization
                binary_data2 = instance.to_bytes()
                assert binary_data == binary_data2
                
        finally:
            sys.path.remove(str(python_dir))
    
    def test_binary_size_consistency(self):
        """Test that binary sizes are consistent and predictable."""
        schema_content = """
        namespace test.sizes;
        
        struct SizeTest {
            fixed_u32: u32;
            fixed_f64: f64;
            var_string: string;
            var_array: [u16];
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            SizeTest = self._find_class_by_name(generated_module, 'SizeTest')
            
            # Test with known sizes
            test_cases = [
                {
                    'data': {
                        'fixed_u32': 42,
                        'fixed_f64': 3.14,
                        'var_string': '',
                        'var_array': []
                    },
                    'min_size': 4 + 8 + 2 + 2  # u32 + f64 + string_len + array_len
                },
                {
                    'data': {
                        'fixed_u32': 42,
                        'fixed_f64': 3.14,
                        'var_string': 'hello',  # 5 bytes
                        'var_array': [1, 2, 3]  # 3 * 2 bytes
                    },
                    'min_size': 4 + 8 + 2 + 5 + 2 + 6  # Fixed + string + array
                }
            ]
            
            for test_case in test_cases:
                instance = SizeTest(**test_case['data'])
                binary_data = instance.to_bytes()
                
                # Verify minimum size
                assert len(binary_data) >= test_case['min_size']
                
                # Verify round-trip
                deserialized = SizeTest.from_bytes(binary_data)
                assert deserialized.fixed_u32 == test_case['data']['fixed_u32']
                assert abs(deserialized.fixed_f64 - test_case['data']['fixed_f64']) < 1e-15
                assert deserialized.var_string == test_case['data']['var_string']
                assert deserialized.var_array == test_case['data']['var_array']
                
        finally:
            sys.path.remove(str(python_dir)) 
