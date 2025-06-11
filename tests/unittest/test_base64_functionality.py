"""
Tests for base64 functionality in generated code.
"""

import pytest
import tempfile
import sys
import base64
from pathlib import Path
from unittest.mock import patch

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator
from picomsg.codegen.rust import RustCodeGenerator


class TestBase64Functionality:
    """Test base64 encoding/decoding functionality in generated code."""
    
    def test_python_base64_methods_generation(self):
        """Test that Python code generator includes base64 methods."""
        schema_content = """
        namespace test.base64;
        version 1;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message TestMessage {
            id: u32;
            point: Point;
            data: bytes;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        assert len(files) == 1
        code = files["picomsg_generated.py"]
        
        # Check for base64 import
        assert "import base64" in code
        
        # Check for base64 methods in base class
        assert "def to_base64(self) -> str:" in code
        assert "base64.b64encode(self.to_bytes()).decode(\"ascii\")" in code
        assert "def from_base64(cls, base64_str: str) -> \"Self\":" in code
        assert "base64.b64decode(base64_str.encode(\"ascii\"))" in code
    
    def test_rust_base64_methods_generation(self):
        """Test that Rust code generator includes base64 methods."""
        schema_content = """
        namespace test.base64;
        version 1;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message TestMessage {
            id: u32;
            point: Point;
            data: bytes;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = RustCodeGenerator(schema)
        files = generator.generate()
        
        assert len(files) == 1
        code = files["picomsg_generated.rs"]
        
        # Check for base64 import
        assert "use base64::{Engine as _, engine::general_purpose};" in code
        
        # Check for base64 methods in trait
        assert "fn to_base64(&self) -> TestBase64Result<String>;" in code
        assert "fn from_base64(base64_str: &str) -> TestBase64Result<Self> where Self: Sized;" in code
        
        # Check for base64 implementations
        assert "fn to_base64(&self) -> TestBase64Result<String> {" in code
        assert "general_purpose::STANDARD.encode(&bytes)" in code
        assert "fn from_base64(base64_str: &str) -> TestBase64Result<Self> {" in code
        assert "general_purpose::STANDARD.decode(base64_str)" in code
    
    def test_python_base64_roundtrip_execution(self):
        """Test that generated Python code can perform base64 roundtrip."""
        schema_content = """
        namespace test.roundtrip;
        version 1;
        
        struct SimpleStruct {
            value: u32;
            name: string;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Execute the generated code
        with tempfile.TemporaryDirectory() as temp_dir:
            module_path = Path(temp_dir) / "test_module.py"
            module_path.write_text(code)
            
            # Add temp directory to Python path
            sys.path.insert(0, str(temp_dir))
            
            try:
                import test_module
                
                # Create an instance
                original = test_module.TestRoundtripSimpleStruct(value=42, name="test")
                
                # Convert to base64
                base64_str = original.to_base64()
                assert isinstance(base64_str, str)
                assert len(base64_str) > 0
                
                # Verify it's valid base64
                base64.b64decode(base64_str)  # Should not raise exception
                
                # Convert back from base64
                restored = test_module.TestRoundtripSimpleStruct.from_base64(base64_str)
                
                # Verify the data matches
                assert restored.value == 42
                assert restored.name == "test"
                
                # Test with binary data roundtrip
                binary_data = original.to_bytes()
                base64_from_binary = base64.b64encode(binary_data).decode('ascii')
                assert base64_str == base64_from_binary
                
            finally:
                # Clean up
                if 'test_module' in sys.modules:
                    del sys.modules['test_module']
                sys.path.remove(str(temp_dir))
    
    def test_python_base64_with_complex_data(self):
        """Test base64 functionality with complex data structures."""
        schema_content = """
        namespace test.complex;
        version 1;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message ComplexMessage {
            id: u32;
            points: [Point];
            data: bytes;
            name: string;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Execute the generated code
        with tempfile.TemporaryDirectory() as temp_dir:
            module_path = Path(temp_dir) / "test_module.py"
            module_path.write_text(code)
            
            sys.path.insert(0, str(temp_dir))
            
            try:
                import test_module
                
                # Create complex data
                point1 = test_module.TestComplexPoint(x=1.5, y=2.5)
                point2 = test_module.TestComplexPoint(x=3.5, y=4.5)
                
                original = test_module.TestComplexComplexMessage(
                    id=123,
                    points=[point1, point2],
                    data=b"binary data here",
                    name="complex test"
                )
                
                # Convert to base64 and back
                base64_str = original.to_base64()
                restored = test_module.TestComplexComplexMessage.from_base64(base64_str)
                
                # Verify all data matches
                assert restored.id == 123
                assert len(restored.points) == 2
                assert restored.points[0].x == 1.5
                assert restored.points[0].y == 2.5
                assert restored.points[1].x == 3.5
                assert restored.points[1].y == 4.5
                assert restored.data == b"binary data here"
                assert restored.name == "complex test"
                
            finally:
                if 'test_module' in sys.modules:
                    del sys.modules['test_module']
                sys.path.remove(str(temp_dir))
    
    def test_python_base64_error_handling(self):
        """Test base64 error handling in Python generated code."""
        schema_content = """
        namespace test.errors;
        version 1;
        
        struct SimpleStruct {
            value: u32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Execute the generated code
        with tempfile.TemporaryDirectory() as temp_dir:
            module_path = Path(temp_dir) / "test_module.py"
            module_path.write_text(code)
            
            sys.path.insert(0, str(temp_dir))
            
            try:
                import test_module
                
                # Test invalid base64 string
                with pytest.raises(Exception):  # Should raise base64 decode error
                    test_module.TestErrorsSimpleStruct.from_base64("invalid base64!")
                
                # Test empty base64 string
                with pytest.raises(Exception):
                    test_module.TestErrorsSimpleStruct.from_base64("")
                
            finally:
                if 'test_module' in sys.modules:
                    del sys.modules['test_module']
                sys.path.remove(str(temp_dir))
    
    def test_rust_base64_trait_methods(self):
        """Test that Rust trait includes proper base64 method signatures."""
        schema_content = """
        namespace api.v1;
        version 2;
        
        struct Config {
            timeout: u32;
            enabled: bool;
        }
        
        message Request {
            config: Config;
            payload: bytes;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = RustCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.rs"]
        
        # Check trait definition
        assert "pub trait ApiV1Serialize {" in code
        assert "fn to_base64(&self) -> ApiV1Result<String>;" in code
        assert "fn from_base64(base64_str: &str) -> ApiV1Result<Self> where Self: Sized;" in code
        
        # Check struct implementation
        assert "impl ApiV1Serialize for ApiV1Config {" in code
        assert "fn to_base64(&self) -> ApiV1Result<String> {" in code
        assert "let bytes = self.to_bytes()?;" in code
        assert "Ok(general_purpose::STANDARD.encode(&bytes))" in code
        
        assert "fn from_base64(base64_str: &str) -> ApiV1Result<Self> {" in code
        assert "let bytes = general_purpose::STANDARD.decode(base64_str)" in code
        assert ".map_err(|_| ApiV1Error::InvalidData)?;" in code
        assert "Self::from_bytes(&bytes)" in code
        
        # Check message implementation
        assert "impl ApiV1Serialize for ApiV1Request {" in code
    
    def test_no_namespace_base64_generation(self):
        """Test base64 generation without namespace."""
        schema_content = """
        version 1;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        # Test Python generation
        python_generator = PythonCodeGenerator(schema)
        python_files = python_generator.generate()
        python_code = python_files["picomsg_generated.py"]
        
        assert "class PicoMsgBase:" in python_code
        assert "def to_base64(self) -> str:" in python_code
        assert "def from_base64(cls, base64_str: str) -> \"Self\":" in python_code
        
        # Test Rust generation
        rust_generator = RustCodeGenerator(schema)
        rust_files = rust_generator.generate()
        rust_code = rust_files["picomsg_generated.rs"]
        
        assert "pub trait PicoMsgSerialize {" in rust_code
        assert "fn to_base64(&self) -> PicoMsgResult<String>;" in rust_code
        assert "fn from_base64(base64_str: &str) -> PicoMsgResult<Self> where Self: Sized;" in rust_code
        assert "impl PicoMsgSerialize for Point {" in rust_code
        assert ".map_err(|_| PicoMsgError::InvalidData)?;" in rust_code
    
    def test_base64_with_enums(self):
        """Test base64 functionality with enums."""
        schema_content = """
        namespace test.enums;
        version 1;
        
        enum Status : u8 {
            Active = 1,
            Inactive = 2,
            Pending = 3
        }
        
        struct StatusMessage {
            id: u32;
            status: Status;
            message: string;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        # Test Python generation
        python_generator = PythonCodeGenerator(schema)
        python_files = python_generator.generate()
        python_code = python_files["picomsg_generated.py"]
        
        assert "def to_base64(self) -> str:" in python_code
        assert "def from_base64(cls, base64_str: str) -> \"Self\":" in python_code
        
        # Test Rust generation
        rust_generator = RustCodeGenerator(schema)
        rust_files = rust_generator.generate()
        rust_code = rust_files["picomsg_generated.rs"]
        
        assert "fn to_base64(&self) -> TestEnumsResult<String>;" in rust_code
        assert "fn from_base64(base64_str: &str) -> TestEnumsResult<Self> where Self: Sized;" in rust_code
        
        # Check enum definition is present
        assert "pub enum TestEnumsStatus {" in rust_code
        assert "Active = 1," in rust_code
        assert "Inactive = 2," in rust_code
        assert "Pending = 3," in rust_code
    
    def test_python_base64_with_arrays(self):
        """Test Python base64 functionality with arrays."""
        schema_content = """
        namespace test.arrays;
        version 1;
        
        struct ArrayStruct {
            numbers: [u32];
            names: [string];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Execute the generated code
        with tempfile.TemporaryDirectory() as temp_dir:
            module_path = Path(temp_dir) / "test_module.py"
            module_path.write_text(code)
            
            sys.path.insert(0, str(temp_dir))
            
            try:
                import test_module
                
                # Create instance with arrays
                original = test_module.TestArraysArrayStruct(
                    numbers=[1, 2, 3, 4, 5],
                    names=["hello", "world", "test"]
                )
                
                # Convert to base64 and back
                base64_str = original.to_base64()
                restored = test_module.TestArraysArrayStruct.from_base64(base64_str)
                
                # Verify arrays match
                assert restored.numbers == [1, 2, 3, 4, 5]
                assert restored.names == ["hello", "world", "test"]
                
            finally:
                if 'test_module' in sys.modules:
                    del sys.modules['test_module']
                sys.path.remove(str(temp_dir)) 
