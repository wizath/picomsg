"""
Tests for default values functionality.
"""

import pytest
import tempfile
from pathlib import Path

from picomsg.schema.parser import SchemaParser
from picomsg.schema.ast import Field, PrimitiveType, StringType, ArrayType
from picomsg.codegen.c import CCodeGenerator


class TestDefaultValues:
    """Test default values in schema parsing and code generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SchemaParser()
    
    def test_parse_primitive_defaults(self):
        """Test parsing primitive type default values."""
        schema_text = """
        namespace test.defaults;
        
        message Config {
            port: u16 = 8080;
            timeout: u32 = 30;
            debug: bool = true;
            rate: f32 = 1.5;
            name: string = "default";
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        config = schema.messages[0]
        
        assert config.name == "Config"
        assert len(config.fields) == 5
        
        # Check port field
        port_field = config.fields[0]
        assert port_field.name == "port"
        assert port_field.default_value == 8080
        assert port_field.has_default()
        assert not port_field.is_required()
        
        # Check timeout field
        timeout_field = config.fields[1]
        assert timeout_field.name == "timeout"
        assert timeout_field.default_value == 30
        
        # Check debug field
        debug_field = config.fields[2]
        assert debug_field.name == "debug"
        assert debug_field.default_value is True
        
        # Check rate field
        rate_field = config.fields[3]
        assert rate_field.name == "rate"
        assert rate_field.default_value == 1.5
        
        # Check name field
        name_field = config.fields[4]
        assert name_field.name == "name"
        assert name_field.default_value == "default"
    
    def test_parse_no_defaults(self):
        """Test parsing fields without default values."""
        schema_text = """
        namespace test.defaults;
        
        message User {
            id: u32;
            email: string;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        user = schema.messages[0]
        
        # Check id field (no default)
        id_field = user.fields[0]
        assert id_field.name == "id"
        assert id_field.default_value is None
        assert not id_field.has_default()
        assert id_field.is_required()
        
        # Check email field (no default)
        email_field = user.fields[1]
        assert email_field.name == "email"
        assert email_field.default_value is None
        assert not email_field.has_default()
        assert id_field.is_required()
    
    def test_parse_null_default(self):
        """Test parsing null default values."""
        schema_text = """
        namespace test.defaults;
        
        message Profile {
            bio: string = null;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        profile = schema.messages[0]
        
        bio_field = profile.fields[0]
        assert bio_field.name == "bio"
        assert bio_field.default_value is None
        assert bio_field.has_default()  # null is a valid default
    
    def test_parse_boolean_defaults(self):
        """Test parsing boolean default values."""
        schema_text = """
        namespace test.defaults;
        
        message Settings {
            enabled: bool = true;
            disabled: bool = false;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        settings = schema.messages[0]
        
        enabled_field = settings.fields[0]
        assert enabled_field.default_value is True
        
        disabled_field = settings.fields[1]
        assert disabled_field.default_value is False
    
    def test_parse_string_defaults(self):
        """Test parsing string default values with escapes."""
        schema_text = '''
        namespace test.defaults;
        
        message Text {
            simple: string = "hello";
            escaped: string = "line1\\nline2";
            quoted: string = "say \\"hello\\"";
        }
        '''
        
        schema = self.parser.parse_string(schema_text)
        text = schema.messages[0]
        
        simple_field = text.fields[0]
        assert simple_field.default_value == "hello"
        
        escaped_field = text.fields[1]
        assert escaped_field.default_value == "line1\nline2"
        
        quoted_field = text.fields[2]
        assert quoted_field.default_value == 'say "hello"'
    
    def test_parse_numeric_defaults(self):
        """Test parsing various numeric default values."""
        schema_text = """
        namespace test.defaults;
        
        message Numbers {
            small: u8 = 255;
            large: u64 = 9223372036854775807;
            negative: i32 = -42;
            float_val: f32 = 3.14159;
            double_val: f64 = 2.718281828;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        numbers = schema.messages[0]
        
        assert numbers.fields[0].default_value == 255
        assert numbers.fields[1].default_value == 9223372036854775807
        assert numbers.fields[2].default_value == -42
        assert numbers.fields[3].default_value == 3.14159
        assert numbers.fields[4].default_value == 2.718281828
    
    def test_validation_integer_range(self):
        """Test validation of integer default values within type ranges."""
        # Valid u8 range
        schema_text = """
        namespace test.defaults;
        message Test { value: u8 = 255; }
        """
        schema = self.parser.parse_string(schema_text)  # Should not raise
        
        # Invalid u8 range
        with pytest.raises(ValueError, match="out of range"):
            schema_text = """
            namespace test.defaults;
            message Test { value: u8 = 256; }
            """
            self.parser.parse_string(schema_text)
        
        # Valid i8 range
        schema_text = """
        namespace test.defaults;
        message Test { value: i8 = -128; }
        """
        schema = self.parser.parse_string(schema_text)  # Should not raise
        
        # Invalid i8 range
        with pytest.raises(ValueError, match="out of range"):
            schema_text = """
            namespace test.defaults;
            message Test { value: i8 = -129; }
            """
            self.parser.parse_string(schema_text)
    
    def test_validation_type_mismatch(self):
        """Test validation of type mismatches in default values."""
        # String default for integer field
        with pytest.raises(ValueError, match="must be an integer"):
            schema_text = """
            namespace test.defaults;
            message Test { value: u32 = "not a number"; }
            """
            self.parser.parse_string(schema_text)
        
        # Integer default for boolean field
        with pytest.raises(ValueError, match="must be true or false"):
            schema_text = """
            namespace test.defaults;
            message Test { flag: bool = 1; }
            """
            self.parser.parse_string(schema_text)
        
        # String default for float field
        with pytest.raises(ValueError, match="must be a number"):
            schema_text = """
            namespace test.defaults;
            message Test { value: f32 = "3.14"; }
            """
            self.parser.parse_string(schema_text)
    
    def test_validation_unsupported_defaults(self):
        """Test validation that arrays and bytes don't support defaults."""
        # Array default not supported - should fail at parse time
        with pytest.raises(ValueError, match="Parse error"):
            schema_text = """
            namespace test.defaults;
            message Test { items: [u32] = [1, 2, 3]; }
            """
            self.parser.parse_string(schema_text)
        
        # Fixed array default not supported - should fail at parse time
        with pytest.raises(ValueError, match="Parse error"):
            schema_text = """
            namespace test.defaults;
            message Test { coords: [f32:3] = [1.0, 2.0, 3.0]; }
            """
            self.parser.parse_string(schema_text)
        
        # Bytes default not supported - should fail at validation time
        with pytest.raises(ValueError, match="Default values not supported"):
            schema_text = """
            namespace test.defaults;
            message Test { data: bytes = "hello"; }
            """
            self.parser.parse_string(schema_text)
    
    def test_c_code_generation_with_defaults(self):
        """Test C code generation with default values."""
        schema_text = """
        namespace test.defaults;
        
        message Player {
            id: u32;
            health: u32 = 100;
            mana: u32 = 50;
            name: string = "Player";
            active: bool = true;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = CCodeGenerator(schema)
        files = generator.generate()
        
        header_content = files["picomsg_generated.h"]
        
        # Check that initialization macro is generated
        assert "PLAYER_INIT" in header_content
        assert "test_defaults_player_t" in header_content
        
        # Check default values in macro
        assert ".id = 0" in header_content  # No default = 0
        assert ".health = 100" in header_content
        assert ".mana = 50" in header_content
        assert '.name = "Player"' in header_content
        assert ".active = true" in header_content
        
        # Check macro structure
        assert "__VA_ARGS__" in header_content
    
    def test_c_code_generation_no_defaults(self):
        """Test C code generation without default values."""
        schema_text = """
        namespace test.defaults;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = CCodeGenerator(schema)
        files = generator.generate()
        
        header_content = files["picomsg_generated.h"]
        
        # Check that initialization macro is generated with zeros
        assert "POINT_INIT" in header_content
        assert ".x = 0" in header_content
        assert ".y = 0" in header_content
    
    def test_mixed_defaults_and_required(self):
        """Test mixing fields with and without defaults."""
        schema_text = """
        namespace test.defaults;
        
        message Order {
            id: u32;              // Required
            quantity: u32 = 1;    // Default
            priority: u8 = 5;     // Default
            notes: string;        // Required
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        order = schema.messages[0]
        
        # Check required fields
        assert order.fields[0].is_required()  # id
        assert order.fields[3].is_required()  # notes
        
        # Check fields with defaults
        assert order.fields[1].has_default()  # quantity
        assert order.fields[2].has_default()  # priority
        
        # Check default values
        assert order.fields[1].default_value == 1
        assert order.fields[2].default_value == 5 
