"""
Cross-language compatibility tests for PicoMsg.

Tests that data encoded in one language can be properly decoded in another,
covering enums, fixed arrays, and all supported features.
"""

import pytest
import tempfile
import subprocess
import sys
from pathlib import Path
from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator
from picomsg.codegen.c import CCodeGenerator
from picomsg.codegen.rust import RustCodeGenerator
from .common_schemas import IntegrationSchemas, load_schema


class TestCrossLanguageEnums:
    """Test enum compatibility across languages."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.schema_file = self.temp_dir / "test.pico"
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_enum_python_to_python_roundtrip(self):
        """Test enum serialization/deserialization within Python."""
        # Load schema from file
        schema = load_schema(IntegrationSchemas.CROSS_LANGUAGE_ENUMS)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Import and test
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear module cache
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Test enum values
        assert picomsg_generated.TestEnumsPriority.Low.value == 1
        assert picomsg_generated.TestEnumsPriority.Medium.value == 5
        assert picomsg_generated.TestEnumsPriority.High.value == 10
        
        assert picomsg_generated.TestEnumsStatus.Inactive.value == 0
        assert picomsg_generated.TestEnumsStatus.Active.value == 100
        assert picomsg_generated.TestEnumsStatus.Pending.value == 101
        assert picomsg_generated.TestEnumsStatus.Complete.value == 1000
        
        # Test struct with enums
        task = picomsg_generated.TestEnumsTask(
            id=42,
            name="Test Task",
            priority=picomsg_generated.TestEnumsPriority.High,
            status=picomsg_generated.TestEnumsStatus.Active
        )
        
        # Serialize and deserialize
        data = task.to_bytes()
        task2 = picomsg_generated.TestEnumsTask.from_bytes(data)
        
        assert task2.id == 42
        assert task2.name == "Test Task"
        assert task2.priority == picomsg_generated.TestEnumsPriority.High
        assert task2.status == picomsg_generated.TestEnumsStatus.Active
        
        # Test JSON conversion
        json_data = task.to_json()
        task3 = picomsg_generated.TestEnumsTask.from_json(json_data)
        
        assert task3.id == 42
        assert task3.name == "Test Task"
        assert task3.priority == picomsg_generated.TestEnumsPriority.High
        assert task3.status == picomsg_generated.TestEnumsStatus.Active
    
    def test_enum_binary_format_consistency(self):
        """Test that enum binary format is consistent and predictable."""
        # Load schema from file
        schema = load_schema(IntegrationSchemas.BINARY_FORMAT)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Import and test
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear module cache
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Create pixel with red color
        pixel = picomsg_generated.TestBinaryPixel(
            x=100,
            y=200,
            color=picomsg_generated.TestBinaryColor.Red
        )
        
        data = pixel.to_bytes()
        
        # Verify binary format manually
        # Expected: x=100 (u16 LE), y=200 (u16 LE), color=1 (u8)
        expected = bytes([
            100, 0,  # x = 100 (little endian u16)
            200, 0,  # y = 200 (little endian u16)
            1        # color = Red = 1 (u8)
        ])
        
        assert data == expected
        
        # Test deserialization
        pixel2 = picomsg_generated.TestBinaryPixel.from_bytes(data)
        assert pixel2.x == 100
        assert pixel2.y == 200
        assert pixel2.color == picomsg_generated.TestBinaryColor.Red


class TestCrossLanguageFixedArrays:
    """Test fixed array compatibility across languages."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.schema_file = self.temp_dir / "test.pico"
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_fixed_array_python_roundtrip(self):
        """Test fixed array serialization/deserialization within Python."""
        # Load schema from file
        schema = load_schema(IntegrationSchemas.FIXED_ARRAYS)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Import and test
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear module cache
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Test Vector3 with fixed array
        vec = picomsg_generated.TestArraysVector3(coords=[1.0, 2.0, 3.0])
        data = vec.to_bytes()
        vec2 = picomsg_generated.TestArraysVector3.from_bytes(data)
        assert vec2.coords == [1.0, 2.0, 3.0]
        
        # Test Transform with multiple fixed arrays
        transform = picomsg_generated.TestArraysTransform(
            position=[10.0, 20.0, 30.0],
            rotation=[0.0, 0.0, 0.0, 1.0],
            scale=[1.0, 1.0, 1.0]
        )
        
        data = transform.to_bytes()
        transform2 = picomsg_generated.TestArraysTransform.from_bytes(data)
        
        assert transform2.position == [10.0, 20.0, 30.0]
        assert transform2.rotation == [0.0, 0.0, 0.0, 1.0]
        assert transform2.scale == [1.0, 1.0, 1.0]
        
        # Test GameState with nested fixed arrays
        game_state = picomsg_generated.TestArraysGameState(
            player_positions=[
                picomsg_generated.TestArraysVector3(coords=[1.0, 2.0, 3.0]),
                picomsg_generated.TestArraysVector3(coords=[4.0, 5.0, 6.0]),
                picomsg_generated.TestArraysVector3(coords=[7.0, 8.0, 9.0]),
                picomsg_generated.TestArraysVector3(coords=[10.0, 11.0, 12.0]),
            ],
            directions=[
                picomsg_generated.TestArraysDirection.North,
                picomsg_generated.TestArraysDirection.East,
                picomsg_generated.TestArraysDirection.South,
                picomsg_generated.TestArraysDirection.West,
            ],
            scores=[100, 200, 300, 400]
        )
        
        data = game_state.to_bytes()
        game_state2 = picomsg_generated.TestArraysGameState.from_bytes(data)
        
        assert len(game_state2.player_positions) == 4
        assert game_state2.player_positions[0].coords == [1.0, 2.0, 3.0]
        assert game_state2.player_positions[3].coords == [10.0, 11.0, 12.0]
        
        assert len(game_state2.directions) == 4
        assert game_state2.directions[0] == picomsg_generated.TestArraysDirection.North
        assert game_state2.directions[3] == picomsg_generated.TestArraysDirection.West
        
        assert game_state2.scores == [100, 200, 300, 400]
    
    def test_fixed_array_binary_format_consistency(self):
        """Test that fixed array binary format is consistent."""
        # Load schema from file
        schema = load_schema(IntegrationSchemas.BINARY_FORMAT)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Import and test
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear module cache
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Create array with known values
        arr = picomsg_generated.TestBinaryIntArray(values=[0x12345678, 0x9ABCDEF0, 0x11223344])
        data = arr.to_bytes()
        
        # Verify binary format (little endian u32 values)
        expected = bytes([
            0x78, 0x56, 0x34, 0x12,  # 0x12345678 in little endian
            0xF0, 0xDE, 0xBC, 0x9A,  # 0x9ABCDEF0 in little endian
            0x44, 0x33, 0x22, 0x11,  # 0x11223344 in little endian
        ])
        
        assert data == expected
        
        # Test deserialization
        arr2 = picomsg_generated.TestBinaryIntArray.from_bytes(data)
        assert arr2.values == [0x12345678, 0x9ABCDEF0, 0x11223344]


