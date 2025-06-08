"""
Unit tests for JSON conversion system.
"""

import unittest
import json
import tempfile
import io
from pathlib import Path

from picomsg.schema.parser import SchemaParser
from picomsg.json import (
    SchemaAwareJSONConverter, create_converter, 
    JSONValidationError, JSONConversionError, JSONStreamingError
)
from picomsg.json.streaming import StreamingJSONParser, StreamingJSONWriter


class TestSchemaAwareJSONConverter(unittest.TestCase):
    """Test the schema-aware JSON converter."""
    
    def setUp(self):
        """Set up test schema."""
        schema_content = '''
        namespace test;
        
        struct Config {
            name: string;
            port: u16;
            enabled: u8;
        }
        
        struct Stats {
            count: u32;
            average: f32;
            values: [u32];
        }
        
        message Request {
            id: u64;
            config: Config;
            timestamp: u64;
        }
        '''
        
        self.schema_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pico', delete=False)
        self.schema_file.write(schema_content)
        self.schema_file.close()
        
        parser = SchemaParser()
        self.schema = parser.parse_file(Path(self.schema_file.name))
        self.converter = SchemaAwareJSONConverter(self.schema)
    
    def tearDown(self):
        """Clean up test files."""
        Path(self.schema_file.name).unlink()
    
    def test_validate_valid_json(self):
        """Test validation of valid JSON data."""
        valid_config = {
            "name": "test-server",
            "port": 8080,
            "enabled": 1
        }
        
        # Should not raise an exception
        result = self.converter.validate_json(valid_config, "Config")
        self.assertTrue(result)
    
    def test_validate_missing_field(self):
        """Test validation with missing required field."""
        invalid_config = {
            "name": "test-server",
            "port": 8080
            # Missing 'enabled' field
        }
        
        with self.assertRaises(JSONValidationError) as cm:
            self.converter.validate_json(invalid_config, "Config")
        
        self.assertIn("Missing required field: enabled", str(cm.exception))
    
    def test_validate_extra_field(self):
        """Test validation with extra field."""
        invalid_config = {
            "name": "test-server",
            "port": 8080,
            "enabled": 1,
            "extra_field": "not allowed"
        }
        
        with self.assertRaises(JSONValidationError) as cm:
            self.converter.validate_json(invalid_config, "Config")
        
        self.assertIn("Unexpected fields", str(cm.exception))
    
    def test_validate_wrong_type(self):
        """Test validation with wrong field type."""
        invalid_config = {
            "name": "test-server",
            "port": "not a number",  # Should be u16
            "enabled": 1
        }
        
        with self.assertRaises(JSONValidationError) as cm:
            self.converter.validate_json(invalid_config, "Config")
        
        self.assertIn("must be an integer", str(cm.exception))
    
    def test_validate_out_of_range(self):
        """Test validation with out-of-range values."""
        invalid_config = {
            "name": "test-server",
            "port": 70000,  # Exceeds u16 max (65535)
            "enabled": 1
        }
        
        with self.assertRaises(JSONValidationError) as cm:
            self.converter.validate_json(invalid_config, "Config")
        
        self.assertIn("out of range for u16", str(cm.exception))
    
    def test_validate_array_type(self):
        """Test validation of array types."""
        valid_stats = {
            "count": 100,
            "average": 42.5,
            "values": [1, 2, 3, 4, 5]
        }
        
        result = self.converter.validate_json(valid_stats, "Stats")
        self.assertTrue(result)
        
        # Test invalid array element
        invalid_stats = {
            "count": 100,
            "average": 42.5,
            "values": [1, 2, "not a number", 4, 5]
        }
        
        with self.assertRaises(JSONValidationError) as cm:
            self.converter.validate_json(invalid_stats, "Stats")
        
        self.assertIn("values[2]", str(cm.exception))
    
    def test_validate_nested_struct(self):
        """Test validation of nested struct types."""
        valid_request = {
            "id": 12345,
            "config": {
                "name": "test-server",
                "port": 8080,
                "enabled": 1
            },
            "timestamp": 1640995200
        }
        
        result = self.converter.validate_json(valid_request, "Request")
        self.assertTrue(result)
        
        # Test invalid nested struct
        invalid_request = {
            "id": 12345,
            "config": {
                "name": "test-server",
                "port": "invalid"  # Wrong type
            },
            "timestamp": 1640995200
        }
        
        with self.assertRaises(JSONValidationError):
            self.converter.validate_json(invalid_request, "Request")
    
    def test_pretty_print(self):
        """Test pretty-printing with schema annotations."""
        config_data = {
            "name": "test-server",
            "port": 8080,
            "enabled": 1
        }
        
        pretty_json = self.converter.pretty_print(config_data, "Config")
        
        # Should be valid JSON
        parsed = json.loads(pretty_json)
        self.assertIn("$schema_type", parsed)
        self.assertEqual(parsed["$schema_type"], "Config")
        self.assertEqual(parsed["name"], "test-server")
    
    def test_type_coercion(self):
        """Test type coercion functionality."""
        config_data = {
            "name": "test-server",
            "port": "8080",  # String that should be coerced to int
            "enabled": 1
        }
        
        coerced = self.converter.coerce_types(config_data, "Config")
        
        self.assertEqual(coerced["port"], 8080)
        self.assertIsInstance(coerced["port"], int)
    
    def test_unknown_type(self):
        """Test validation with unknown type name."""
        with self.assertRaises(JSONValidationError) as cm:
            self.converter.validate_json({}, "UnknownType")
        
        self.assertIn("Unknown type: UnknownType", str(cm.exception))


