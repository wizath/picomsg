"""
Tests for JSON CLI integration.
"""

import pytest
import tempfile
import json
from pathlib import Path
from click.testing import CliRunner

from picomsg.cli import main


class TestJSONCLI:
    """Test JSON CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def create_test_schema(self, content: str) -> Path:
        """Create a temporary schema file with given content."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pico', delete=False)
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)
    
    def create_test_json(self, data) -> Path:
        """Create a temporary JSON file with given data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(data, temp_file)
        temp_file.close()
        return Path(temp_file.name)
    
    def create_test_json_lines(self, data_list: list) -> Path:
        """Create a temporary JSON Lines file with given data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        for item in data_list:
            json.dump(item, temp_file)
            temp_file.write('\n')
        temp_file.close()
        return Path(temp_file.name)
    
    def test_json_validate_command_valid_data(self):
        """Test json validate command with valid data."""
        schema_content = """
        namespace test.json;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        json_data = {"x": 1.5, "y": 2.5}
        
        schema_file = self.create_test_schema(schema_content)
        json_file = self.create_test_json(json_data)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'validate', str(schema_file), str(json_file), 'Point'
            ])
            assert result.exit_code == 0
            assert "JSON validation passed for type 'Point'" in result.output
        finally:
            schema_file.unlink()
            json_file.unlink()
    
    def test_json_validate_command_invalid_data(self):
        """Test json validate command with invalid data."""
        schema_content = """
        namespace test.json;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        json_data = {"x": "invalid", "y": 2.5}
        
        schema_file = self.create_test_schema(schema_content)
        json_file = self.create_test_json(json_data)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'validate', str(schema_file), str(json_file), 'Point'
            ])
            assert result.exit_code == 1
            assert "Field x must be a number" in result.output
        finally:
            schema_file.unlink()
            json_file.unlink()
    
    def test_json_validate_command_streaming(self):
        """Test json validate command with streaming option."""
        schema_content = """
        namespace test.json;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        json_data = [{"x": 1.5, "y": 2.5}, {"x": 3.0, "y": 4.0}]
        
        schema_file = self.create_test_schema(schema_content)
        json_file = self.create_test_json(json_data)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'validate', str(schema_file), str(json_file), 'Point', '--streaming'
            ])
            assert result.exit_code == 0
            assert "JSON array validation passed for type 'Point'" in result.output
        finally:
            schema_file.unlink()
            json_file.unlink()
    
    def test_json_pretty_command(self):
        """Test json pretty command."""
        schema_content = """
        namespace test.json;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        json_data = {"x": 1.5, "y": 2.5}
        
        schema_file = self.create_test_schema(schema_content)
        json_file = self.create_test_json(json_data)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'pretty', str(schema_file), str(json_file), 'Point'
            ])
            assert result.exit_code == 0
            assert '"x"' in result.output
            assert '"y"' in result.output
            assert '1.5' in result.output
            assert '2.5' in result.output
        finally:
            schema_file.unlink()
            json_file.unlink()
    
    def test_json_pretty_command_with_output_file(self):
        """Test json pretty command with output file."""
        schema_content = """
        namespace test.json;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        json_data = {"x": 1.5, "y": 2.5}
        
        schema_file = self.create_test_schema(schema_content)
        json_file = self.create_test_json(json_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'pretty', str(schema_file), str(json_file), 'Point',
                '--output', str(output_path), '--indent', '4'
            ])
            assert result.exit_code == 0
            
            assert output_path.exists()
            with open(output_path) as f:
                content = f.read()
                assert '"x"' in content
                assert '"y"' in content
                assert '1.5' in content
                assert '2.5' in content
        finally:
            schema_file.unlink()
            json_file.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_json_convert_command_array_to_lines(self):
        """Test json convert command from array to lines."""
        json_data = [{"name": "item1", "value": 1}, {"name": "item2", "value": 2}]
        
        input_file = self.create_test_json(json_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'convert', str(input_file), str(output_path),
                '--from-format', 'array', '--to-format', 'lines'
            ])
            assert result.exit_code == 0
            
            assert output_path.exists()
            with open(output_path) as f:
                lines = f.readlines()
                assert len(lines) == 2
                assert json.loads(lines[0])["name"] == "item1"
                assert json.loads(lines[1])["name"] == "item2"
        finally:
            input_file.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_json_convert_command_lines_to_array(self):
        """Test json convert command from lines to array."""
        json_data = [{"name": "item1", "value": 1}, {"name": "item2", "value": 2}]
        
        input_file = self.create_test_json_lines(json_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'convert', str(input_file), str(output_path),
                '--from-format', 'lines', '--to-format', 'array'
            ])
            assert result.exit_code == 0
            
            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)
                assert len(data) == 2
                assert data[0]["name"] == "item1"
                assert data[1]["name"] == "item2"
        finally:
            input_file.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_json_info_command_text_format(self):
        """Test json info command with text format."""
        schema_content = """
        namespace test.json;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'info', str(schema_file), '--format', 'text'
            ])
            assert result.exit_code == 0
            assert "Schema:" in result.output
            assert "Total types: 1" in result.output
            assert "Point" in result.output
        finally:
            schema_file.unlink()
    
    def test_json_info_command_json_format(self):
        """Test json info command with JSON format."""
        schema_content = """
        namespace test.json;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'info', str(schema_file), '--format', 'json'
            ])
            assert result.exit_code == 0
            
            json_output = json.loads(result.output)
            assert "structs" in json_output
            assert len(json_output["structs"]) == 1
            assert json_output["structs"][0]["name"] == "Point"
            assert json_output["total_types"] == 1
        finally:
            schema_file.unlink()
    
    def test_json_validate_nonexistent_schema(self):
        """Test json validate with non-existent schema file."""
        json_data = {"x": 1.5, "y": 2.5}
        json_file = self.create_test_json(json_data)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'validate', 'nonexistent.pico', str(json_file), 'Point'
            ])
            assert result.exit_code == 2
        finally:
            json_file.unlink()
    
    def test_json_validate_nonexistent_json(self):
        """Test json validate with non-existent JSON file."""
        schema_content = """
        namespace test.json;
        
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'validate', str(schema_file), 'nonexistent.json', 'Point'
            ])
            assert result.exit_code == 2
        finally:
            schema_file.unlink()
    
    def test_json_convert_with_validation_disabled(self):
        """Test json convert command with validation disabled."""
        json_data = [{"name": "item1", "value": 1}, {"name": "item2", "value": 2}]
        
        input_file = self.create_test_json(json_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'convert', str(input_file), str(output_path),
                '--from-format', 'array', '--to-format', 'lines',
                '--no-validate'
            ])
            assert result.exit_code == 0
            
            assert output_path.exists()
            with open(output_path) as f:
                lines = f.readlines()
                assert len(lines) == 2
        finally:
            input_file.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_json_convert_with_pretty_output(self):
        """Test json convert command with pretty output."""
        json_data = [{"name": "item1", "value": 1}, {"name": "item2", "value": 2}]
        
        input_file = self.create_test_json_lines(json_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            result = self.runner.invoke(main, [
                'json', 'convert', str(input_file), str(output_path),
                '--from-format', 'lines', '--to-format', 'array',
                '--pretty'
            ])
            assert result.exit_code == 0
            
            assert output_path.exists()
            with open(output_path) as f:
                content = f.read()
                assert '"name"' in content
                assert '"value"' in content
        finally:
            input_file.unlink()
            if output_path.exists():
                output_path.unlink() 
