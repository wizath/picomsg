"""
Tests for JSON streaming functionality.
"""

import pytest
import tempfile
import json
import io
from pathlib import Path

from picomsg.json.streaming import (
    StreamingJSONParser, StreamingJSONWriter,
    stream_validate_json_array, stream_convert_json_lines_to_array,
    stream_convert_json_array_to_lines
)
from picomsg.json import JSONStreamingError, SchemaAwareJSONConverter
from picomsg.schema.parser import SchemaParser


class TestStreamingJSONFunctionality:
    """Test streaming JSON functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.schema_content = """
        namespace test.streaming;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        parser = SchemaParser()
        self.schema = parser.parse_string(self.schema_content)
        self.converter = SchemaAwareJSONConverter(self.schema)
    
    def create_test_json_file(self, data) -> Path:
        """Create a temporary JSON file with given data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(data, temp_file)
        temp_file.close()
        return Path(temp_file.name)
    
    def create_test_json_lines_file(self, data_list: list) -> Path:
        """Create a temporary JSON Lines file with given data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        for item in data_list:
            json.dump(item, temp_file)
            temp_file.write('\n')
        temp_file.close()
        return Path(temp_file.name)
    
    def create_test_schema_file(self) -> Path:
        """Create a temporary schema file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pico', delete=False)
        temp_file.write(self.schema_content)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_stream_validate_json_array_valid(self):
        """Test streaming validation of valid JSON array."""
        json_data = [
            {"x": 1.0, "y": 2.0},
            {"x": 3.0, "y": 4.0},
            {"x": 5.0, "y": 6.0}
        ]
        
        json_file = self.create_test_json_file(json_data)
        schema_file = self.create_test_schema_file()
        
        try:
            result = stream_validate_json_array(json_file, "Point", schema_file)
            assert result is True
        finally:
            json_file.unlink()
            schema_file.unlink()
    
    def test_stream_validate_json_array_invalid(self):
        """Test streaming validation of invalid JSON array."""
        json_data = [
            {"x": 1.0, "y": 2.0},
            {"x": "invalid", "y": 4.0},
            {"x": 5.0, "y": 6.0}
        ]
        
        json_file = self.create_test_json_file(json_data)
        schema_file = self.create_test_schema_file()
        
        try:
            result = stream_validate_json_array(json_file, "Point", schema_file)
            assert result is False
        finally:
            json_file.unlink()
            schema_file.unlink()
    
    def test_stream_validate_json_array_empty(self):
        """Test streaming validation of empty JSON array."""
        json_data = []
        
        json_file = self.create_test_json_file(json_data)
        schema_file = self.create_test_schema_file()
        
        try:
            result = stream_validate_json_array(json_file, "Point", schema_file)
            assert result is True
        finally:
            json_file.unlink()
            schema_file.unlink()
    

    
    def test_stream_convert_json_lines_to_array(self):
        """Test converting JSON Lines to array format."""
        json_data = [
            {"x": 1.0, "y": 2.0},
            {"x": 3.0, "y": 4.0},
            {"x": 5.0, "y": 6.0}
        ]
        
        input_file = self.create_test_json_lines_file(json_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            stream_convert_json_lines_to_array(input_file, output_path)
            
            assert output_path.exists()
            with open(output_path) as f:
                result_data = json.load(f)
                assert len(result_data) == 3
                assert result_data[0]["x"] == 1.0
                assert result_data[1]["x"] == 3.0
                assert result_data[2]["x"] == 5.0
        finally:
            input_file.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_stream_convert_json_lines_to_array_with_validation(self):
        """Test converting JSON Lines to array with validation."""
        json_data = [
            {"x": 1.0, "y": 2.0},
            {"x": 3.0, "y": 4.0}
        ]
        
        input_file = self.create_test_json_lines_file(json_data)
        schema_file = self.create_test_schema_file()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            stream_convert_json_lines_to_array(
                input_file, output_path, 
                type_name="Point", schema_file=schema_file
            )
            
            assert output_path.exists()
            with open(output_path) as f:
                result_data = json.load(f)
                assert len(result_data) == 2
        finally:
            input_file.unlink()
            schema_file.unlink()
            if output_path.exists():
                output_path.unlink()
    

    
    def test_stream_convert_json_array_to_lines(self):
        """Test converting JSON array to lines format."""
        json_data = [
            {"x": 1.0, "y": 2.0},
            {"x": 3.0, "y": 4.0},
            {"x": 5.0, "y": 6.0}
        ]
        
        input_file = self.create_test_json_file(json_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            stream_convert_json_array_to_lines(input_file, output_path)
            
            assert output_path.exists()
            with open(output_path) as f:
                lines = f.readlines()
                assert len(lines) == 3
                assert json.loads(lines[0])["x"] == 1.0
                assert json.loads(lines[1])["x"] == 3.0
                assert json.loads(lines[2])["x"] == 5.0
        finally:
            input_file.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_stream_convert_json_array_to_lines_with_validation(self):
        """Test converting JSON array to lines with validation."""
        json_data = [
            {"x": 1.0, "y": 2.0},
            {"x": 3.0, "y": 4.0}
        ]
        
        input_file = self.create_test_json_file(json_data)
        schema_file = self.create_test_schema_file()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            stream_convert_json_array_to_lines(
                input_file, output_path,
                type_name="Point", schema_file=schema_file
            )
            
            assert output_path.exists()
            with open(output_path) as f:
                lines = f.readlines()
                assert len(lines) == 2
        finally:
            input_file.unlink()
            schema_file.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_streaming_json_parser_large_array(self):
        """Test streaming parser with large JSON array."""
        parser = StreamingJSONParser()
        
        large_data = [{"x": float(i), "y": float(i * 2)} for i in range(100)]
        json_str = json.dumps(large_data)
        
        stream = io.StringIO(json_str)
        objects = list(parser.parse_json_array_stream(stream, validate=False))
        
        assert len(objects) == 100
        assert objects[0]["x"] == 0.0
        assert objects[99]["x"] == 99.0
    
    def test_streaming_json_parser_large_json_lines(self):
        """Test streaming parser with large JSON Lines."""
        parser = StreamingJSONParser()
        
        lines = []
        for i in range(100):
            lines.append(json.dumps({"x": float(i), "y": float(i * 2)}))
        json_lines_str = '\n'.join(lines)
        
        stream = io.StringIO(json_lines_str)
        objects = list(parser.parse_json_lines_stream(stream, validate=False))
        
        assert len(objects) == 100
        assert objects[0]["x"] == 0.0
        assert objects[99]["x"] == 99.0
    
    def test_streaming_json_parser_array_format(self):
        """Test streaming parser with JSON array."""
        parser = StreamingJSONParser(self.converter)
        
        json_data = [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}]
        json_str = json.dumps(json_data)
        
        stream = io.StringIO(json_str)
        objects = list(parser.parse_json_array_stream(stream, validate=False))
        
        assert len(objects) == 2
        assert objects[0]["x"] == 1.0
        assert objects[1]["x"] == 3.0
    
    def test_streaming_json_parser_lines_format(self):
        """Test streaming parser with JSON Lines."""
        parser = StreamingJSONParser(self.converter)
        
        json_lines = '''{"x": 1.0, "y": 2.0}
{"x": 3.0, "y": 4.0}'''
        
        stream = io.StringIO(json_lines)
        objects = list(parser.parse_json_lines_stream(stream, validate=False))
        
        assert len(objects) == 2
        assert objects[0]["x"] == 1.0
        assert objects[1]["x"] == 3.0
    
    def test_streaming_json_parser_empty_lines_handling(self):
        """Test streaming parser handles empty lines correctly."""
        parser = StreamingJSONParser()
        
        json_lines = '''{"x": 1.0, "y": 2.0}

{"x": 3.0, "y": 4.0}


{"x": 5.0, "y": 6.0}
'''
        
        stream = io.StringIO(json_lines)
        objects = list(parser.parse_json_lines_stream(stream, validate=False))
        
        assert len(objects) == 3
        assert objects[0]["x"] == 1.0
        assert objects[1]["x"] == 3.0
        assert objects[2]["x"] == 5.0
    
    def test_streaming_json_parser_malformed_json_lines(self):
        """Test streaming parser with malformed JSON Lines."""
        parser = StreamingJSONParser()
        
        json_lines = '''{"x": 1.0, "y": 2.0}
{"x": 3.0, "y": 4.0
{"x": 5.0, "y": 6.0}'''
        
        stream = io.StringIO(json_lines)
        
        with pytest.raises(JSONStreamingError):
            list(parser.parse_json_lines_stream(stream, validate=False))
    
    def test_streaming_json_writer_array_format(self):
        """Test streaming JSON writer for array format."""
        output = io.StringIO()
        writer = StreamingJSONWriter(output, self.converter)
        
        writer.start_array()
        writer.write_object({"x": 1.0, "y": 2.0})
        writer.write_object({"x": 3.0, "y": 4.0})
        writer.end_array()
        
        result = output.getvalue()
        parsed = json.loads(result)
        
        assert len(parsed) == 2
        assert parsed[0]["x"] == 1.0
        assert parsed[1]["x"] == 3.0
    
    def test_streaming_json_writer_lines_format(self):
        """Test streaming JSON writer for lines format."""
        output = io.StringIO()
        writer = StreamingJSONWriter(output, self.converter)
        
        objects = [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}]
        writer.write_json_lines(iter(objects))
        
        result = output.getvalue()
        lines = result.strip().split('\n')
        
        assert len(lines) == 2
        assert json.loads(lines[0])["x"] == 1.0
        assert json.loads(lines[1])["x"] == 3.0
    
    def test_streaming_json_parser_with_validation(self):
        """Test streaming parser with validation enabled."""
        parser = StreamingJSONParser(self.converter)
        
        json_data = [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}]
        json_str = json.dumps(json_data)
        
        stream = io.StringIO(json_str)
        objects = list(parser.parse_json_array_stream(stream, type_name="Point", validate=True))
        
        assert len(objects) == 2
        assert objects[0]["x"] == 1.0
        assert objects[1]["x"] == 3.0
    
    def test_streaming_json_parser_validation_failure(self):
        """Test streaming parser with validation failure."""
        parser = StreamingJSONParser(self.converter)
        
        json_data = [{"x": 1.0, "y": 2.0}, {"x": "invalid", "y": 4.0}]
        json_str = json.dumps(json_data)
        
        stream = io.StringIO(json_str)
        
        with pytest.raises(JSONStreamingError):
            list(parser.parse_json_array_stream(stream, type_name="Point", validate=True)) 