class TestStreamingJSONParser(unittest.TestCase):
    """Test the streaming JSON parser."""
    
    def setUp(self):
        """Set up test data."""
        self.parser = StreamingJSONParser()
    
    def test_parse_json_array_stream(self):
        """Test parsing JSON array stream."""
        json_array = '''[
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2},
            {"name": "item3", "value": 3}
        ]'''
        
        stream = io.StringIO(json_array)
        objects = list(self.parser.parse_json_array_stream(stream, validate=False))
        
        self.assertEqual(len(objects), 3)
        self.assertEqual(objects[0]["name"], "item1")
        self.assertEqual(objects[1]["value"], 2)
    
    def test_parse_empty_json_array(self):
        """Test parsing empty JSON array."""
        json_array = '[]'
        
        stream = io.StringIO(json_array)
        objects = list(self.parser.parse_json_array_stream(stream, validate=False))
        
        self.assertEqual(len(objects), 0)
    
    def test_parse_json_lines_stream(self):
        """Test parsing JSON Lines stream."""
        json_lines = '''{"name": "item1", "value": 1}
{"name": "item2", "value": 2}
{"name": "item3", "value": 3}'''
        
        stream = io.StringIO(json_lines)
        objects = list(self.parser.parse_json_lines_stream(stream, validate=False))
        
        self.assertEqual(len(objects), 3)
        self.assertEqual(objects[0]["name"], "item1")
        self.assertEqual(objects[2]["value"], 3)
    
    def test_parse_json_lines_with_empty_lines(self):
        """Test parsing JSON Lines with empty lines."""
        json_lines = '''{"name": "item1", "value": 1}

{"name": "item2", "value": 2}

{"name": "item3", "value": 3}'''
        
        stream = io.StringIO(json_lines)
        objects = list(self.parser.parse_json_lines_stream(stream, validate=False))
        
        self.assertEqual(len(objects), 3)
    
    def test_parse_invalid_json_array(self):
        """Test parsing invalid JSON array."""
        invalid_json = '[{"name": "item1", "value": 1'  # Missing closing brace and bracket
        
        stream = io.StringIO(invalid_json)
        
        with self.assertRaises(JSONStreamingError):
            list(self.parser.parse_json_array_stream(stream, validate=False))
    
    def test_parse_invalid_json_lines(self):
        """Test parsing invalid JSON Lines."""
        invalid_json_lines = '''{"name": "item1", "value": 1}
{"name": "item2", "value":}
{"name": "item3", "value": 3}'''
        
        stream = io.StringIO(invalid_json_lines)
        
        with self.assertRaises(JSONStreamingError) as cm:
            list(self.parser.parse_json_lines_stream(stream, validate=False))
        
        self.assertIn("line 2", str(cm.exception).lower())


