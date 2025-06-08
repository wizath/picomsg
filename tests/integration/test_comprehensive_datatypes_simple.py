"""
Data type integration tests (simplified version).

This module tests data types that are currently fully supported by the
Python generator, focusing on primitive types and basic struct composition.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator


class TestDataTypesSimple:
    """Tests for supported data types with cross-platform compatibility."""
    
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
    
    def test_all_primitive_types(self):
        """Test all primitive types with boundary values."""
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
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module to avoid conflicts between tests
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            AllPrimitives = self._find_class_by_name(generated_module, 'AllPrimitives')
            
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
            
            for test_case in test_cases:
                case_name = test_case['name']
                data = test_case['data']
                
                # Create instance
                instance = AllPrimitives(**data)
                
                # Serialize to binary
                binary_data = instance.to_bytes()
                assert len(binary_data) > 0, f"Empty binary data for {case_name}"
                
                # Deserialize from binary
                deserialized = AllPrimitives.from_bytes(binary_data)
                
                # Verify all primitive fields
                for field_name, expected_value in data.items():
                    actual_value = getattr(deserialized, field_name)
                    if isinstance(expected_value, float):
                        # Use different tolerances for f32 vs f64
                        if field_name.endswith('f32_field'):
                            tolerance = 1e-5  # f32 has less precision
                        else:
                            tolerance = 1e-12  # f64 has more precision
                        assert abs(actual_value - expected_value) < tolerance, \
                            f"Float mismatch in {case_name}.{field_name}: {expected_value} != {actual_value}"
                    else:
                        assert actual_value == expected_value, \
                            f"Value mismatch in {case_name}.{field_name}: {expected_value} != {actual_value}"
                
        finally:
            sys.path.remove(str(python_dir))
    
    def test_nested_primitive_structures(self):
        """Test nested struct composition with only primitive types."""
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
        
        struct Dimensions {
            width: f32;
            height: f32;
            depth: f32;
        }
        
        struct Box {
            position: Point;
            size: Dimensions;
            material_id: u16;
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
            Point = self._find_class_by_name(generated_module, 'Point')
            Rectangle = self._find_class_by_name(generated_module, 'Rectangle')
            Dimensions = self._find_class_by_name(generated_module, 'Dimensions')
            Box = self._find_class_by_name(generated_module, 'Box')
            
            # Test individual Point
            point = Point(x=1.5, y=2.5)
            point_binary = point.to_bytes()
            point_deserialized = Point.from_bytes(point_binary)
            assert abs(point_deserialized.x - 1.5) < 1e-5  # f32 tolerance
            assert abs(point_deserialized.y - 2.5) < 1e-5  # f32 tolerance
            
            # Test Rectangle with nested Points
            rectangle = Rectangle(
                top_left=Point(x=0.0, y=0.0),
                bottom_right=Point(x=10.0, y=10.0),
                color=0xFF0000
            )
            
            rect_binary = rectangle.to_bytes()
            rect_deserialized = Rectangle.from_bytes(rect_binary)
            
            assert abs(rect_deserialized.top_left.x - 0.0) < 1e-5  # f32 tolerance
            assert abs(rect_deserialized.top_left.y - 0.0) < 1e-5  # f32 tolerance
            assert abs(rect_deserialized.bottom_right.x - 10.0) < 1e-5  # f32 tolerance
            assert abs(rect_deserialized.bottom_right.y - 10.0) < 1e-5  # f32 tolerance
            assert rect_deserialized.color == 0xFF0000
            
            # Test Box with multiple nested structs
            box = Box(
                position=Point(x=5.0, y=3.0),
                size=Dimensions(width=2.0, height=1.5, depth=0.8),
                material_id=42
            )
            
            box_binary = box.to_bytes()
            box_deserialized = Box.from_bytes(box_binary)
            
            assert abs(box_deserialized.position.x - 5.0) < 1e-5  # f32 tolerance
            assert abs(box_deserialized.position.y - 3.0) < 1e-5  # f32 tolerance
            assert abs(box_deserialized.size.width - 2.0) < 1e-5  # f32 tolerance
            assert abs(box_deserialized.size.height - 1.5) < 1e-5  # f32 tolerance
            assert abs(box_deserialized.size.depth - 0.8) < 1e-5  # f32 tolerance
            assert box_deserialized.material_id == 42
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_binary_format_consistency(self):
        """Test that binary format is consistent and deterministic."""
        schema_content = """
        namespace test.format;
        
        struct BinaryTest {
            u8_val: u8;
            u16_val: u16;
            u32_val: u32;
            f32_val: f32;
            u64_val: u64;
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
            BinaryTest = self._find_class_by_name(generated_module, 'BinaryTest')
            
            # Test known values with predictable binary representation
            instance = BinaryTest(
                u8_val=0x42,
                u16_val=0x1234,
                u32_val=0x12345678,
                f32_val=3.14159,
                u64_val=0x123456789ABCDEF0
            )
            
            binary_data = instance.to_bytes()
            
            # Verify we can deserialize
            deserialized = BinaryTest.from_bytes(binary_data)
            assert deserialized.u8_val == 0x42
            assert deserialized.u16_val == 0x1234
            assert deserialized.u32_val == 0x12345678
            assert abs(deserialized.f32_val - 3.14159) < 1e-6
            assert deserialized.u64_val == 0x123456789ABCDEF0
            
            # Test that binary format is deterministic
            binary_data2 = instance.to_bytes()
            assert binary_data == binary_data2
            
            # Test that different instances with same data produce same binary
            instance2 = BinaryTest(
                u8_val=0x42,
                u16_val=0x1234,
                u32_val=0x12345678,
                f32_val=3.14159,
                u64_val=0x123456789ABCDEF0
            )
            binary_data3 = instance2.to_bytes()
            assert binary_data == binary_data3
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_endianness_and_alignment(self):
        """Test endianness consistency and struct alignment."""
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
            EndiannessTest = self._find_class_by_name(generated_module, 'EndiannessTest')
            AlignmentTest = self._find_class_by_name(generated_module, 'AlignmentTest')
            
            # Test endianness with specific values that would show byte order issues
            endian_test = EndiannessTest(
                u16_val=0x1234,      # Should be 0x34, 0x12 in little-endian
                u32_val=0x12345678,  # Should be 0x78, 0x56, 0x34, 0x12
                u64_val=0x123456789ABCDEF0,
                i16_val=-1,          # Should be 0xFF, 0xFF
                i32_val=-1,          # Should be 0xFF, 0xFF, 0xFF, 0xFF
                i64_val=-1,          # Should be all 0xFF bytes
                f32_val=1.0,         # IEEE 754 little-endian
                f64_val=1.0          # IEEE 754 little-endian
            )
            
            endian_binary = endian_test.to_bytes()
            endian_deserialized = EndiannessTest.from_bytes(endian_binary)
            
            assert endian_deserialized.u16_val == 0x1234
            assert endian_deserialized.u32_val == 0x12345678
            assert endian_deserialized.u64_val == 0x123456789ABCDEF0
            assert endian_deserialized.i16_val == -1
            assert endian_deserialized.i32_val == -1
            assert endian_deserialized.i64_val == -1
            assert abs(endian_deserialized.f32_val - 1.0) < 1e-6
            assert abs(endian_deserialized.f64_val - 1.0) < 1e-15
            
            # Test struct alignment and padding
            align_test = AlignmentTest(
                u8_field=0x11,
                u32_field=0x22334455,
                u8_field2=0x66,
                u64_field=0x778899AABBCCDDEE,
                u16_field=0xFF00
            )
            
            align_binary = align_test.to_bytes()
            align_deserialized = AlignmentTest.from_bytes(align_binary)
            
            assert align_deserialized.u8_field == 0x11
            assert align_deserialized.u32_field == 0x22334455
            assert align_deserialized.u8_field2 == 0x66
            assert align_deserialized.u64_field == 0x778899AABBCCDDEE
            assert align_deserialized.u16_field == 0xFF00
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_complex_nested_scenario(self):
        """Test a complex scenario with multiple levels of nesting."""
        schema_content = """
        namespace game.simple;
        
        struct Vector3 {
            x: f32;
            y: f32;
            z: f32;
        }
        
        struct Transform {
            position: Vector3;
            rotation: Vector3;
            scale: Vector3;
        }
        
        struct Entity {
            id: u32;
            transform: Transform;
            health: f32;
            flags: u16;
        }
        
        struct GameState {
            player: Entity;
            enemy: Entity;
            timestamp: u64;
            score: u32;
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
            Vector3 = self._find_class_by_name(generated_module, 'Vector3')
            Transform = self._find_class_by_name(generated_module, 'Transform')
            Entity = self._find_class_by_name(generated_module, 'Entity')
            GameState = self._find_class_by_name(generated_module, 'GameState')
            
            # Create a complex nested structure
            game_state = GameState(
                player=Entity(
                    id=1,
                    transform=Transform(
                        position=Vector3(x=10.0, y=0.0, z=5.0),
                        rotation=Vector3(x=0.0, y=45.0, z=0.0),
                        scale=Vector3(x=1.0, y=1.0, z=1.0)
                    ),
                    health=100.0,
                    flags=0x0001
                ),
                enemy=Entity(
                    id=2,
                    transform=Transform(
                        position=Vector3(x=-5.0, y=0.0, z=8.0),
                        rotation=Vector3(x=0.0, y=180.0, z=0.0),
                        scale=Vector3(x=1.2, y=1.2, z=1.2)
                    ),
                    health=75.0,
                    flags=0x0002
                ),
                timestamp=1234567890,
                score=42000
            )
            
            # Test serialization and deserialization
            binary_data = game_state.to_bytes()
            deserialized = GameState.from_bytes(binary_data)
            
            # Verify deep structure
            assert deserialized.player.id == 1
            assert abs(deserialized.player.transform.position.x - 10.0) < 1e-6
            assert abs(deserialized.player.transform.position.y - 0.0) < 1e-6
            assert abs(deserialized.player.transform.position.z - 5.0) < 1e-6
            assert abs(deserialized.player.transform.rotation.y - 45.0) < 1e-6
            assert abs(deserialized.player.health - 100.0) < 1e-6
            assert deserialized.player.flags == 0x0001
            
            assert deserialized.enemy.id == 2
            assert abs(deserialized.enemy.transform.position.x - (-5.0)) < 1e-6
            assert abs(deserialized.enemy.transform.scale.x - 1.2) < 1e-6
            assert abs(deserialized.enemy.health - 75.0) < 1e-6
            assert deserialized.enemy.flags == 0x0002
            
            assert deserialized.timestamp == 1234567890
            assert deserialized.score == 42000
            
        finally:
            sys.path.remove(str(python_dir)) 
