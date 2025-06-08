"""
Tests for Rust code generator.
"""

import pytest
from picomsg.schema.ast import (
    Schema, Struct, Message, Field, Namespace,
    PrimitiveType, StringType, BytesType, ArrayType, StructType
)
from picomsg.codegen.rust import RustCodeGenerator


def test_rust_generator_basic():
    """Test basic Rust code generation."""
    schema = Schema(enums=[], 
        namespace=Namespace("test.example"),
        structs=[
            Struct("Point", [
                Field("x", PrimitiveType("f32")),
                Field("y", PrimitiveType("f32"))
            ])
        ],
        messages=[
            Message("EchoRequest", [
                Field("point", StructType("Point")),
                Field("id", PrimitiveType("u32"))
            ])
        ]
    )
    
    generator = RustCodeGenerator(schema)
    files = generator.generate()
    
    assert len(files) == 1
    assert "picomsg_generated.rs" in files
    
    content = files["picomsg_generated.rs"]
    
    # Check for proper Rust syntax
    assert "use serde::{Deserialize, Serialize};" in content
    assert "use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};" in content
    
    # Check for proper naming conventions
    assert "pub struct TestExamplePoint {" in content
    assert "pub struct TestExampleEchoRequest {" in content
    assert "pub enum TestExampleError {" in content
    assert "pub trait TestExampleSerialize {" in content
    
    # Check for constants
    assert "pub const TESTEXAMPLE_VERSION: u8 = 1;" in content
    assert "pub const TESTEXAMPLE_ECHOREQUEST_TYPE_ID: u16 = 1;" in content


def test_rust_generator_primitives():
    """Test Rust generation with all primitive types."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("AllTypes", [
                Field("u8_field", PrimitiveType("u8")),
                Field("u16_field", PrimitiveType("u16")),
                Field("u32_field", PrimitiveType("u32")),
                Field("u64_field", PrimitiveType("u64")),
                Field("i8_field", PrimitiveType("i8")),
                Field("i16_field", PrimitiveType("i16")),
                Field("i32_field", PrimitiveType("i32")),
                Field("i64_field", PrimitiveType("i64")),
                Field("f32_field", PrimitiveType("f32")),
                Field("f64_field", PrimitiveType("f64")),
            ])
        ],
        messages=[]
    )
    
    generator = RustCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg_generated.rs"]
    
    # Check struct definition
    assert "pub struct AllTypes {" in content
    assert "pub u8_field: u8," in content
    assert "pub f64_field: f64," in content
    
    # Check serialization methods
    assert "reader.read_u8()?" in content
    assert "reader.read_f64::<LittleEndian>()?" in content
    assert "writer.write_u8(self.u8_field)?" in content
    assert "writer.write_f64::<LittleEndian>(self.f64_field)?" in content


def test_rust_generator_strings_and_bytes():
    """Test Rust generation with string and bytes types."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("StringStruct", [
                Field("name", StringType()),
                Field("data", BytesType()),
            ])
        ],
        messages=[]
    )
    
    generator = RustCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg_generated.rs"]
    
    # Check types
    assert "pub name: String," in content
    assert "pub data: Vec<u8>," in content
    
    # Check string serialization
    assert "let len = reader.read_u16::<LittleEndian>()? as usize;" in content
    assert "String::from_utf8(buf).map_err(|_| PicoMsgError::InvalidData)?" in content
    assert "writer.write_u16::<LittleEndian>(self.name.len() as u16)?;" in content
    assert "writer.write_all(self.name.as_bytes())?;" in content


def test_rust_generator_arrays():
    """Test Rust generation with array types."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("ArrayStruct", [
                Field("numbers", ArrayType(PrimitiveType("u32"))),
                Field("points", ArrayType(StructType("Point"))),
            ])
        ],
        messages=[]
    )
    
    generator = RustCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg_generated.rs"]
    
    # Check types
    assert "pub numbers: Vec<u32>," in content
    assert "pub points: Vec<Point>," in content
    
    # Check array serialization
    assert "let count = reader.read_u16::<LittleEndian>()? as usize;" in content
    assert "writer.write_u16::<LittleEndian>(self.numbers.len() as u16)?;" in content


def test_rust_generator_with_version():
    """Test Rust generation with schema version."""
    schema = Schema(enums=[], 
        namespace=Namespace("test.versioned"),
        structs=[],
        messages=[],
        version=42
    )
    
    generator = RustCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg_generated.rs"]
    
    assert "pub const TESTVERSIONED_VERSION: u8 = 42;" in content


def test_rust_generator_module_name_option():
    """Test Rust generator with custom module name."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("TestStruct", [Field("value", PrimitiveType("u32"))])
        ],
        messages=[]
    )
    
    generator = RustCodeGenerator(schema)
    generator.set_option('module_name', 'custom_module')
    files = generator.generate()
    
    assert "custom_module.rs" in files


def test_rust_generator_no_namespace():
    """Test Rust generation without namespace."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("Point", [
                Field("x", PrimitiveType("f32")),
                Field("y", PrimitiveType("f32"))
            ])
        ],
        messages=[]
    )
    
    generator = RustCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg_generated.rs"]
    
    # Check that types don't have namespace prefix
    assert "pub struct Point {" in content
    assert "pub enum PicoMsgError {" in content
    assert "pub trait PicoMsgSerialize {" in content
    
    # Check constants don't have namespace prefix
    assert "pub const MAGIC_BYTE_1: u8 = 0xAB;" in content


def test_rust_sanitize_identifier():
    """Test Rust identifier sanitization."""
    schema = Schema(enums=[], namespace=None, structs=[], messages=[])
    generator = RustCodeGenerator(schema)
    
    # Test normal identifiers
    assert generator._sanitize_identifier("normal") == "normal"
    assert generator._sanitize_identifier("CamelCase") == "CamelCase"
    
    # Test Rust keywords
    assert generator._sanitize_identifier("type") == "r#type"
    assert generator._sanitize_identifier("match") == "r#match"
    assert generator._sanitize_identifier("async") == "r#async" 
