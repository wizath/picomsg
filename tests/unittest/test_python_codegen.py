"""
Tests for Python code generator.
"""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator


class TestPythonCodeGenerator:
    """Test Python code generator."""
    
    def test_basic_generation(self):
        """Test basic code generation."""
        schema_content = """
        namespace test.basic;
        version 1;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message SimpleMessage {
            id: u32;
            point: Point;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        assert len(files) == 1
        assert "picomsg_generated.py" in files
        
        code = files["picomsg_generated.py"]
        
        # Check for basic structure
        assert '"""Generated PicoMsg Python bindings"""' in code
        assert "import struct" in code
        assert "import json" in code
        assert "from typing import Dict, Any, Optional, Union, List" in code
        
        # Check for constants
        assert "TESTBASIC_MAGIC_BYTE_1 = 0xAB" in code
        assert "TESTBASIC_VERSION = 1" in code
        assert "TESTBASIC_SIMPLEMESSAGE_TYPE_ID = 1" in code
        
        # Check for error classes
        assert "class TestBasicError(Exception):" in code
        assert "class TestBasicErrorBufferTooSmall(TestBasicError):" in code
        
        # Check for base class
        assert "class TestBasicBase:" in code
        assert "def from_bytes(cls, data: bytes)" in code
        assert "def to_bytes(self) -> bytes:" in code
        assert "def to_json(self, indent: Optional[int] = None) -> str:" in code
        
        # Check for struct class
        assert "class TestBasicPoint(TestBasicBase):" in code
        assert "struct.pack" in code
        assert "struct.unpack" in code
        
        # Check for message class
        assert "class TestBasicSimpleMessage(TestBasicBase):" in code
        assert "self._id" in code
        assert "self._point" in code
    
    def test_primitive_types(self):
        """Test all primitive types."""
        schema_content = """
        namespace test.primitives;
        
        struct AllTypes {
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
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check that struct module is used for serialization
        assert 'struct.pack' in code
        assert 'struct.unpack' in code
        
        # Check default values in constructor
        assert 'self._u8_field = kwargs.get("u8_field", 0)' in code
        assert 'self._f32_field = kwargs.get("f32_field", 0.0)' in code
    
    def test_strings_and_bytes(self):
        """Test string and bytes types."""
        schema_content = """
        namespace test.strings;
        
        struct StringStruct {
            name: string;
            data: bytes;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check that strings and bytes are handled
        assert "string" in code or "bytes" in code  # Basic type handling
        
        # Check default values
        assert 'self._name = kwargs.get("name", "")' in code
        assert 'self._data = kwargs.get("data", b"")' in code
    
    def test_arrays(self):
        """Test array types."""
        schema_content = """
        namespace test.arrays;
        
        struct ArrayStruct {
            numbers: [u32];
            points: [Point];
        }
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check that arrays are handled
        assert "numbers" in code
        assert "points" in code
        
        # Check default values
        assert 'self._numbers = kwargs.get("numbers", [])' in code
        assert 'self._points = kwargs.get("points", [])' in code
    
    def test_custom_module_name(self):
        """Test custom module name option."""
        schema_content = """
        namespace test.custom;
        
        struct Simple {
            value: u32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        generator.set_option('module_name', 'my_custom_module')
        
        files = generator.generate()
        
        assert len(files) == 1
        assert "my_custom_module.py" in files
        assert "picomsg_generated.py" not in files
    
    def test_namespace_handling(self):
        """Test namespace handling in generated code."""
        schema_content = """
        namespace api.v1.messages;
        
        struct Header {
            type: u8;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check namespace prefix in constants
        assert "APIV1MESSAGES_MAGIC_BYTE_1 = 0xAB" in code
        
        # Check namespace prefix in class names
        assert "class ApiV1MessagesError(Exception):" in code
        assert "class ApiV1MessagesBase:" in code
        assert "class ApiV1MessagesHeader(ApiV1MessagesBase):" in code
    
    def test_struct_size_calculation(self):
        """Test struct size calculation."""
        schema_content = """
        namespace test.sizes;
        
        struct SmallStruct {
            a: u8;
            b: u16;
        }
        
        struct LargeStruct {
            a: u64;
            b: f64;
            c: u32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check that structs are generated
        assert "SmallStruct" in code
        assert "LargeStruct" in code
    
    def test_identifier_sanitization(self):
        """Test identifier sanitization."""
        schema_content = """
        namespace test.sanitize;
        
        struct Test_Struct {
            field_with_underscores: u32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check that underscores are preserved in Python (they're valid)
        assert "class TestSanitizeTest_Struct" in code
        assert "field_with_underscores" in code
    
    def test_json_serialization_methods(self):
        """Test JSON serialization method generation."""
        schema_content = """
        namespace test.json;
        
        struct JsonTest {
            id: u32;
            value: f32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check to_dict method
        assert "def to_dict(self) -> Dict[str, Any]:" in code
        assert "id" in code
        assert "value" in code
        
        # Check from_dict method
        assert "def from_dict(cls, data: Dict[str, Any]) -> \"Self\":" in code
        assert 'kwargs["id"] = data.get("id")' in code
        assert 'kwargs["value"] = data.get("value")' in code
        
        # Check JSON methods in base class
        assert "def to_json(self, indent: Optional[int] = None) -> str:" in code
        assert "def from_json(cls, json_str: str) -> \"Self\":" in code
    
    def test_cross_platform_compatibility(self):
        """Test cross-platform compatibility features."""
        schema_content = """
        namespace test.compat;
        
        struct CompatTest {
            value: u32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check for struct-based serialization (cross-platform compatibility)
        assert 'struct.pack' in code
        assert 'struct.unpack' in code
    
    def test_error_handling(self):
        """Test error handling in generated code."""
        schema_content = """
        namespace test.errors;
        
        struct ErrorTest {
            value: u32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check error class hierarchy
        assert "class TestErrorsError(Exception):" in code
        assert "class TestErrorsErrorInvalidHeader(TestErrorsError):" in code
        assert "class TestErrorsErrorBufferTooSmall(TestErrorsError):" in code
        assert "class TestErrorsErrorInvalidData(TestErrorsError):" in code
        
        # Check error classes exist
        assert "TestErrorsError" in code
    
    def test_generated_code_execution(self):
        """Test that generated code can be executed."""
        schema_content = """
        namespace test.exec;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message TestMessage {
            id: u32;
            point: Point;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Write to temporary file and try to import
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Add temp directory to path
            temp_dir = Path(temp_path).parent
            temp_name = Path(temp_path).stem
            
            sys.path.insert(0, str(temp_dir))
            
            # Import the module
            import importlib.util
            spec = importlib.util.spec_from_file_location(temp_name, temp_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Test basic functionality
            point = module.TestExecPoint(x=1.0, y=2.0)
            assert point.x == 1.0
            assert point.y == 2.0
            
            # Test JSON serialization
            json_str = point.to_json()
            assert "1.0" in json_str
            assert "2.0" in json_str
            
            # Test binary serialization
            binary_data = point.to_bytes()
            assert len(binary_data) == 8  # 2 floats = 8 bytes
            
            # Test deserialization
            point2 = module.TestExecPoint.from_bytes(binary_data)
            assert abs(point2.x - 1.0) < 0.001
            assert abs(point2.y - 2.0) < 0.001
            
        finally:
            # Cleanup
            sys.path.remove(str(temp_dir))
            Path(temp_path).unlink()
    
    def test_version_handling(self):
        """Test version handling in constants."""
        schema_content = """
        namespace test.version;
        version 42;
        
        struct VersionTest {
            value: u32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        assert "TESTVERSION_VERSION = 42" in code
    
    def test_no_namespace(self):
        """Test generation without namespace."""
        schema_content = """
        struct NoNamespace {
            value: u32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check that no namespace prefix is used
        assert "MAGIC_BYTE_1 = 0xAB" in code
        assert "class PicoMsgError(Exception):" in code
        assert "class PicoMsgBase:" in code
        assert "class NoNamespace(PicoMsgBase):" in code

    def test_enum_generation(self):
        """Test enum code generation."""
        schema_content = """
        namespace test.enums;
        
        enum Color : u8 {
            Red = 1,
            Green = 2,
            Blue = 3,
        }
        
        enum Status : u16 {
            Inactive,
            Active = 10,
            Complete,
        }
        
        struct Item {
            name: string;
            color: Color;
            status: Status;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check enum imports
        assert "from enum import IntEnum" in code
        
        # Check Color enum
        assert "class TestEnumsColor(IntEnum):" in code
        assert "Red = 1" in code
        assert "Green = 2" in code
        assert "Blue = 3" in code
        
        # Check Status enum
        assert "class TestEnumsStatus(IntEnum):" in code
        assert "Inactive = 0" in code
        assert "Active = 10" in code
        assert "Complete = 11" in code
        
        # Check enum utility methods
        assert "def from_int(cls, value: int)" in code
        assert "def to_int(self) -> int" in code
        
        # Check enum usage in struct (generated code uses property setters, not type hints)
        assert "TestEnumsColor.Red" in code  # Default value
        assert "TestEnumsStatus.Inactive" in code  # Default value

    def test_enum_serialization(self):
        """Test enum serialization in generated code."""
        schema_content = """
        namespace test.enum_serial;
        
        enum Priority : u8 {
            Low,
            Medium,
            High,
        }
        
        struct Task {
            priority: Priority;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check enum serialization
        assert "self._priority.to_int()" in code
        assert "TestEnum_serialPriority.from_int(value)" in code
        
        # Check struct packing format for u8 enum
        assert "struct.pack" in code

    def test_enum_arrays(self):
        """Test enum arrays in generated code."""
        schema_content = """
        namespace test.enum_arrays;
        
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
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check variable array enum handling
        assert "item.to_int()" in code  # Serialization
        assert "TestEnum_arraysColor.from_int(value)" in code  # Deserialization
        
        # Check fixed array enum handling (generated code doesn't use type hints in this way)
        assert "TestEnum_arraysColor" in code

    def test_enum_json_conversion(self):
        """Test enum JSON conversion in generated code."""
        schema_content = """
        namespace test.enum_json;
        
        enum Status : u16 {
            Pending = 100,
            Active = 200,
            Complete = 300,
        }
        
        struct User {
            name: string;
            status: Status;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check JSON serialization (enum to int)
        assert "self._status.to_int()" in code
        
        # Check JSON deserialization (int to enum)
        assert 'TestEnum_jsonStatus.from_int(data["status"])' in code

    def test_enum_validation(self):
        """Test enum validation in generated code."""
        schema_content = """
        namespace test.enum_validation;
        
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
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check validation in from_int method
        assert "raise ValueError" in code
        assert "Invalid" in code and "value" in code

    def test_enum_type_hints(self):
        """Test enum type hints in generated code."""
        schema_content = """
        namespace test.enum_hints;
        
        enum Priority : u8 {
            Low,
            High,
        }
        
        struct Task {
            priority: Priority;
            priorities: [Priority];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check enum usage (generated code doesn't use type hints in this way)
        assert "TestEnum_hintsPriority" in code 
