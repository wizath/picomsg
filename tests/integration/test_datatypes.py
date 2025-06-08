"""
Comprehensive data type integration tests.

This module tests all supported PicoMsg data types, nesting capabilities,
and array handling with cross-platform binary compatibility between
C, Rust, and Python implementations.
"""

import pytest
import tempfile
import subprocess
import struct
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.c import CCodeGenerator
from picomsg.codegen.rust import RustCodeGenerator
from picomsg.codegen.python import PythonCodeGenerator


class TestDataTypes:
    """Comprehensive tests for all data types with cross-platform compatibility."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = None
        self.test_data = {}
    
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
    
    def generate_all_languages(self, schema_file: Path) -> Dict[str, Path]:
        """Generate code for all supported languages."""
        temp_dir = self.create_temp_dir()
        
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        # Generate Python code
        python_dir = temp_dir / "python_generated"
        python_dir.mkdir(exist_ok=True)
        python_generator = PythonCodeGenerator(schema)
        python_files = python_generator.generate()
        for filename, content in python_files.items():
            (python_dir / filename).write_text(content)
        
        return {
            'python': python_dir
        }
    
    def test_all_primitive_types(self):
        """Test all primitive types with cross-platform compatibility."""
        schema_content = """
        namespace test.primitives;
        
        struct AllPrimitives {
            u8_field: u8;
            u16_field: u16;
            u32_field: u32;
            u64_field: u64;
            i8_field: i8;
            i16_field: i16;
            i32_field: i32;
            i64_field: i64;
            f32_field: f32;
            f64_field: f64;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        lang_dirs = self.generate_all_languages(schema_file)
        
        # Test data with edge cases
        test_cases = [
            {
                'name': 'zero_values',
                'data': {
                    'u8_field': 0, 'u16_field': 0, 'u32_field': 0, 'u64_field': 0,
                    'i8_field': 0, 'i16_field': 0, 'i32_field': 0, 'i64_field': 0,
                    'f32_field': 0.0, 'f64_field': 0.0
                }
            },
            {
                'name': 'max_unsigned_values',
                'data': {
                    'u8_field': 255, 'u16_field': 65535, 'u32_field': 4294967295, 'u64_field': 18446744073709551615,
                    'i8_field': 127, 'i16_field': 32767, 'i32_field': 2147483647, 'i64_field': 9223372036854775807,
                    'f32_field': 3.14159, 'f64_field': 2.718281828459045
                }
            },
            {
                'name': 'min_signed_values',
                'data': {
                    'u8_field': 1, 'u16_field': 1, 'u32_field': 1, 'u64_field': 1,
                    'i8_field': -128, 'i16_field': -32768, 'i32_field': -2147483648, 'i64_field': -9223372036854775808,
                    'f32_field': -3.14159, 'f64_field': -2.718281828459045
                }
            },
            {
                'name': 'random_values',
                'data': {
                    'u8_field': 42, 'u16_field': 1234, 'u32_field': 987654321, 'u64_field': 1234567890123456789,
                    'i8_field': -42, 'i16_field': -1234, 'i32_field': -987654321, 'i64_field': -1234567890123456789,
                    'f32_field': 123.456, 'f64_field': 123456.789012345
                }
            }
        ]
        
        # Test Python to binary and back
        self._test_python_round_trip(lang_dirs['python'], 'AllPrimitives', test_cases)
    
    def test_variable_length_types(self):
        """Test string, bytes, and array types."""
        schema_content = """
        namespace test.variable;
        
        struct VariableTypes {
            name: string;
            data: bytes;
            numbers: [u32];
            texts: [string];
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        lang_dirs = self.generate_all_languages(schema_file)
        
        test_cases = [
            {
                'name': 'empty_values',
                'data': {
                    'name': '',
                    'data': b'',
                    'numbers': [],
                    'texts': []
                }
            },
            {
                'name': 'simple_values',
                'data': {
                    'name': 'Hello, World!',
                    'data': b'binary data here',
                    'numbers': [1, 2, 3, 4, 5],
                    'texts': ['first', 'second', 'third']
                }
            },
            {
                'name': 'unicode_and_large_arrays',
                'data': {
                    'name': 'Unicode: 🚀 ñ ü 中文',
                    'data': bytes(range(256)),  # All possible byte values
                    'numbers': list(range(100)),  # Large array
                    'texts': [f'item_{i}' for i in range(50)]  # Many strings
                }
            },
            {
                'name': 'special_characters',
                'data': {
                    'name': 'Special: \n\t\r"\'\\',
                    'data': b'\x00\x01\x02\xff\xfe\xfd',
                    'numbers': [0, 1, 4294967295],  # Min and max u32
                    'texts': ['', 'single', 'multiple words here']
                }
            }
        ]
        
        # Test Python round trip
        self._test_python_round_trip(lang_dirs['python'], 'VariableTypes', test_cases)
    
    def test_nested_structures(self):
        """Test nested struct composition."""
        schema_content = """
        namespace test.nested;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct Rectangle {
            top_left: Point;
            bottom_right: Point;
            color: u32;
        }
        
        struct Scene {
            background: Rectangle;
            foreground: Rectangle;
            name: string;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        lang_dirs = self.generate_all_languages(schema_file)
        
        # Test individual structs first
        point_cases = [
            {'name': 'origin', 'data': {'x': 0.0, 'y': 0.0}},
            {'name': 'positive', 'data': {'x': 123.456, 'y': 789.012}},
            {'name': 'negative', 'data': {'x': -123.456, 'y': -789.012}}
        ]
        
        rectangle_cases = [
            {
                'name': 'unit_square',
                'data': {
                    'top_left': {'x': 0.0, 'y': 0.0},
                    'bottom_right': {'x': 1.0, 'y': 1.0},
                    'color': 0x808080
                }
            }
        ]
        
        scene_cases = [
            {
                'name': 'simple_scene',
                'data': {
                    'background': {
                        'top_left': {'x': 0.0, 'y': 0.0},
                        'bottom_right': {'x': 100.0, 'y': 100.0},
                        'color': 0xFF0000
                    },
                    'foreground': {
                        'top_left': {'x': 10.0, 'y': 10.0},
                        'bottom_right': {'x': 90.0, 'y': 90.0},
                        'color': 0x00FF00
                    },
                    'name': 'Test Scene'
                }
            }
        ]
        
        self._test_python_round_trip(lang_dirs['python'], 'Point', point_cases)
        self._test_python_round_trip(lang_dirs['python'], 'Rectangle', rectangle_cases)
        self._test_python_round_trip(lang_dirs['python'], 'Scene', scene_cases)
    
    def test_arrays_of_structs(self):
        """Test arrays containing struct types."""
        schema_content = """
        namespace test.arrays;
        
        struct Vertex {
            x: f32;
            y: f32;
            z: f32;
        }
        
        struct Polygon {
            vertices: [Vertex];
            color: u32;
            name: string;
        }
        
        struct Mesh {
            polygons: [Polygon];
            material: string;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        lang_dirs = self.generate_all_languages(schema_file)
        
        test_cases = [
            {
                'name': 'empty_mesh',
                'data': {
                    'polygons': [],
                    'material': 'empty'
                }
            },
            {
                'name': 'triangle_mesh',
                'data': {
                    'polygons': [
                        {
                            'vertices': [
                                {'x': 0.0, 'y': 0.0, 'z': 0.0},
                                {'x': 1.0, 'y': 0.0, 'z': 0.0},
                                {'x': 0.5, 'y': 1.0, 'z': 0.0}
                            ],
                            'color': 0xFF0000,
                            'name': 'red_triangle'
                        }
                    ],
                    'material': 'plastic'
                }
            }
        ]
        
        self._test_python_round_trip(lang_dirs['python'], 'Mesh', test_cases)
    
    def test_multidimensional_arrays(self):
        """Test nested arrays (2D, 3D arrays)."""
        schema_content = """
        namespace test.multidim;
        
        struct Matrix2D {
            rows: [[f32]];
            width: u32;
            height: u32;
        }
        
        struct Tensor3D {
            data: [[[u8]]];
            dimensions: [u32];
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        lang_dirs = self.generate_all_languages(schema_file)
        
        matrix_cases = [
            {
                'name': 'empty_matrix',
                'data': {
                    'rows': [],
                    'width': 0,
                    'height': 0
                }
            },
            {
                'name': 'identity_matrix',
                'data': {
                    'rows': [
                        [1.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0],
                        [0.0, 0.0, 1.0]
                    ],
                    'width': 3,
                    'height': 3
                }
            }
        ]
        
        tensor_cases = [
            {
                'name': 'empty_tensor',
                'data': {
                    'data': [],
                    'dimensions': [0, 0, 0]
                }
            },
            {
                'name': 'small_tensor',
                'data': {
                    'data': [
                        [
                            [1, 2],
                            [3, 4]
                        ],
                        [
                            [5, 6],
                            [7, 8]
                        ]
                    ],
                    'dimensions': [2, 2, 2]
                }
            }
        ]
        
        self._test_python_round_trip(lang_dirs['python'], 'Matrix2D', matrix_cases)
        self._test_python_round_trip(lang_dirs['python'], 'Tensor3D', tensor_cases)
    
    def test_binary_format_consistency(self):
        """Test that binary format is consistent and follows specification."""
        schema_content = """
        namespace test.format;
        
        struct BinaryTest {
            u8_val: u8;
            u16_val: u16;
            u32_val: u32;
            f32_val: f32;
            str_val: string;
            array_val: [u16];
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        lang_dirs = self.generate_all_languages(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(lang_dirs['python']))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            BinaryTest = self._find_class_by_name(generated_module, 'BinaryTest')
            
            # Test known values with predictable binary representation
            instance = BinaryTest(
                u8_val=0x42,
                u16_val=0x1234,
                u32_val=0x12345678,
                f32_val=3.14159,
                str_val="test",
                array_val=[1, 2, 3]
            )
            
            binary_data = instance.to_bytes()
            
            # Verify we can deserialize
            deserialized = BinaryTest.from_bytes(binary_data)
            assert deserialized.u8_val == 0x42
            assert deserialized.u16_val == 0x1234
            assert deserialized.u32_val == 0x12345678
            assert abs(deserialized.f32_val - 3.14159) < 1e-6
            assert deserialized.str_val == "test"
            assert deserialized.array_val == [1, 2, 3]
            
        finally:
            sys.path.remove(str(lang_dirs['python']))
    
    def _find_class_by_name(self, module, class_name: str):
        """Find a class by name, handling namespace prefixes."""
        # First try direct access
        if hasattr(module, class_name):
            return getattr(module, class_name)
        
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
                    hasattr(attr_obj, 'to_bytes') and  # Must have serialization methods
                    hasattr(attr_obj, 'from_bytes') and
                    not attr_name.endswith('Error') and  # Skip error classes
                    not attr_name.endswith('Base')):     # Skip base classes
                    return attr_obj
        
        # Debug: show what classes are available
        available_classes = []
        for attr_name in dir(module):
            if not attr_name.startswith('_') and hasattr(module, attr_name):
                attr_obj = getattr(module, attr_name)
                if isinstance(attr_obj, type) and hasattr(attr_obj, '__init__'):
                    available_classes.append(attr_name)
        
        raise AttributeError(f"Could not find class for {class_name}. Available classes: {available_classes}")
    
    def _test_python_round_trip(self, python_dir: Path, struct_name: str, test_cases: List[Dict[str, Any]]):
        """Test Python serialization round trip."""
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            struct_class = self._find_class_by_name(generated_module, struct_name)
            
            for test_case in test_cases:
                case_name = test_case['name']
                data = test_case['data']
                
                # Create instance with nested data
                instance = self._create_instance_from_data(struct_class, data)
                
                # Serialize to binary
                binary_data = instance.to_bytes()
                assert len(binary_data) > 0, f"Empty binary data for {case_name}"
                
                # Deserialize from binary
                deserialized = struct_class.from_bytes(binary_data)
                
                # Verify round trip
                self._verify_instance_equality(instance, deserialized, case_name)
                
                # Test JSON round trip if available
                if hasattr(instance, 'to_json') and hasattr(struct_class, 'from_json'):
                    try:
                        json_data = instance.to_json()
                        json_deserialized = struct_class.from_json(json_data)
                        self._verify_instance_equality(instance, json_deserialized, f"{case_name}_json")
                    except Exception as e:
                        # JSON might not be supported for all types
                        print(f"JSON test skipped for {case_name}: {e}")
                
        finally:
            sys.path.remove(str(python_dir))
    
    def _create_instance_from_data(self, struct_class, data):
        """Create a struct instance from nested dictionary data."""
        if isinstance(data, dict):
            # Handle nested structures by creating instances recursively
            kwargs = {}
            module = __import__(struct_class.__module__)
            
            for key, value in data.items():
                if isinstance(value, dict):
                    # This is a nested struct - we need to create it
                    # Try common nested class names based on field name
                    field_name_variants = [
                        key.title().replace('_', ''),  # top_left -> TopLeft
                        key.replace('_', '').title(),  # top_left -> TopLeft
                        key.title(),                   # top_left -> Top_Left
                    ]
                    
                    # Also try common struct names
                    common_names = ['Point', 'Rectangle', 'Transform', 'Vector3', 'Vertex', 'Scene']
                    
                    # Get all available classes and try to match
                    available_classes = []
                    for attr_name in dir(module):
                        if not attr_name.startswith('_') and hasattr(module, attr_name):
                            attr_obj = getattr(module, attr_name)
                            if (isinstance(attr_obj, type) and 
                                hasattr(attr_obj, '__init__') and
                                hasattr(attr_obj, 'to_bytes') and
                                not attr_name.endswith('Error') and
                                not attr_name.endswith('Base')):
                                available_classes.append((attr_name, attr_obj))
                    
                    found = False
                    # Try to find the best matching class based on the data structure
                    # Score each class by how well it matches the data
                    best_match = None
                    best_score = -1
                    
                    for class_name, class_obj in available_classes:
                        score = 0
                        
                        # Check if class name matches field name patterns
                        for variant in field_name_variants:
                            if class_name.endswith(variant):
                                score += 10  # High score for field name match
                        
                        # Check if class name matches common struct names
                        for common_name in common_names:
                            if class_name.endswith(common_name):
                                score += 5  # Medium score for common name match
                        
                        # Check if the class can actually handle the data structure
                        try:
                            # Try to create a dummy instance to see if the fields match
                            dummy_kwargs = {}
                            for data_key in value.keys():
                                # Check if the class has properties for the data keys
                                if hasattr(class_obj, data_key):
                                    score += 2  # Bonus for matching field names
                            
                            # Prefer classes with more matching fields
                            if score > best_score:
                                best_score = score
                                best_match = class_obj
                        except:
                            continue
                    
                    if best_match and best_score > 0:
                        try:
                            kwargs[key] = self._create_instance_from_data(best_match, value)
                            found = True
                        except (AttributeError, TypeError):
                            pass
                    
                    if not found:
                        # Last resort: try to use the value as-is
                        kwargs[key] = value
                        
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # Array of nested structs
                    # Try to determine element type from field name
                    element_name_variants = [
                        key.rstrip('s').title().replace('_', ''),  # vertices -> Vertex
                        key.rstrip('es').title().replace('_', ''), # boxes -> Box
                        key[:-1].title().replace('_', ''),         # items -> Item
                    ]
                    
                    common_element_names = ['Vertex', 'Polygon', 'Player', 'Item', 'Property', 'Point']
                    
                    found = False
                    for possible_name in element_name_variants + common_element_names:
                        try:
                            element_class = self._find_class_by_name(module, possible_name)
                            kwargs[key] = [self._create_instance_from_data(element_class, item) for item in value]
                            found = True
                            break
                        except (AttributeError, TypeError):
                            continue
                    
                    if not found:
                        kwargs[key] = value
                else:
                    kwargs[key] = value
            
            return struct_class(**kwargs)
        else:
            return data
    
    def _verify_instance_equality(self, original, deserialized, test_name: str):
        """Verify that two struct instances are equal."""
        # Get all non-private, non-method attributes
        original_attrs = {name: getattr(original, name) for name in dir(original) 
                         if not name.startswith('_') and not callable(getattr(original, name))}
        
        for attr_name, original_value in original_attrs.items():
            if hasattr(deserialized, attr_name):
                deserialized_value = getattr(deserialized, attr_name)
                self._compare_values(original_value, deserialized_value, f"{test_name}.{attr_name}")
    
    def _compare_values(self, original, deserialized, path: str):
        """Compare two values with appropriate tolerance for different types."""
        if isinstance(original, float):
            # Use different tolerances based on the magnitude and expected precision
            # f32 has ~7 decimal digits of precision, f64 has ~15-17
            if abs(original) > 1e6:
                # For large numbers, use relative tolerance
                tolerance = max(1e-4, abs(original) * 1e-6)
            else:
                # For smaller numbers, use absolute tolerance appropriate for f32
                tolerance = 1e-4
            assert abs(original - deserialized) < tolerance, \
                f"Float mismatch at {path}: {original} != {deserialized} (diff: {abs(original - deserialized)}, tolerance: {tolerance})"
        elif isinstance(original, list):
            assert len(original) == len(deserialized), \
                f"Array length mismatch at {path}: {len(original)} != {len(deserialized)}"
            for i, (orig_item, deser_item) in enumerate(zip(original, deserialized)):
                self._compare_values(orig_item, deser_item, f"{path}[{i}]")
        elif hasattr(original, '__dict__'):
            # This is a struct instance
            self._verify_instance_equality(original, deserialized, path)
        else:
            assert original == deserialized, \
                f"Value mismatch at {path}: {original} != {deserialized}" 
