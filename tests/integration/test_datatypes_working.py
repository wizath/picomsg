#!/usr/bin/env python3

import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
import pytest


class TestWorkingDataTypes:
    """Test data types that are known to work with the current Python generator."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dirs = []
    
    def teardown_method(self):
        """Clean up test environment."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
    
    def create_temp_dir(self) -> Path:
        """Create a temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_schema_file(self, content: str, filename: str = "test.pico") -> Path:
        """Create a schema file with the given content."""
        temp_dir = self.create_temp_dir()
        schema_file = temp_dir / filename
        schema_file.write_text(content)
        return schema_file
    
    def generate_python_code(self, schema_file: Path) -> Path:
        """Generate Python code from schema."""
        output_dir = self.create_temp_dir() / "python_generated"
        output_dir.mkdir()
        
        cmd = [
            sys.executable, '-m', 'picomsg.cli', 'compile',
            '-l', 'python',
            '-o', str(output_dir),
            str(schema_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Code generation failed: {result.stderr}")
        
        return output_dir
    
    def _find_class_by_name(self, module, class_name: str):
        """Find a class by name, handling namespace prefixes."""
        # First try direct access
        if hasattr(module, class_name):
            return getattr(module, class_name)
        
        # Try with namespace prefixes
        for attr_name in dir(module):
            if (attr_name.endswith(class_name) and 
                not attr_name.startswith('_') and 
                hasattr(module, attr_name)):
                attr_obj = getattr(module, attr_name)
                if (isinstance(attr_obj, type) and 
                    hasattr(attr_obj, '__init__') and
                    hasattr(attr_obj, 'to_bytes') and
                    hasattr(attr_obj, 'from_bytes') and
                    not attr_name.endswith('Error') and
                    not attr_name.endswith('Base')):
                    return attr_obj
        
        raise AttributeError(f"Could not find class for {class_name}")
    
    def test_all_primitive_types(self):
        """Test all primitive data types."""
        schema_content = """
        namespace test.primitives;
        
        struct AllPrimitives {
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
            # Clear any cached module
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            AllPrimitives = self._find_class_by_name(generated_module, 'AllPrimitives')
            
            # Test boundary values
            test_cases = [
                {
                    'name': 'zero_values',
                    'u8_val': 0, 'u16_val': 0, 'u32_val': 0, 'u64_val': 0,
                    'i8_val': 0, 'i16_val': 0, 'i32_val': 0, 'i64_val': 0,
                    'f32_val': 0.0, 'f64_val': 0.0
                },
                {
                    'name': 'max_unsigned',
                    'u8_val': 255, 'u16_val': 65535, 'u32_val': 4294967295, 'u64_val': 18446744073709551615,
                    'i8_val': 127, 'i16_val': 32767, 'i32_val': 2147483647, 'i64_val': 9223372036854775807,
                    'f32_val': 3.4028235e+38, 'f64_val': 1.7976931348623157e+308
                },
                {
                    'name': 'min_signed',
                    'u8_val': 0, 'u16_val': 0, 'u32_val': 0, 'u64_val': 0,
                    'i8_val': -128, 'i16_val': -32768, 'i32_val': -2147483648, 'i64_val': -9223372036854775808,
                    'f32_val': -3.4028235e+38, 'f64_val': -1.7976931348623157e+308
                },
                {
                    'name': 'typical_values',
                    'u8_val': 42, 'u16_val': 1234, 'u32_val': 123456789, 'u64_val': 123456789012345,
                    'i8_val': -42, 'i16_val': -1234, 'i32_val': -123456789, 'i64_val': -123456789012345,
                    'f32_val': 3.14159, 'f64_val': 2.718281828459045
                }
            ]
            
            for test_case in test_cases:
                case_name = test_case.pop('name')
                
                # Create instance
                instance = AllPrimitives(**test_case)
                
                # Test serialization
                binary_data = instance.to_bytes()
                assert len(binary_data) > 0, f"Empty binary data for {case_name}"
                
                # Test deserialization
                deserialized = AllPrimitives.from_bytes(binary_data)
                
                # Verify values with appropriate tolerance
                for field_name, expected_value in test_case.items():
                    actual_value = getattr(deserialized, field_name)
                    if isinstance(expected_value, float):
                        if field_name.startswith('f32'):
                            # Use relative tolerance for large f32 values
                            if abs(expected_value) > 1e30:
                                tolerance = abs(expected_value) * 1e-6  # Relative tolerance
                            else:
                                tolerance = 1e-5  # Absolute tolerance
                            assert abs(actual_value - expected_value) < tolerance, \
                                f"f32 mismatch in {case_name}.{field_name}: {actual_value} != {expected_value}"
                        else:  # f64
                            # Use relative tolerance for large f64 values
                            if abs(expected_value) > 1e100:
                                tolerance = abs(expected_value) * 1e-15  # Relative tolerance
                            else:
                                tolerance = 1e-12  # Absolute tolerance
                            assert abs(actual_value - expected_value) < tolerance, \
                                f"f64 mismatch in {case_name}.{field_name}: {actual_value} != {expected_value}"
                    else:
                        assert actual_value == expected_value, \
                            f"Value mismatch in {case_name}.{field_name}: {actual_value} != {expected_value}"
                
        finally:
            sys.path.remove(str(python_dir))
    
    def test_simple_nested_structs(self):
        """Test simple nested structures with only primitive fields."""
        schema_content = """
        namespace test.simple;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct Rectangle {
            top_left: Point;
            bottom_right: Point;
            color: u32;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            Point = self._find_class_by_name(generated_module, 'Point')
            Rectangle = self._find_class_by_name(generated_module, 'Rectangle')
            
            # Test Point
            point = Point(x=1.5, y=2.5)
            point_binary = point.to_bytes()
            point_deserialized = Point.from_bytes(point_binary)
            
            assert abs(point_deserialized.x - 1.5) < 1e-5
            assert abs(point_deserialized.y - 2.5) < 1e-5
            
            # Test Rectangle with Point instances
            top_left = Point(x=0.0, y=0.0)
            bottom_right = Point(x=10.0, y=10.0)
            rectangle = Rectangle(
                top_left=top_left,
                bottom_right=bottom_right,
                color=0xFF0000
            )
            
            rect_binary = rectangle.to_bytes()
            rect_deserialized = Rectangle.from_bytes(rect_binary)
            
            assert abs(rect_deserialized.top_left.x - 0.0) < 1e-5
            assert abs(rect_deserialized.top_left.y - 0.0) < 1e-5
            assert abs(rect_deserialized.bottom_right.x - 10.0) < 1e-5
            assert abs(rect_deserialized.bottom_right.y - 10.0) < 1e-5
            assert rect_deserialized.color == 0xFF0000
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_binary_format_consistency(self):
        """Test that binary format is consistent."""
        schema_content = """
        namespace test.binary;
        
        struct BinaryTest {
            u8_val: u8;
            u16_val: u16;
            u32_val: u32;
            f32_val: f32;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            BinaryTest = self._find_class_by_name(generated_module, 'BinaryTest')
            
            # Create instance with known values
            instance = BinaryTest(
                u8_val=0x42,
                u16_val=0x1234,
                u32_val=0x12345678,
                f32_val=3.14159
            )
            
            # Serialize multiple times - should be identical
            binary1 = instance.to_bytes()
            binary2 = instance.to_bytes()
            assert binary1 == binary2, "Binary serialization not consistent"
            
            # Deserialize and re-serialize - should be identical
            deserialized = BinaryTest.from_bytes(binary1)
            binary3 = deserialized.to_bytes()
            assert binary1 == binary3, "Round-trip serialization not consistent"
            
            # Verify values
            assert deserialized.u8_val == 0x42
            assert deserialized.u16_val == 0x1234
            assert deserialized.u32_val == 0x12345678
            assert abs(deserialized.f32_val - 3.14159) < 1e-5
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_multiple_structs(self):
        """Test multiple independent structs in same schema."""
        schema_content = """
        namespace test.multi;
        
        struct Player {
            id: u32;
            health: f32;
            score: u64;
        }
        
        struct Enemy {
            type_id: u16;
            damage: f32;
            alive: u8;
        }
        
        struct GameState {
            level: u32;
            time_remaining: f32;
            paused: u8;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            Player = self._find_class_by_name(generated_module, 'Player')
            Enemy = self._find_class_by_name(generated_module, 'Enemy')
            GameState = self._find_class_by_name(generated_module, 'GameState')
            
            # Test Player
            player = Player(id=123, health=100.0, score=9876543210)
            player_binary = player.to_bytes()
            player_deserialized = Player.from_bytes(player_binary)
            
            assert player_deserialized.id == 123
            assert abs(player_deserialized.health - 100.0) < 1e-5
            assert player_deserialized.score == 9876543210
            
            # Test Enemy
            enemy = Enemy(type_id=5, damage=25.5, alive=1)
            enemy_binary = enemy.to_bytes()
            enemy_deserialized = Enemy.from_bytes(enemy_binary)
            
            assert enemy_deserialized.type_id == 5
            assert abs(enemy_deserialized.damage - 25.5) < 1e-5
            assert enemy_deserialized.alive == 1
            
            # Test GameState
            game_state = GameState(level=10, time_remaining=45.75, paused=0)
            game_binary = game_state.to_bytes()
            game_deserialized = GameState.from_bytes(game_binary)
            
            assert game_deserialized.level == 10
            assert abs(game_deserialized.time_remaining - 45.75) < 1e-5
            assert game_deserialized.paused == 0
            
        finally:
            sys.path.remove(str(python_dir))
    
    def test_edge_case_values(self):
        """Test edge case values for primitive types."""
        schema_content = """
        namespace test.edge;
        
        struct EdgeCases {
            u8_min: u8;
            u8_max: u8;
            i8_min: i8;
            i8_max: i8;
            f32_small: f32;
            f32_large: f32;
            f64_precise: f64;
        }
        """
        
        schema_file = self.create_schema_file(schema_content)
        python_dir = self.generate_python_code(schema_file)
        
        import sys
        import importlib
        sys.path.insert(0, str(python_dir))
        
        try:
            # Clear any cached module
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            import picomsg_generated as generated_module
            EdgeCases = self._find_class_by_name(generated_module, 'EdgeCases')
            
            # Test edge cases
            edge_case = EdgeCases(
                u8_min=0,
                u8_max=255,
                i8_min=-128,
                i8_max=127,
                f32_small=1.175494e-38,  # Smallest positive f32
                f32_large=3.402823e+38,  # Largest f32
                f64_precise=1.7976931348623157e+308  # Large f64
            )
            
            binary_data = edge_case.to_bytes()
            deserialized = EdgeCases.from_bytes(binary_data)
            
            assert deserialized.u8_min == 0
            assert deserialized.u8_max == 255
            assert deserialized.i8_min == -128
            assert deserialized.i8_max == 127
            assert abs(deserialized.f32_small - 1.175494e-38) < 1e-43
            assert abs(deserialized.f32_large - 3.402823e+38) < 1e+33
            assert abs(deserialized.f64_precise - 1.7976931348623157e+308) < 1e+303
            
        finally:
            sys.path.remove(str(python_dir)) 
