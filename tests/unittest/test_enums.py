"""
Tests for enum functionality in PicoMsg.
"""

import pytest
from picomsg.schema.parser import SchemaParser
from picomsg.schema.ast import Enum, EnumValue, EnumType, PrimitiveType
from picomsg.codegen.python import PythonCodeGenerator


class TestEnumFunctionality:
    """Test enum functionality."""
    
    def test_basic_enum_parsing(self):
        """Test basic enum parsing."""
        schema_text = """
        enum Color : u8 {
            Red = 1,
            Green = 2,
            Blue = 3,
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        assert len(schema.enums) == 1
        color_enum = schema.enums[0]
        assert color_enum.name == "Color"
        assert color_enum.backing_type.name == "u8"
        assert len(color_enum.values) == 3
        assert color_enum.values[0].name == "Red"
        assert color_enum.values[0].value == 1
    
    def test_enum_auto_increment(self):
        """Test enum auto-increment values."""
        schema_text = """
        enum Status : u16 {
            Inactive,
            Active = 10,
            Pending,
            Complete = 100,
            Failed,
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        status_enum = schema.enums[0]
        assert status_enum.values[0].value == 0   # Inactive
        assert status_enum.values[1].value == 10  # Active
        assert status_enum.values[2].value == 11  # Pending
        assert status_enum.values[3].value == 100 # Complete
        assert status_enum.values[4].value == 101 # Failed
    
    def test_enum_in_struct(self):
        """Test enum usage in struct fields."""
        schema_text = """
        enum Priority : u8 {
            Low,
            Medium,
            High,
        }
        
        struct Task {
            name: string;
            priority: Priority;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        assert len(schema.enums) == 1
        assert len(schema.structs) == 1
        
        task_struct = schema.structs[0]
        priority_field = task_struct.fields[1]
        assert priority_field.name == "priority"
        assert isinstance(priority_field.type, EnumType)
        assert priority_field.type.name == "Priority"
    
    def test_enum_validation_errors(self):
        """Test enum parsing validation errors."""
        parser = SchemaParser()
        
        # Invalid backing type
        with pytest.raises(ValueError, match="must be an integer type"):
            parser.parse_string("""
            enum Color : f32 {
                Red,
            }
            """)
        
        # Value out of range for u8
        with pytest.raises(ValueError, match="exceeds maximum"):
            parser.parse_string("""
            enum Color : u8 {
                Red = 300,
            }
            """)
        
        # Duplicate enum value names
        with pytest.raises(ValueError, match="Duplicate enum value names"):
            parser.parse_string("""
            enum Color : u8 {
                Red,
                Red,
            }
            """)
    
    def test_enum_code_generation(self):
        """Test enum code generation."""
        schema_text = """
        enum Color : u8 {
            Red = 1,
            Green = 2,
            Blue = 3,
        }
        
        struct Item {
            color: Color;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        gen = PythonCodeGenerator(schema)
        files = gen.generate()
        code = list(files.values())[0]
        
        # Check enum class generation
        assert "from enum import IntEnum" in code
        assert "class Color(IntEnum):" in code
        assert "Red = 1" in code
        assert "Green = 2" in code
        assert "Blue = 3" in code
        assert "def from_int(cls, value: int)" in code
        assert "def to_int(self) -> int" in code
    
    def test_enum_serialization_functionality(self):
        """Test enum serialization functionality."""
        schema_text = """
        enum Priority : u8 {
            Low,
            Medium,
            High,
        }
        
        struct Task {
            name: string;
            priority: Priority;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        gen = PythonCodeGenerator(schema)
        files = gen.generate()
        code = list(files.values())[0]
        
        # Execute generated code
        exec_globals = {}
        exec(code, exec_globals)
        Priority = exec_globals['Priority']
        Task = exec_globals['Task']
        
        # Test enum values
        assert Priority.Low.value == 0
        assert Priority.Medium.value == 1
        assert Priority.High.value == 2
        
        # Test to_int method
        assert Priority.Low.to_int() == 0
        assert Priority.High.to_int() == 2
        
        # Test from_int method
        assert Priority.from_int(0) == Priority.Low
        assert Priority.from_int(2) == Priority.High
        
        # Test invalid value
        with pytest.raises(ValueError, match="Invalid Priority value"):
            Priority.from_int(99)
        
        # Test task with enum
        task = Task(name="Test Task", priority=Priority.High)
        assert task.priority == Priority.High
        
        # Test serialization
        data = task.to_bytes()
        assert len(data) > 0
        
        # Test deserialization
        task2 = Task.from_bytes(data)
        assert task2.name == "Test Task"
        assert task2.priority == Priority.High
    
    def test_enum_arrays(self):
        """Test enum arrays functionality."""
        schema_text = """
        enum Color : u8 {
            Red,
            Green,
            Blue,
        }
        
        struct Palette {
            colors: [Color];
            primary: [Color:3];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        gen = PythonCodeGenerator(schema)
        files = gen.generate()
        code = list(files.values())[0]
        
        # Execute generated code
        exec_globals = {}
        exec(code, exec_globals)
        Color = exec_globals['Color']
        Palette = exec_globals['Palette']
        
        # Create palette with enum arrays
        palette = Palette(
            colors=[Color.Red, Color.Blue],
            primary=[Color.Red, Color.Green, Color.Blue]
        )
        
        # Test serialization
        data = palette.to_bytes()
        
        # Test deserialization
        palette2 = Palette.from_bytes(data)
        assert len(palette2.colors) == 2
        assert palette2.colors[0] == Color.Red
        assert palette2.colors[1] == Color.Blue
        assert len(palette2.primary) == 3
        assert palette2.primary[0] == Color.Red
        assert palette2.primary[1] == Color.Green
        assert palette2.primary[2] == Color.Blue
    
    def test_enum_json_conversion(self):
        """Test enum JSON conversion."""
        schema_text = """
        enum Status : u8 {
            Pending,
            Active,
            Complete,
        }
        
        struct User {
            name: string;
            status: Status;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        gen = PythonCodeGenerator(schema)
        files = gen.generate()
        code = list(files.values())[0]
        
        # Execute generated code
        exec_globals = {}
        exec(code, exec_globals)
        Status = exec_globals['Status']
        User = exec_globals['User']
        
        # Create user with enum
        user = User(name="Alice", status=Status.Active)
        
        # Test to_dict (JSON serialization)
        json_data = user.to_dict()
        assert json_data['name'] == "Alice"
        assert json_data['status'] == 1  # Active = 1
        
        # Test from_dict (JSON deserialization)
        user2 = User.from_dict(json_data)
        assert user2.name == "Alice"
        assert user2.status == Status.Active

    def test_enum_ast_creation(self):
        """Test enum AST creation and validation."""
        # Test EnumValue creation
        value1 = EnumValue(name="Red", value=1)
        assert value1.name == "Red"
        assert value1.value == 1
        
        # Test EnumValue with auto-increment (None)
        value2 = EnumValue(name="Green")
        assert value2.name == "Green"
        assert value2.value is None
        
        # Test Enum creation
        backing_type = PrimitiveType(name="u8")
        values = [
            EnumValue(name="Red", value=1),
            EnumValue(name="Green", value=2),
            EnumValue(name="Blue", value=3),
        ]
        
        enum = Enum(name="Color", backing_type=backing_type, values=values)
        assert enum.name == "Color"
        assert enum.backing_type.name == "u8"
        assert len(enum.values) == 3
        assert enum.values[0].value == 1
    
    def test_enum_validation(self):
        """Test enum validation."""
        backing_type = PrimitiveType(name="u8")
        
        # Test invalid backing type
        with pytest.raises(ValueError, match="must be an integer type"):
            Enum(name="Test", backing_type=PrimitiveType(name="f32"), values=[])
        
        # Test duplicate value names
        values = [
            EnumValue(name="Red", value=1),
            EnumValue(name="Red", value=2),  # Duplicate name
        ]
        with pytest.raises(ValueError, match="Duplicate enum value names"):
            Enum(name="Test", backing_type=backing_type, values=values)
        
        # Test value exceeds backing type range
        values = [EnumValue(name="TooLarge", value=300)]  # u8 max is 255
        with pytest.raises(ValueError, match="exceeds maximum"):
            Enum(name="Test", backing_type=backing_type, values=values)
    
    def test_enum_size_and_alignment(self):
        """Test enum size and alignment methods."""
        backing_type = PrimitiveType(name="u16")
        values = [EnumValue(name="Test", value=1)]
        enum = Enum(name="Test", backing_type=backing_type, values=values)
        
        assert enum.size_bytes() == 2  # u16 = 2 bytes
        assert enum.alignment() == 2   # u16 alignment = 2
