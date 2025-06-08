"""
Edge cases and boundary condition tests for PicoMsg data types.

This module tests edge cases, boundary conditions, and error handling
for all supported data types.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator


class TestDataTypeEdgeCases:
    """Test edge cases and boundary conditions for all data types."""
    
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
    
    def test_primitive_type_boundaries(self):
        """Test boundary values for all primitive types."""
        schema_content = """
        namespace test.boundaries;
        
        struct PrimitiveBoundaries {
            u8_min: u8;
            u8_max: u8;
            u16_min: u16;
            u16_max: u16;
            u32_min: u32;
            u32_max: u32;
            u64_min: u64;
            u64_max: u64;
            i8_min: i8;
            i8_max: i8;
            i16_min: i16;
            i16_max: i16;
            i32_min: i32;
            i32_max: i32;
            i64_min: i64;
            i64_max: i64;
            f32_zero: f32;
            f32_small: f32;
            f32_large: f32;
            f64_zero: f64;
            f64_small: f64;
            f64_large: f64;
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
            PrimitiveBoundaries = self._find_class_by_name(generated_module, 'PrimitiveBoundaries')
            
            # Test boundary values
            boundary_instance = PrimitiveBoundaries(
                u8_min=0, u8_max=255,
                u16_min=0, u16_max=65535,
                u32_min=0, u32_max=4294967295,
                u64_min=0, u64_max=18446744073709551615,
                i8_min=-128, i8_max=127,
                i16_min=-32768, i16_max=32767,
                i32_min=-2147483648, i32_max=2147483647,
                i64_min=-9223372036854775808, i64_max=9223372036854775807,
                f32_zero=0.0, f32_small=1e-38, f32_large=3.4e38,
                f64_zero=0.0, f64_small=1e-308, f64_large=1.7e308
            )
            
            # Test serialization and deserialization
            binary_data = boundary_instance.to_bytes()
            deserialized = PrimitiveBoundaries.from_bytes(binary_data)
            
            # Verify all values
            assert deserialized.u8_min == 0
            assert deserialized.u8_max == 255
            assert deserialized.u16_min == 0
            assert deserialized.u16_max == 65535
            assert deserialized.u32_min == 0
            assert deserialized.u32_max == 4294967295
            assert deserialized.u64_min == 0
            assert deserialized.u64_max == 18446744073709551615
            assert deserialized.i8_min == -128
            assert deserialized.i8_max == 127
            assert deserialized.i16_min == -32768
            assert deserialized.i16_max == 32767
            assert deserialized.i32_min == -2147483648
            assert deserialized.i32_max == 2147483647
            assert deserialized.i64_min == -9223372036854775808
            assert deserialized.i64_max == 9223372036854775807
            
            # Float comparisons with tolerance
            assert abs(deserialized.f32_zero - 0.0) < 1e-6
            assert abs(deserialized.f32_small - 1e-38) < 1e-39
            assert abs(deserialized.f32_large - 3.4e38) < 1e37
            assert abs(deserialized.f64_zero - 0.0) < 1e-15
            assert abs(deserialized.f64_small - 1e-308) < 1e-309
            assert abs(deserialized.f64_large - 1.7e308) < 1e307
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_string_edge_cases(self):
        """Test edge cases for string types."""
        schema_content = """
        namespace test.strings;
        
        struct StringEdgeCases {
            empty_string: string;
            single_char: string;
            unicode_string: string;
            long_string: string;
            special_chars: string;
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
            StringEdgeCases = self._find_class_by_name(generated_module, 'StringEdgeCases')
            
            # Create a long string (but within u16 limit)
            long_string = 'A' * 1000
            
            test_cases = [
                {
                    'name': 'empty_and_special',
                    'data': {
                        'empty_string': '',
                        'single_char': 'A',
                        'unicode_string': '🚀🌟💫',
                        'long_string': long_string,
                        'special_chars': '\n\t\r"\'\\/'
                    }
                },
                {
                    'name': 'unicode_variety',
                    'data': {
                        'empty_string': '',
                        'single_char': '中',
                        'unicode_string': 'Hello, 世界! 🌍',
                        'long_string': 'ñ' * 500,
                        'special_chars': '\x00\x01\x02\x7F'
                    }
                }
            ]
            
            for test_case in test_cases:
                instance = StringEdgeCases(**test_case['data'])
                binary_data = instance.to_bytes()
                deserialized = StringEdgeCases.from_bytes(binary_data)
                
                assert deserialized.empty_string == test_case['data']['empty_string']
                assert deserialized.single_char == test_case['data']['single_char']
                assert deserialized.unicode_string == test_case['data']['unicode_string']
                assert deserialized.long_string == test_case['data']['long_string']
                assert deserialized.special_chars == test_case['data']['special_chars']
                
        finally:
            sys.path.remove(str(python_dir))
    
    def test_bytes_edge_cases(self):
        """Test edge cases for bytes types."""
        schema_content = """
        namespace test.bytes;
        
        struct BytesEdgeCases {
            empty_bytes: bytes;
            single_byte: bytes;
            all_values: bytes;
            large_bytes: bytes;
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
            BytesEdgeCases = self._find_class_by_name(generated_module, 'BytesEdgeCases')
            
            test_cases = [
                {
                    'name': 'various_bytes',
                    'data': {
                        'empty_bytes': b'',
                        'single_byte': b'\x42',
                        'all_values': bytes(range(256)),  # All possible byte values
                        'large_bytes': b'\xAA' * 1000  # Large but within u16 limit
                    }
                },
                {
                    'name': 'special_patterns',
                    'data': {
                        'empty_bytes': b'',
                        'single_byte': b'\x00',
                        'all_values': b'\x00\x01\x02\xFD\xFE\xFF',
                        'large_bytes': bytes(range(256)) * 2  # 512 bytes
                    }
                }
            ]
            
            for test_case in test_cases:
                instance = BytesEdgeCases(**test_case['data'])
                binary_data = instance.to_bytes()
                deserialized = BytesEdgeCases.from_bytes(binary_data)
                
                assert deserialized.empty_bytes == test_case['data']['empty_bytes']
                assert deserialized.single_byte == test_case['data']['single_byte']
                assert deserialized.all_values == test_case['data']['all_values']
                assert deserialized.large_bytes == test_case['data']['large_bytes']
                
        finally:
            sys.path.remove(str(python_dir))
    
    def test_array_edge_cases(self):
        """Test edge cases for array types."""
        schema_content = """
        namespace test.arrays;
        
        struct ArrayEdgeCases {
            empty_u8: [u8];
            empty_string: [string];
            single_element: [u32];
            large_array: [u16];
            nested_empty: [[u8]];
            nested_mixed: [[string]];
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
            ArrayEdgeCases = self._find_class_by_name(generated_module, 'ArrayEdgeCases')
            
            test_cases = [
                {
                    'name': 'empty_arrays',
                    'data': {
                        'empty_u8': [],
                        'empty_string': [],
                        'single_element': [42],
                        'large_array': list(range(1000)),
                        'nested_empty': [],
                        'nested_mixed': []
                    }
                },
                {
                    'name': 'nested_arrays',
                    'data': {
                        'empty_u8': [0, 255],
                        'empty_string': ['', 'hello', ''],
                        'single_element': [4294967295],
                        'large_array': [0, 1, 65535] * 100,
                        'nested_empty': [[], [1, 2, 3], []],
                        'nested_mixed': [[], ['a'], ['b', 'c'], []]
                    }
                }
            ]
            
            for test_case in test_cases:
                instance = ArrayEdgeCases(**test_case['data'])
                binary_data = instance.to_bytes()
                deserialized = ArrayEdgeCases.from_bytes(binary_data)
                
                assert deserialized.empty_u8 == test_case['data']['empty_u8']
                assert deserialized.empty_string == test_case['data']['empty_string']
                assert deserialized.single_element == test_case['data']['single_element']
                assert deserialized.large_array == test_case['data']['large_array']
                assert deserialized.nested_empty == test_case['data']['nested_empty']
                assert deserialized.nested_mixed == test_case['data']['nested_mixed']
                
        finally:
            sys.path.remove(str(python_dir))
    
    def test_deeply_nested_structures(self):
        """Test deeply nested structure edge cases."""
        schema_content = """
        namespace test.deep;
        
        struct Level1 {
            value: u32;
            name: string;
        }
        
        struct Level2 {
            level1: Level1;
            array1: [Level1];
        }
        
        struct Level3 {
            level2: Level2;
            array2: [Level2];
        }
        
        struct Level4 {
            level3: Level3;
            array3: [Level3];
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
            Level1 = self._find_class_by_name(generated_module, 'Level1')
            Level2 = self._find_class_by_name(generated_module, 'Level2')
            Level3 = self._find_class_by_name(generated_module, 'Level3')
            Level4 = self._find_class_by_name(generated_module, 'Level4')
            
            # Create deeply nested structure
            level1_instances = [
                Level1(value=1, name="first"),
                Level1(value=2, name="second")
            ]
            
            level2_instances = [
                Level2(
                    level1=Level1(value=10, name="nested"),
                    array1=level1_instances
                )
            ]
            
            level3_instance = Level3(
                level2=Level2(
                    level1=Level1(value=100, name="deep"),
                    array1=[Level1(value=101, name="deep_array")]
                ),
                array2=level2_instances
            )
            
            level4_instance = Level4(
                level3=level3_instance,
                array3=[level3_instance]
            )
            
            # Test serialization and deserialization
            binary_data = level4_instance.to_bytes()
            deserialized = Level4.from_bytes(binary_data)
            
            # Verify deep structure
            assert deserialized.level3.level2.level1.value == 100
            assert deserialized.level3.level2.level1.name == "deep"
            assert len(deserialized.level3.array2) == 1
            assert deserialized.level3.array2[0].level1.value == 10
            assert len(deserialized.array3) == 1
            assert deserialized.array3[0].level2.level1.value == 100
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_large_data_structures(self):
        """Test handling of large data structures."""
        schema_content = """
        namespace test.large;
        
        struct LargeStruct {
            big_string: string;
            big_bytes: bytes;
            big_array: [u32];
            string_array: [string];
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
            LargeStruct = self._find_class_by_name(generated_module, 'LargeStruct')
            
            # Create large data (but within reasonable limits)
            large_instance = LargeStruct(
                big_string='X' * 5000,  # 5KB string
                big_bytes=bytes(range(256)) * 20,  # 5KB bytes
                big_array=list(range(1000)),  # 1000 u32 values
                string_array=[f'item_{i}' for i in range(500)]  # 500 strings
            )
            
            # Test serialization
            binary_data = large_instance.to_bytes()
            assert len(binary_data) > 10000  # Should be substantial
            
            # Test deserialization
            deserialized = LargeStruct.from_bytes(binary_data)
            
            assert len(deserialized.big_string) == 5000
            assert deserialized.big_string == 'X' * 5000
            assert len(deserialized.big_bytes) == 5120
            assert deserialized.big_bytes == bytes(range(256)) * 20
            assert len(deserialized.big_array) == 1000
            assert deserialized.big_array == list(range(1000))
            assert len(deserialized.string_array) == 500
            assert deserialized.string_array[0] == 'item_0'
            assert deserialized.string_array[499] == 'item_499'
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_special_float_values(self):
        """Test special floating point values."""
        schema_content = """
        namespace test.floats;
        
        struct FloatSpecials {
            f32_zero: f32;
            f32_neg_zero: f32;
            f32_small: f32;
            f32_large: f32;
            f64_zero: f64;
            f64_neg_zero: f64;
            f64_small: f64;
            f64_large: f64;
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
            FloatSpecials = self._find_class_by_name(generated_module, 'FloatSpecials')
            
            # Test special float values
            special_instance = FloatSpecials(
                f32_zero=0.0,
                f32_neg_zero=-0.0,
                f32_small=1e-38,
                f32_large=3.4e38,
                f64_zero=0.0,
                f64_neg_zero=-0.0,
                f64_small=1e-308,
                f64_large=1.7e308
            )
            
            binary_data = special_instance.to_bytes()
            deserialized = FloatSpecials.from_bytes(binary_data)
            
            # Verify float values (with appropriate tolerance)
            assert abs(deserialized.f32_zero - 0.0) < 1e-10
            assert abs(deserialized.f32_neg_zero - (-0.0)) < 1e-10
            assert abs(deserialized.f32_small - 1e-38) < 1e-39
            assert abs(deserialized.f32_large - 3.4e38) < 1e37
            assert abs(deserialized.f64_zero - 0.0) < 1e-15
            assert abs(deserialized.f64_neg_zero - (-0.0)) < 1e-15
            assert abs(deserialized.f64_small - 1e-308) < 1e-309
            assert abs(deserialized.f64_large - 1.7e308) < 1e307
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_mixed_complexity_scenario(self):
        """Test a complex scenario mixing all edge cases."""
        schema_content = """
        namespace test.complex;
        
        struct ComplexEdgeCase {
            primitives: [u64];
            strings: [string];
            bytes_data: [bytes];
            nested_arrays: [[[u8]]];
            mixed_content: string;
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
            ComplexEdgeCase = self._find_class_by_name(generated_module, 'ComplexEdgeCase')
            
            # Create complex edge case data
            complex_instance = ComplexEdgeCase(
                primitives=[0, 18446744073709551615, 1234567890],  # Min, max, random u64
                strings=['', 'short', 'A' * 100, '🚀🌟💫', '\n\t\r'],  # Various string types
                bytes_data=[b'', b'\x00', bytes(range(256)), b'\xFF' * 50],  # Various byte arrays
                nested_arrays=[
                    [],  # Empty 2D array
                    [[]],  # Array with empty array
                    [[1, 2, 3], [4, 5], []],  # Mixed content
                    [[255] * 10, [0] * 5]  # Repeated values
                ],
                mixed_content='Complex: 🌍 with "quotes" and \n newlines \t tabs'
            )
            
            # Test serialization and deserialization
            binary_data = complex_instance.to_bytes()
            deserialized = ComplexEdgeCase.from_bytes(binary_data)
            
            # Verify all complex data
            assert deserialized.primitives == [0, 18446744073709551615, 1234567890]
            assert deserialized.strings == ['', 'short', 'A' * 100, '🚀🌟💫', '\n\t\r']
            assert deserialized.bytes_data == [b'', b'\x00', bytes(range(256)), b'\xFF' * 50]
            assert deserialized.nested_arrays == [
                [],
                [[]],
                [[1, 2, 3], [4, 5], []],
                [[255] * 10, [0] * 5]
            ]
            assert deserialized.mixed_content == 'Complex: 🌍 with "quotes" and \n newlines \t tabs'
            
        finally:
            sys.path.remove(str(python_dir)) 