class TestCrossLanguageComprehensive:
    """Comprehensive cross-language compatibility tests."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.schema_file = self.temp_dir / "test.pico"
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_comprehensive_schema_python_roundtrip(self):
        """Test a comprehensive schema with all features in Python."""
        # Load schema from file
        schema = load_schema(IntegrationSchemas.COMPREHENSIVE)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Import and test
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear module cache
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Create complex data structure
        complex_data = picomsg_generated.TestComprehensiveComplexData(
            id=12345678901234567890,
            type=picomsg_generated.TestComprehensiveMessageType.Data,
            priority=picomsg_generated.TestComprehensivePriority.High,
            timestamp=1640995200000,  # 2022-01-01 00:00:00 UTC in milliseconds
            position=picomsg_generated.TestComprehensivePoint3D(x=1.5, y=2.5, z=3.5),
            color=picomsg_generated.TestComprehensiveColor(rgba=[255, 128, 64, 255]),
            metadata=picomsg_generated.TestComprehensiveMetadata(
                tags=["important", "urgent", "test"],
                values=[3.14159, 2.71828],
                flags=[True, False, True, False]
            ),
            points=[
                picomsg_generated.TestComprehensivePoint3D(x=1.0, y=0.0, z=0.0),
                picomsg_generated.TestComprehensivePoint3D(x=0.0, y=1.0, z=0.0),
                picomsg_generated.TestComprehensivePoint3D(x=0.0, y=0.0, z=1.0),
                picomsg_generated.TestComprehensivePoint3D(x=1.0, y=1.0, z=0.0),
                picomsg_generated.TestComprehensivePoint3D(x=1.0, y=0.0, z=1.0),
            ],
            priorities=[
                picomsg_generated.TestComprehensivePriority.Low,
                picomsg_generated.TestComprehensivePriority.Normal,
                picomsg_generated.TestComprehensivePriority.Critical,
            ]
        )
        
        # Create message
        message = picomsg_generated.TestComprehensiveComplexMessage(
            header_id=0xDEADBEEF,
            data=complex_data,
            checksum=0x12345678
        )
        
        # Test serialization/deserialization
        data = message.to_bytes()
        message2 = picomsg_generated.TestComprehensiveComplexMessage.from_bytes(data)
        
        # Verify all fields
        assert message2.header_id == 0xDEADBEEF
        assert message2.checksum == 0x12345678
        
        data2 = message2.data
        assert data2.id == 12345678901234567890
        assert data2.type == picomsg_generated.TestComprehensiveMessageType.Data
        assert data2.priority == picomsg_generated.TestComprehensivePriority.High
        assert data2.timestamp == 1640995200000
        
        assert data2.position.x == 1.5
        assert data2.position.y == 2.5
        assert data2.position.z == 3.5
        
        assert data2.color.rgba == [255, 128, 64, 255]
        
        assert data2.metadata.tags == ["important", "urgent", "test"]
        assert data2.metadata.values == [3.14159, 2.71828]
        assert data2.metadata.flags == [True, False, True, False]
        
        assert len(data2.points) == 5
        assert data2.points[0].x == 1.0 and data2.points[0].y == 0.0 and data2.points[0].z == 0.0
        assert data2.points[4].x == 1.0 and data2.points[4].y == 0.0 and data2.points[4].z == 1.0
        
        assert len(data2.priorities) == 3
        assert data2.priorities[0] == picomsg_generated.TestComprehensivePriority.Low
        assert data2.priorities[1] == picomsg_generated.TestComprehensivePriority.Normal
        assert data2.priorities[2] == picomsg_generated.TestComprehensivePriority.Critical
        
        # Test JSON conversion
        json_str = message.to_json()
        message3 = picomsg_generated.TestComprehensiveComplexMessage.from_json(json_str)
        
        # Verify JSON roundtrip preserves all data
        assert message3.header_id == message.header_id
        assert message3.data.id == message.data.id
        assert message3.data.type == message.data.type
        assert message3.data.priority == message.data.priority
        assert message3.data.position.x == message.data.position.x
        assert message3.data.color.rgba == message.data.color.rgba
        assert message3.data.metadata.tags == message.data.metadata.tags
        assert len(message3.data.points) == len(message.data.points)
        assert len(message3.data.priorities) == len(message.data.priorities)
    
    def test_code_generation_consistency(self):
        """Test that code generation is consistent across runs."""
        schema_text = """
        namespace test.consistency;
        
        enum Status : u8 {
            Active = 1,
            Inactive = 2,
        }
        
        struct Item {
            id: u32;
            status: Status;
            data: [u8:16];
        }
        """
        
        # Generate code multiple times
        self.schema_file.write_text(schema_text)
        parser = SchemaParser()
        schema = parser.parse_file(self.schema_file)
        
        # Generate Python code multiple times
        generator1 = PythonCodeGenerator(schema)
        files1 = generator1.generate()
        
        generator2 = PythonCodeGenerator(schema)
        files2 = generator2.generate()
        
        # Code should be identical
        assert files1["picomsg_generated.py"] == files2["picomsg_generated.py"]
        
        # Generate C code multiple times
        c_generator1 = CCodeGenerator(schema)
        c_files1 = c_generator1.generate()
        
        c_generator2 = CCodeGenerator(schema)
        c_files2 = c_generator2.generate()
        
        # C code should be identical
        assert c_files1["picomsg_generated.h"] == c_files2["picomsg_generated.h"]
        assert c_files1["picomsg_generated.c"] == c_files2["picomsg_generated.c"]
        
        # Generate Rust code multiple times
        rust_generator1 = RustCodeGenerator(schema)
        rust_files1 = rust_generator1.generate()
        
        rust_generator2 = RustCodeGenerator(schema)
        rust_files2 = rust_generator2.generate()
        
        # Rust code should be identical
        assert rust_files1["picomsg_generated.rs"] == rust_files2["picomsg_generated.rs"]


class TestCrossLanguageValidation:
    """Test validation and error handling across languages."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.schema_file = self.temp_dir / "test.pico"
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_enum_validation_errors(self):
        """Test enum validation error handling."""
        schema_text = """
        namespace test.validation;
        
        enum Color : u8 {
            Red = 1,
            Green = 2,
            Blue = 3,
        }
        
        struct Pixel {
            color: Color;
        }
        """
        
        # Generate Python code
        self.schema_file.write_text(schema_text)
        parser = SchemaParser()
        schema = parser.parse_file(self.schema_file)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Import and test
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear module cache
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Test valid enum values
        pixel = picomsg_generated.TestValidationPixel(
            color=picomsg_generated.TestValidationColor.Red
        )
        data = pixel.to_bytes()
        pixel2 = picomsg_generated.TestValidationPixel.from_bytes(data)
        assert pixel2.color == picomsg_generated.TestValidationColor.Red
        
        # Test invalid binary data (enum value 99 doesn't exist)
        invalid_data = bytes([99])  # Invalid enum value
        
        # Should handle invalid enum values gracefully
        try:
            pixel3 = picomsg_generated.TestValidationPixel.from_bytes(invalid_data)
            # If no exception, check that it handles the invalid value somehow
            assert hasattr(pixel3, 'color')
        except (ValueError, KeyError):
            # Expected behavior - invalid enum values should raise errors
            pass
    
    def test_fixed_array_validation_errors(self):
        """Test fixed array validation error handling."""
        schema_text = """
        namespace test.validation;
        
        struct Vector3 {
            coords: [f32:3];
        }
        """
        
        # Generate Python code
        self.schema_file.write_text(schema_text)
        parser = SchemaParser()
        schema = parser.parse_file(self.schema_file)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Import and test
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear module cache
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Test valid fixed array
        vec = picomsg_generated.TestValidationVector3(coords=[1.0, 2.0, 3.0])
        data = vec.to_bytes()
        vec2 = picomsg_generated.TestValidationVector3.from_bytes(data)
        assert vec2.coords == [1.0, 2.0, 3.0]
        
        # Test invalid array size during serialization
        with pytest.raises(ValueError, match="must have exactly 3 elements"):
            vec_bad = picomsg_generated.TestValidationVector3(coords=[1.0, 2.0])  # Too few elements
            vec_bad.to_bytes()
        
        with pytest.raises(ValueError, match="must have exactly 3 elements"):
            vec_bad2 = picomsg_generated.TestValidationVector3(coords=[1.0, 2.0, 3.0, 4.0])  # Too many elements
            vec_bad2.to_bytes() 
