"""
Tests for PicoMsg schema parser.
"""

import pytest
import tempfile
from pathlib import Path

from picomsg.schema.parser import SchemaParser
from picomsg.schema.ast import (
    Schema, Namespace, Struct, Message, Field, Enum, EnumValue,
    PrimitiveType, StringType, BytesType, ArrayType, StructType, EnumType, FixedArrayType
)


class TestSchemaParser:
    """Test SchemaParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SchemaParser()
    
    def test_parse_empty_schema(self):
        """Test parsing an empty schema."""
        schema_text = ""
        schema = self.parser.parse_string(schema_text)
        
        assert schema.namespace is None
        assert len(schema.structs) == 0
        assert len(schema.messages) == 0
    
    def test_parse_namespace_only(self):
        """Test parsing schema with only namespace."""
        schema_text = "namespace com.example.api;"
        schema = self.parser.parse_string(schema_text)
        
        assert schema.namespace is not None
        assert schema.namespace.name == "com.example.api"
        assert len(schema.structs) == 0
        assert len(schema.messages) == 0
    
    def test_parse_simple_struct(self):
        """Test parsing a simple struct."""
        schema_text = """
        struct Point {
            x: f32;
            y: f32;
        }
        """
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.structs) == 1
        struct = schema.structs[0]
        assert struct.name == "Point"
        assert len(struct.fields) == 2
        
        assert struct.fields[0].name == "x"
        assert isinstance(struct.fields[0].type, PrimitiveType)
        assert struct.fields[0].type.name == "f32"
        
        assert struct.fields[1].name == "y"
        assert isinstance(struct.fields[1].type, PrimitiveType)
        assert struct.fields[1].type.name == "f32"
    
    def test_parse_all_primitive_types(self):
        """Test parsing all primitive types."""
        schema_text = """
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
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.structs) == 1
        struct = schema.structs[0]
        assert len(struct.fields) == 10
        
        expected_types = ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64', 'f32', 'f64']
        for i, expected_type in enumerate(expected_types):
            field = struct.fields[i]
            assert isinstance(field.type, PrimitiveType)
            assert field.type.name == expected_type
    
    def test_parse_string_and_bytes_types(self):
        """Test parsing string and bytes types."""
        schema_text = """
        struct StringsAndBytes {
            name: string;
            data: bytes;
        }
        """
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.structs) == 1
        struct = schema.structs[0]
        assert len(struct.fields) == 2
        
        assert isinstance(struct.fields[0].type, StringType)
        assert isinstance(struct.fields[1].type, BytesType)
    
    def test_parse_array_types(self):
        """Test parsing array types."""
        schema_text = """
        struct Arrays {
            numbers: [u32];
            strings: [string];
            nested: [[u8]];
        }
        """
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.structs) == 1
        struct = schema.structs[0]
        assert len(struct.fields) == 3
        
        # numbers: [u32]
        assert isinstance(struct.fields[0].type, ArrayType)
        assert isinstance(struct.fields[0].type.element_type, PrimitiveType)
        assert struct.fields[0].type.element_type.name == "u32"
        
        # strings: [string]
        assert isinstance(struct.fields[1].type, ArrayType)
        assert isinstance(struct.fields[1].type.element_type, StringType)
        
        # nested: [[u8]]
        assert isinstance(struct.fields[2].type, ArrayType)
        assert isinstance(struct.fields[2].type.element_type, ArrayType)
        assert isinstance(struct.fields[2].type.element_type.element_type, PrimitiveType)
        assert struct.fields[2].type.element_type.element_type.name == "u8"
    
    def test_parse_struct_references(self):
        """Test parsing struct type references."""
        schema_text = """
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct Line {
            start: Point;
            end: Point;
        }
        """
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.structs) == 2
        
        point_struct = schema.get_struct("Point")
        line_struct = schema.get_struct("Line")
        
        assert point_struct is not None
        assert line_struct is not None
        
        assert len(line_struct.fields) == 2
        assert isinstance(line_struct.fields[0].type, StructType)
        assert line_struct.fields[0].type.name == "Point"
        assert isinstance(line_struct.fields[1].type, StructType)
        assert line_struct.fields[1].type.name == "Point"
    
    def test_parse_messages(self):
        """Test parsing message definitions."""
        schema_text = """
        message EchoRequest {
            id: u32;
            data: bytes;
        }
        
        message EchoResponse {
            id: u32;
            result: string;
        }
        """
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.messages) == 2
        
        request = schema.get_message("EchoRequest")
        response = schema.get_message("EchoResponse")
        
        assert request is not None
        assert response is not None
        
        assert len(request.fields) == 2
        assert request.fields[0].name == "id"
        assert isinstance(request.fields[0].type, PrimitiveType)
        assert request.fields[0].type.name == "u32"
        
        assert request.fields[1].name == "data"
        assert isinstance(request.fields[1].type, BytesType)
    
    def test_parse_complete_schema(self):
        """Test parsing a complete schema with namespace, structs, and messages."""
        schema_text = """
        namespace test.complete;
        
        struct Header {
            command: u8;
            length: u16;
        }
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message Request {
            header: Header;
            point: Point;
            tags: [string];
        }
        
        message Response {
            header: Header;
            status: u8;
            data: bytes;
        }
        """
        schema = self.parser.parse_string(schema_text)
        
        assert schema.namespace is not None
        assert schema.namespace.name == "test.complete"
        assert len(schema.structs) == 2
        assert len(schema.messages) == 2
        
        # Verify struct references in messages are valid
        request = schema.get_message("Request")
        assert request is not None
        assert len(request.fields) == 3
        
        # header: Header
        assert isinstance(request.fields[0].type, StructType)
        assert request.fields[0].type.name == "Header"
        
        # point: Point
        assert isinstance(request.fields[1].type, StructType)
        assert request.fields[1].type.name == "Point"
        
        # tags: [string]
        assert isinstance(request.fields[2].type, ArrayType)
        assert isinstance(request.fields[2].type.element_type, StringType)
    
    def test_parse_with_comments(self):
        """Test parsing schema with comments."""
        schema_text = """
        // This is a line comment
        namespace test.comments;
        
        /* This is a block comment */
        struct Point {
            x: f32;  // X coordinate
            y: f32;  /* Y coordinate */
        }
        
        /*
         * Multi-line
         * block comment
         */
        message TestMessage {
            point: Point;  // Point field
        }
        """
        schema = self.parser.parse_string(schema_text)
        
        assert schema.namespace.name == "test.comments"
        assert len(schema.structs) == 1
        assert len(schema.messages) == 1
    
    def test_parse_file(self):
        """Test parsing schema from file."""
        schema_text = """
        namespace test.file;
        
        struct TestStruct {
            value: u32;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pico', delete=False) as f:
            f.write(schema_text)
            temp_path = Path(f.name)
        
        try:
            schema = self.parser.parse_file(temp_path)
            assert schema.namespace.name == "test.file"
            assert len(schema.structs) == 1
        finally:
            temp_path.unlink()
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.parser.parse_file("nonexistent.pico")
    
    def test_parse_syntax_error(self):
        """Test parsing schema with syntax errors."""
        schema_text = """
        struct InvalidStruct {
            field_without_type;  // Missing type
        }
        """
        with pytest.raises(ValueError, match="Parse error"):
            self.parser.parse_string(schema_text)
    
    def test_parse_invalid_field_name(self):
        """Test parsing schema with invalid field names."""
        schema_text = """
        struct InvalidFields {
            123invalid: u32;
        }
        """
        with pytest.raises(ValueError):
            self.parser.parse_string(schema_text)
    
    def test_parse_undefined_type_reference(self):
        """Test parsing schema with undefined type references."""
        schema_text = """
        struct TestStruct {
            field: UndefinedType;
        }
        """
        with pytest.raises(ValueError, match="Undefined type"):
            self.parser.parse_string(schema_text)
    
    def test_parse_circular_type_reference(self):
        """Test parsing schema with circular type references."""
        schema_text = """
        struct A {
            b: B;
        }
        
        struct B {
            a: A;
        }
        """
        # This should parse successfully - circular references are allowed
        # (they would be handled at runtime/code generation level)
        schema = self.parser.parse_string(schema_text)
        assert len(schema.structs) == 2
    
    def test_parse_multiple_namespaces_error(self):
        """Test parsing schema with multiple namespace declarations."""
        schema_text = """
        namespace first.namespace;
        namespace second.namespace;
        """
        with pytest.raises(ValueError, match="Multiple namespace declarations"):
            self.parser.parse_string(schema_text)
    
    def test_parse_duplicate_struct_names(self):
        """Test parsing schema with duplicate struct names."""
        schema_text = """
        struct Point {
            x: f32;
        }
        
        struct Point {
            y: f32;
        }
        """
        with pytest.raises(ValueError, match="Duplicate struct names"):
            self.parser.parse_string(schema_text)
    
    def test_parse_duplicate_message_names(self):
        """Test parsing schema with duplicate message names."""
        schema_text = """
        message Test {
            a: u32;
        }
        
        message Test {
            b: u32;
        }
        """
        with pytest.raises(ValueError, match="Duplicate message names"):
            self.parser.parse_string(schema_text)
    
    def test_parse_struct_message_name_conflict(self):
        """Test parsing schema with struct/message name conflicts."""
        schema_text = """
        struct Test {
            x: f32;
        }
        
        message Test {
            y: f32;
        }
        """
        with pytest.raises(ValueError, match="Conflicting enum, struct, and message names"):
            self.parser.parse_string(schema_text)
    
    def test_parse_empty_struct(self):
        """Test parsing empty struct."""
        schema_text = """
        struct Empty {
        }
        """
        schema = self.parser.parse_string(schema_text)
        assert len(schema.structs) == 1
        assert len(schema.structs[0].fields) == 0
    
    def test_parse_empty_message(self):
        """Test parsing empty message."""
        schema_text = """
        message EmptyMessage {
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        assert len(schema.messages) == 1
        message = schema.messages[0]
        assert message.name == "EmptyMessage"
        assert len(message.fields) == 0

    def test_parse_version_declaration(self):
        """Test parsing version declaration."""
        schema_text = """
        version 5;
        namespace test;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        assert schema.version == 5
        assert schema.namespace.name == "test"
        assert len(schema.structs) == 1
        assert schema.structs[0].name == "Point"

    def test_parse_version_only(self):
        """Test parsing schema with only version declaration."""
        schema_text = "version 42;"
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        assert schema.version == 42
        assert schema.namespace is None
        assert len(schema.structs) == 0
        assert len(schema.messages) == 0

    def test_parse_version_with_namespace_order(self):
        """Test parsing version and namespace in different orders."""
        # Version first
        schema_text1 = """
        version 3;
        namespace test.order;
        """
        
        parser = SchemaParser()
        schema1 = parser.parse_string(schema_text1)
        assert schema1.version == 3
        assert schema1.namespace.name == "test.order"
        
        # Namespace first
        schema_text2 = """
        namespace test.order;
        version 3;
        """
        
        schema2 = parser.parse_string(schema_text2)
        assert schema2.version == 3
        assert schema2.namespace.name == "test.order"

    def test_parse_multiple_version_declarations_error(self):
        """Test that multiple version declarations cause an error."""
        schema_text = """
        version 1;
        version 2;
        """
        
        parser = SchemaParser()
        with pytest.raises(ValueError, match="Multiple version declarations not allowed"):
            parser.parse_string(schema_text)

    def test_parse_invalid_version_range(self):
        """Test parsing invalid version numbers."""
        parser = SchemaParser()
        
        # Test version 0 (invalid)
        schema_text = "version 0;"
        with pytest.raises(ValueError, match="Schema version must be between 1 and 255"):
            parser.parse_string(schema_text)
        
        # Test version 256 (invalid)
        schema_text = "version 256;"
        with pytest.raises(ValueError, match="Schema version must be between 1 and 255"):
            parser.parse_string(schema_text)

    def test_parse_schema_without_version(self):
        """Test parsing schema without version declaration."""
        schema_text = """
        namespace test;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        assert schema.version is None
        assert schema.namespace.name == "test"
        assert len(schema.structs) == 1

    def test_parse_basic_enum(self):
        """Test parsing basic enum declaration."""
        schema_text = """
        enum Color : u8 {
            Red = 1,
            Green = 2,
            Blue = 3,
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.enums) == 1
        enum = schema.enums[0]
        assert enum.name == "Color"
        assert enum.backing_type.name == "u8"
        assert len(enum.values) == 3
        
        assert enum.values[0].name == "Red"
        assert enum.values[0].value == 1
        assert enum.values[1].name == "Green"
        assert enum.values[1].value == 2
        assert enum.values[2].name == "Blue"
        assert enum.values[2].value == 3

    def test_parse_enum_auto_increment(self):
        """Test parsing enum with auto-increment values."""
        schema_text = """
        enum Status : u16 {
            Inactive,
            Active = 10,
            Pending,
            Complete = 100,
            Failed,
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.enums) == 1
        enum = schema.enums[0]
        assert enum.backing_type.name == "u16"
        
        # Check auto-increment values
        assert enum.values[0].value == 0   # Inactive
        assert enum.values[1].value == 10  # Active
        assert enum.values[2].value == 11  # Pending
        assert enum.values[3].value == 100 # Complete
        assert enum.values[4].value == 101 # Failed

    def test_parse_enum_in_struct(self):
        """Test parsing enum used in struct fields."""
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
        
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.enums) == 1
        assert len(schema.structs) == 1
        
        task_struct = schema.structs[0]
        priority_field = task_struct.fields[1]
        assert priority_field.name == "priority"
        assert isinstance(priority_field.type, EnumType)
        assert priority_field.type.name == "Priority"

    def test_parse_enum_in_arrays(self):
        """Test parsing enum used in array fields."""
        schema_text = """
        enum Color : u8 {
            Red,
            Green,
            Blue,
        }
        
        message Palette {
            colors: [Color];
            primary: [Color:3];
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.enums) == 1
        assert len(schema.messages) == 1
        
        palette_message = schema.messages[0]
        colors_field = palette_message.fields[0]
        primary_field = palette_message.fields[1]
        
        # Variable array of enums
        assert isinstance(colors_field.type, ArrayType)
        assert isinstance(colors_field.type.element_type, EnumType)
        assert colors_field.type.element_type.name == "Color"
        
        # Fixed array of enums
        assert isinstance(primary_field.type, FixedArrayType)
        assert isinstance(primary_field.type.element_type, EnumType)
        assert primary_field.type.element_type.name == "Color"
        assert primary_field.type.size == 3

    def test_parse_enum_validation_errors(self):
        """Test enum parsing validation errors."""
        # Invalid backing type
        schema_text = """
        enum Color : f32 {
            Red,
        }
        """
        with pytest.raises(ValueError, match="must be an integer type"):
            self.parser.parse_string(schema_text)
        
        # Value out of range for u8
        schema_text = """
        enum Color : u8 {
            Red = 300,
        }
        """
        with pytest.raises(ValueError, match="exceeds maximum"):
            self.parser.parse_string(schema_text)
        
        # Duplicate enum value names
        schema_text = """
        enum Color : u8 {
            Red,
            Red,
        }
        """
        with pytest.raises(ValueError, match="Duplicate enum value names"):
            self.parser.parse_string(schema_text)

    def test_parse_enum_name_conflicts(self):
        """Test enum name conflicts with structs and messages."""
        # Enum-struct conflict
        schema_text = """
        enum Test : u8 {
            Value,
        }
        
        struct Test {
            field: u32;
        }
        """
        with pytest.raises(ValueError, match="Conflicting enum, struct, and message names"):
            self.parser.parse_string(schema_text)
        
        # Enum-message conflict
        schema_text = """
        enum Test : u8 {
            Value,
        }
        
        message Test {
            field: u32;
        }
        """
        with pytest.raises(ValueError, match="Conflicting enum, struct, and message names"):
            self.parser.parse_string(schema_text)

    def test_parse_undefined_enum_reference(self):
        """Test parsing undefined enum reference."""
        schema_text = """
        struct Item {
            color: UndefinedEnum;
        }
        """
        with pytest.raises(ValueError, match="Undefined type"):
            self.parser.parse_string(schema_text)

    def test_parse_multiple_enums(self):
        """Test parsing multiple enum declarations."""
        schema_text = """
        enum Color : u8 {
            Red,
            Green,
            Blue,
        }
        
        enum Size : u16 {
            Small = 100,
            Medium = 200,
            Large = 300,
        }
        
        struct Product {
            color: Color;
            size: Size;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        
        assert len(schema.enums) == 2
        assert len(schema.structs) == 1
        
        color_enum = schema.get_enum("Color")
        size_enum = schema.get_enum("Size")
        
        assert color_enum is not None
        assert color_enum.backing_type.name == "u8"
        assert size_enum is not None
        assert size_enum.backing_type.name == "u16"
        
        product_struct = schema.structs[0]
        assert isinstance(product_struct.fields[0].type, EnumType)
        assert isinstance(product_struct.fields[1].type, EnumType) 