class TestStreamingJSONWriter(unittest.TestCase):
    """Test the streaming JSON writer."""
    
    def test_write_json_array(self):
        """Test writing JSON array."""
        output = io.StringIO()
        writer = StreamingJSONWriter(output)
        
        objects = [
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2},
            {"name": "item3", "value": 3}
        ]
        
        writer.start_array()
        for obj in objects:
            writer.write_object(obj)
        writer.end_array()
        
        result = output.getvalue()
        parsed = json.loads(result)
        
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]["name"], "item1")
    
    def test_write_pretty_json_array(self):
        """Test writing pretty-printed JSON array."""
        output = io.StringIO()
        writer = StreamingJSONWriter(output, indent=2)
        
        objects = [
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2}
        ]
        
        writer.start_array()
        for obj in objects:
            writer.write_object(obj)
        writer.end_array()
        
        result = output.getvalue()
        
        # Should contain newlines and indentation
        self.assertIn('\n', result)
        self.assertIn('  ', result)
        
        # Should still be valid JSON
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 2)
    
    def test_write_json_lines(self):
        """Test writing JSON Lines format."""
        output = io.StringIO()
        writer = StreamingJSONWriter(output)
        
        objects = [
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2},
            {"name": "item3", "value": 3}
        ]
        
        writer.write_json_lines(iter(objects))
        
        result = output.getvalue()
        lines = result.strip().split('\n')
        
        self.assertEqual(len(lines), 3)
        
        # Each line should be valid JSON
        for i, line in enumerate(lines):
            obj = json.loads(line)
            self.assertEqual(obj["name"], f"item{i+1}")
    
    def test_write_without_start_array(self):
        """Test writing object without starting array."""
        output = io.StringIO()
        writer = StreamingJSONWriter(output)
        
        with self.assertRaises(JSONStreamingError):
            writer.write_object({"test": "data"})


class TestJSONUtilityFunctions(unittest.TestCase):
    """Test JSON utility functions."""
    
    def setUp(self):
        """Set up test schema file."""
        schema_content = '''
        namespace test;
        
        struct SimpleConfig {
            name: string;
            value: u32;
        }
        '''
        
        self.schema_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pico', delete=False)
        self.schema_file.write(schema_content)
        self.schema_file.close()
    
    def tearDown(self):
        """Clean up test files."""
        Path(self.schema_file.name).unlink()
    
    def test_create_converter(self):
        """Test creating converter from schema file."""
        converter = create_converter(self.schema_file.name)
        
        self.assertIsInstance(converter, SchemaAwareJSONConverter)
        
        # Test validation works
        valid_data = {"name": "test", "value": 42}
        result = converter.validate_json(valid_data, "SimpleConfig")
        self.assertTrue(result)
    
    def test_validate_json_file(self):
        """Test validating JSON file."""
        from picomsg.json import validate_json_file
        
        # Create test JSON file
        json_data = {"name": "test", "value": 42}
        json_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(json_data, json_file)
        json_file.close()
        
        try:
            result = validate_json_file(json_file.name, "SimpleConfig", self.schema_file.name)
            self.assertTrue(result)
        finally:
            Path(json_file.name).unlink()
    
    def test_pretty_print_json_file(self):
        """Test pretty-printing JSON file."""
        from picomsg.json import pretty_print_json_file
        
        # Create test JSON file
        json_data = {"name": "test", "value": 42}
        json_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(json_data, json_file)
        json_file.close()
        
        try:
            formatted = pretty_print_json_file(json_file.name, "SimpleConfig", self.schema_file.name)
            
            # Should be valid JSON with schema annotation
            parsed = json.loads(formatted)
            self.assertIn("$schema_type", parsed)
            self.assertEqual(parsed["name"], "test")
        finally:
            Path(json_file.name).unlink()


if __name__ == '__main__':
    unittest.main() 
