"""
Tests for JSON validation code generators.
"""

import unittest
from picomsg.schema.parser import SchemaParser
from picomsg.codegen.rust_json import RustJsonCodeGenerator
from picomsg.codegen.python_json import PythonJsonCodeGenerator


class TestJsonValidationGenerators(unittest.TestCase):
    """Test JSON validation code generators."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = SchemaParser()
    
    def test_rust_json_basic_message(self):
        """Test Rust JSON generator with basic message."""
        schema_text = """
        namespace game;
        
        message Player {
            id: u32;
            name: string = "Player";
            health: u32 = 100;
            active: bool = true;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = RustJsonCodeGenerator(schema)
        files = generator.generate()
        
        # Check generated files
        self.assertIn("picomsg_json.rs", files)
        self.assertIn("Cargo.toml", files)
        
        rust_code = files["picomsg_json.rs"]
        cargo_toml = files["Cargo.toml"]
        
        # Check Rust code structure
        self.assertIn("use serde::{Deserialize, Serialize};", rust_code)
        self.assertIn("use validator::{Validate, ValidationError, ValidationErrors};", rust_code)
        self.assertIn("pub struct GamePlayer {", rust_code)
        self.assertIn("#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Validate)]", rust_code)
        
        # Check field validation
        self.assertIn("pub id: u32,", rust_code)
        self.assertIn("pub name: String,", rust_code)
        self.assertIn("pub health: u32,", rust_code)
        self.assertIn("pub active: bool,", rust_code)
        
        # Check validation helpers
        self.assertIn("pub fn validate_json_string", rust_code)
        self.assertIn("pub fn to_validated_json", rust_code)
        
        # Check Cargo.toml
        self.assertIn('name = "game_json"', cargo_toml)
        self.assertIn('serde = { version = "1.0", features = ["derive"] }', cargo_toml)
        self.assertIn('validator = { version = "0.16", features = ["derive"] }', cargo_toml)
    
    def test_python_json_basic_message(self):
        """Test Python JSON generator with basic message."""
        schema_text = """
        namespace game;
        
        message Player {
            id: u32;
            name: string = "Player";
            health: u32 = 100;
            active: bool = true;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonJsonCodeGenerator(schema)
        files = generator.generate()
        
        # Check generated files
        self.assertIn("picomsg_json.py", files)
        self.assertIn("requirements.txt", files)
        
        python_code = files["picomsg_json.py"]
        requirements = files["requirements.txt"]
        
        # Check Python code structure
        self.assertIn("from pydantic import BaseModel, Field, field_validator, ValidationError", python_code)
        self.assertIn("class GamePlayer(BaseModel):", python_code)
        
        # Check field definitions with validation
        self.assertIn("id: conint(ge=0, le=4294967295) = Field(...)", python_code)
        self.assertIn("name: Optional[constr(max_length=65535)] = Field(default='Player')", python_code)
        self.assertIn("health: Optional[conint(ge=0, le=4294967295)] = Field(default=100)", python_code)
        self.assertIn("active: Optional[bool] = Field(default=True)", python_code)
        
        # Check validation helpers
        self.assertIn("def validate_json_string", python_code)
        self.assertIn("def to_validated_json", python_code)
        
        # Check requirements
        self.assertIn("pydantic>=2.0.0", requirements)
    
    def test_rust_json_with_structs(self):
        """Test Rust JSON generator with nested structs."""
        schema_text = """
        namespace test;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message User {
            id: u32;
            location: Point;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = RustJsonCodeGenerator(schema)
        files = generator.generate()
        
        rust_code = files["picomsg_json.rs"]
        
        # Check struct generation
        self.assertIn("pub struct TestPoint {", rust_code)
        self.assertIn("pub x: f32,", rust_code)
        self.assertIn("pub y: f32,", rust_code)
        
        # Check message with struct field
        self.assertIn("pub struct TestUser {", rust_code)
        self.assertIn("pub location: TestPoint,", rust_code)
    
    def test_python_json_with_structs(self):
        """Test Python JSON generator with nested structs."""
        schema_text = """
        namespace test;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message User {
            id: u32;
            location: Point;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonJsonCodeGenerator(schema)
        files = generator.generate()
        
        python_code = files["picomsg_json.py"]
        
        # Check struct generation
        self.assertIn("class TestPoint(BaseModel):", python_code)
        self.assertIn("x: confloat(allow_inf_nan=False) = Field(...)", python_code)
        self.assertIn("y: confloat(allow_inf_nan=False) = Field(...)", python_code)
        
        # Check message with struct field
        self.assertIn("class TestUser(BaseModel):", python_code)
        self.assertIn('location: "TestPoint" = Field(...)', python_code)
    
    def test_rust_json_validation_attributes(self):
        """Test Rust JSON generator validation attributes."""
        schema_text = """
        namespace test;
        
        message ValidationTest {
            small_int: u8 = 255;
            big_int: u64 = 1000;
            name: string = "test";
            scores: [u32];
            coords: [f32:3];
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = RustJsonCodeGenerator(schema)
        files = generator.generate()
        
        rust_code = files["picomsg_json.rs"]
        
        # Check validation attributes
        self.assertIn("#[validate(range(min = 0, max = 255))]", rust_code)
        self.assertIn("#[validate(range(min = 0, max = 18446744073709551615))]", rust_code)
        self.assertIn("#[validate(length(min = 0, max = 65535))]", rust_code)
        self.assertIn("#[validate(length(min = 0, max = 10000))]", rust_code)
        self.assertIn("#[validate(length(min = 3, max = 3))]", rust_code)
    
    def test_python_json_validation_types(self):
        """Test Python JSON generator validation types."""
        schema_text = """
        namespace test;
        
        message ValidationTest {
            small_int: u8 = 255;
            big_int: u64 = 1000;
            name: string = "test";
            scores: [u32];
            coords: [f32:3];
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonJsonCodeGenerator(schema)
        files = generator.generate()
        
        python_code = files["picomsg_json.py"]
        
        # Check validation types
        self.assertIn("conint(ge=0, le=255)", python_code)
        self.assertIn("conint(ge=0, le=18446744073709551615)", python_code)
        self.assertIn("constr(max_length=65535)", python_code)
        self.assertIn("conlist(conint(ge=0, le=4294967295), max_length=10000)", python_code)
        self.assertIn("conlist(confloat(allow_inf_nan=False), min_length=3, max_length=3)", python_code)
    
    def test_rust_json_default_values(self):
        """Test Rust JSON generator with default values."""
        schema_text = """
        namespace test;
        
        message DefaultsTest {
            id: u32;
            name: string = "default";
            count: u32 = 42;
            active: bool = true;
            optional_field: string = null;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = RustJsonCodeGenerator(schema)
        files = generator.generate()
        
        rust_code = files["picomsg_json.rs"]
        
        # Check default value handling
        self.assertIn("pub id: u32,", rust_code)  # Required field
        self.assertIn("pub name: String,", rust_code)  # With default
        self.assertIn("pub count: u32,", rust_code)  # With default
        self.assertIn("pub active: bool,", rust_code)  # With default
        self.assertIn("pub optional_field: String,", rust_code)  # Explicit null
    
    def test_python_json_default_values(self):
        """Test Python JSON generator with default values."""
        schema_text = """
        namespace test;
        
        message DefaultsTest {
            id: u32;
            name: string = "default";
            count: u32 = 42;
            active: bool = true;
            optional_field: string = null;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonJsonCodeGenerator(schema)
        files = generator.generate()
        
        python_code = files["picomsg_json.py"]
        
        # Check default value handling
        self.assertIn("id: conint(ge=0, le=4294967295) = Field(...)", python_code)  # Required
        self.assertIn("name: Optional[constr(max_length=65535)] = Field(default='default')", python_code)
        self.assertIn("count: Optional[conint(ge=0, le=4294967295)] = Field(default=42)", python_code)
        self.assertIn("active: Optional[bool] = Field(default=True)", python_code)
        self.assertIn("optional_field: Optional[constr(max_length=65535)] = Field(default=None)", python_code)
    

    
    def test_generator_options(self):
        """Test generator options."""
        schema_text = """
        namespace test;
        message Simple { id: u32; }
        """
        
        schema = self.parser.parse_string(schema_text)
        
        # Test Rust generator with custom module name
        rust_generator = RustJsonCodeGenerator(schema)
        rust_generator.set_option('module_name', 'custom_rust')
        rust_files = rust_generator.generate()
        self.assertIn("custom_rust.rs", rust_files)
        
        # Test Python generator with custom module name
        python_generator = PythonJsonCodeGenerator(schema)
        python_generator.set_option('module_name', 'custom_python')
        python_files = python_generator.generate()
        self.assertIn("custom_python.py", python_files)


if __name__ == '__main__':
    unittest.main() 
