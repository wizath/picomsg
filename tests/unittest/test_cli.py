"""
Tests for PicoMsg CLI.
"""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner

from picomsg.cli import main


class TestCLI:
    """Test CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def create_test_schema(self, content: str) -> Path:
        """Create a temporary schema file with given content."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pico', delete=False)
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_main_help(self):
        """Test main command help."""
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'PicoMsg - Lightweight binary serialization format' in result.output
        assert 'compile' in result.output
        assert 'validate' in result.output
        assert 'info' in result.output
    
    def test_validate_command_valid_schema(self):
        """Test validate command with valid schema."""
        schema_content = """
        namespace test.valid;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message TestMessage {
            point: Point;
            id: u32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, ['validate', str(schema_file)])
            assert result.exit_code == 0
            assert '✓ Schema file is valid' in result.output
            assert 'Namespace: test.valid' in result.output
            assert 'Structs: 1' in result.output
            assert 'Messages: 1' in result.output
            assert 'Point (2 fields)' in result.output
            assert 'TestMessage (2 fields)' in result.output
        finally:
            schema_file.unlink()
    
    def test_validate_command_invalid_schema(self):
        """Test validate command with invalid schema."""
        schema_content = """
        struct InvalidStruct {
            field: UndefinedType;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, ['validate', str(schema_file)])
            assert result.exit_code == 1
            assert 'Validation failed' in result.output
            assert 'Undefined type' in result.output
        finally:
            schema_file.unlink()
    
    def test_validate_command_nonexistent_file(self):
        """Test validate command with non-existent file."""
        result = self.runner.invoke(main, ['validate', 'nonexistent.pico'])
        assert result.exit_code == 2  # Click file not found error
    
    def test_info_command_detailed_output(self):
        """Test info command with detailed schema information."""
        schema_content = """
        namespace detailed.info;
        
        struct Header {
            magic: u16;
            version: u8;
            flags: u8;
        }
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message Request {
            header: Header;
            points: [Point];
            name: string;
        }
        
        message Response {
            header: Header;
            status: u8;
            data: bytes;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, ['info', str(schema_file)])
            assert result.exit_code == 0
            
            # Check header
            assert 'Schema:' in result.output
            assert '=' * 50 in result.output
            assert 'Namespace: detailed.info' in result.output
            
            # Check structs section
            assert 'Structs:' in result.output
            assert 'Header:' in result.output
            assert 'magic: u16' in result.output
            assert 'version: u8' in result.output
            assert 'flags: u8' in result.output
            
            assert 'Point:' in result.output
            assert 'x: f32' in result.output
            assert 'y: f32' in result.output
            
            # Check messages section
            assert 'Messages:' in result.output
            assert 'Request:' in result.output
            assert 'header: Header' in result.output
            assert 'points: [Point]' in result.output
            assert 'name: string' in result.output
            
            assert 'Response:' in result.output
            assert 'status: u8' in result.output
            assert 'data: bytes' in result.output
        finally:
            schema_file.unlink()
    
    def test_info_command_empty_schema(self):
        """Test info command with empty schema."""
        schema_content = ""
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, ['info', str(schema_file)])
            assert result.exit_code == 0
            assert 'Schema:' in result.output
            # Should not have Structs or Messages sections for empty schema
            assert 'Structs:' not in result.output
            assert 'Messages:' not in result.output
        finally:
            schema_file.unlink()
    
    def test_compile_command_c_language(self):
        """Test compile command for C language."""
        schema_content = """
        namespace test.compile;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message TestMessage {
            point: Point;
            id: u32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            try:
                result = self.runner.invoke(main, [
                    'compile', str(schema_file),
                    '--lang', 'c',
                    '--output', str(output_dir)
                ])
                
                assert result.exit_code == 0
                assert 'Parsed schema:' in result.output
                assert 'Namespace: test.compile' in result.output
                assert 'Structs: 1' in result.output
                assert 'Messages: 1' in result.output
                assert 'Generated 2 files' in result.output
                assert 'picomsg_generated.h' in result.output
                assert 'picomsg_generated.c' in result.output
                
                # Check files were actually created
                header_file = output_dir / 'picomsg_generated.h'
                impl_file = output_dir / 'picomsg_generated.c'
                assert header_file.exists()
                assert impl_file.exists()
                
                # Check file contents
                header_content = header_file.read_text()
                assert 'typedef struct' in header_content
                assert 'test_compile_point_t' in header_content
                
            finally:
                schema_file.unlink()
    
    def test_compile_command_custom_header_name(self):
        """Test compile command with custom header name."""
        schema_content = """
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            try:
                result = self.runner.invoke(main, [
                    'compile', str(schema_file),
                    '--lang', 'c',
                    '--output', str(output_dir),
                    '--header-name', 'custom_header'
                ])
                
                assert result.exit_code == 0
                assert 'custom_header.h' in result.output
                assert 'custom_header.c' in result.output
                
                # Check files were created with custom names
                header_file = output_dir / 'custom_header.h'
                impl_file = output_dir / 'custom_header.c'
                assert header_file.exists()
                assert impl_file.exists()
                
            finally:
                schema_file.unlink()
    
    def test_compile_command_unsupported_language(self):
        """Test compile command with unsupported language."""
        schema_content = """
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, [
                'compile', str(schema_file),
                '--lang', 'javascript'  # Not yet implemented
            ])
            
            assert result.exit_code == 1
            assert "Language 'javascript' not yet implemented" in result.output
            
        finally:
            schema_file.unlink()

    def test_compile_command_python_language(self):
        """Test compile command with Python language."""
        schema_content = """
        namespace test.python;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message EchoRequest {
            point: Point;
            id: u32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                result = self.runner.invoke(main, [
                    'compile', str(schema_file),
                    '--lang', 'python',
                    '--output', str(temp_path / 'generated'),
                    '--module-name', 'test_module'
                ])
                
                assert result.exit_code == 0
                assert "Generating Python code with module name: test_module" in result.output
                assert "Generated 1 files" in result.output
                
                # Check output directory was created
                output_dir = temp_path / 'generated'
                assert output_dir.exists()
                assert (output_dir / 'test_module.py').exists()
                
                # Check basic Python content
                python_content = (output_dir / 'test_module.py').read_text()
                assert "import struct" in python_content
                assert "import json" in python_content
                assert "class TestPythonPoint(TestPythonBase):" in python_content
                assert "class TestPythonEchoRequest(TestPythonBase):" in python_content
                assert "class TestPythonError(Exception):" in python_content
                
            finally:
                schema_file.unlink()

    def test_compile_command_rust_language(self):
        """Test compile command with Rust language."""
        schema_content = """
        namespace test.rust;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message EchoRequest {
            point: Point;
            id: u32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                result = self.runner.invoke(main, [
                    'compile', str(schema_file),
                    '--lang', 'rust',
                    '--output', str(temp_path / 'generated'),
                    '--module-name', 'test_module'
                ])
                
                assert result.exit_code == 0
                assert "Generating Rust code with module name: test_module" in result.output
                assert "Generated 1 files" in result.output
                
                # Check output directory was created
                output_dir = temp_path / 'generated'
                assert output_dir.exists()
                assert (output_dir / 'test_module.rs').exists()
                
                # Check basic Rust content
                rust_content = (output_dir / 'test_module.rs').read_text()
                assert "use serde::{Deserialize, Serialize};" in rust_content
                assert "pub struct TestRustPoint {" in rust_content
                assert "pub struct TestRustEchoRequest {" in rust_content
                assert "pub enum TestRustError {" in rust_content
                
            finally:
                schema_file.unlink()
    
    def test_compile_command_default_options(self):
        """Test compile command with default options."""
        schema_content = """
        struct Point {
            x: f32;
            y: f32;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                result = self.runner.invoke(main, [
                    'compile', str(schema_file),
                    '--output', str(temp_path / 'generated')
                ])
                
                assert result.exit_code == 0
                
                # Check output directory was created
                output_dir = temp_path / 'generated'
                assert output_dir.exists()
                assert (output_dir / 'picomsg_generated.h').exists()
                assert (output_dir / 'picomsg_generated.c').exists()
                
            finally:
                schema_file.unlink()
    
    def test_compile_command_invalid_schema(self):
        """Test compile command with invalid schema."""
        schema_content = """
        struct InvalidStruct {
            field: UndefinedType;
        }
        """
        
        schema_file = self.create_test_schema(schema_content)
        
        try:
            result = self.runner.invoke(main, [
                'compile', str(schema_file),
                '--lang', 'c'
            ])
            
            assert result.exit_code == 1
            assert 'Error:' in result.output
            assert 'Undefined type' in result.output
            
        finally:
            schema_file.unlink()
    
    def test_version_option(self):
        """Test --version option."""
        result = self.runner.invoke(main, ['--version'])
        assert result.exit_code == 0
        assert '0.6.0' in result.output
    
    def test_format_type_function(self):
        """Test the _format_type helper function."""
        from picomsg.cli import _format_type
        from picomsg.schema.ast import (
            PrimitiveType, StringType, BytesType, ArrayType, StructType
        )
        
        # Test primitive types
        assert _format_type(PrimitiveType(name='u32')) == 'u32'
        assert _format_type(PrimitiveType(name='f64')) == 'f64'
        
        # Test special types
        assert _format_type(StringType()) == 'string'
        assert _format_type(BytesType()) == 'bytes'
        assert _format_type(StructType(name='Point')) == 'Point'
        
        # Test array types
        array_type = ArrayType(element_type=PrimitiveType(name='u32'))
        assert _format_type(array_type) == '[u32]'
        
        # Test nested array
        nested_array = ArrayType(element_type=ArrayType(element_type=PrimitiveType(name='u8')))
        assert _format_type(nested_array) == '[[u8]]'
    
    def test_command_help_messages(self):
        """Test help messages for individual commands."""
        # Test compile command help
        result = self.runner.invoke(main, ['compile', '--help'])
        assert result.exit_code == 0
        assert 'Compile a PicoMsg schema file' in result.output
        assert '--lang' in result.output
        assert '--output' in result.output
        assert '--header-name' in result.output
        
        # Test validate command help
        result = self.runner.invoke(main, ['validate', '--help'])
        assert result.exit_code == 0
        assert 'Validate a PicoMsg schema file' in result.output
        
        # Test info command help
        result = self.runner.invoke(main, ['info', '--help'])
        assert result.exit_code == 0
        assert 'Show detailed information' in result.output
    
    def test_language_choice_validation(self):
        """Test that language choice is properly validated."""
        schema_content = "struct Point { x: f32; }"
        schema_file = self.create_test_schema(schema_content)
        
        try:
            # Test invalid language choice
            result = self.runner.invoke(main, [
                'compile', str(schema_file),
                '--lang', 'invalid_language'
            ])
            
            assert result.exit_code == 2  # Click validation error
            assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()
            
        finally:
            schema_file.unlink()
    
    def test_output_directory_creation(self):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_file = Path(temp_dir) / "test.pico"
            schema_file.write_text("namespace test;\nstruct Point { x: f32; y: f32; }")
            
            output_dir = Path(temp_dir) / "nonexistent" / "output"
            
            result = self.runner.invoke(main, [
                'compile', str(schema_file),
                '--output', str(output_dir)
            ])
            
            assert result.exit_code == 0
            assert output_dir.exists()
            assert (output_dir / "picomsg_generated.h").exists()

    def test_compile_structs_only_option(self):
        """Test compile command with --structs-only option."""
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_file = Path(temp_dir) / "test.pico"
            schema_file.write_text("""
                namespace test;
                
                struct Point {
                    x: f32;
                    y: f32;
                }
                
                message EchoRequest {
                    point: Point;
                    id: u32;
                }
            """)
            
            output_dir = Path(temp_dir) / "output"
            
            result = self.runner.invoke(main, [
                'compile', str(schema_file),
                '--output', str(output_dir),
                '--structs-only'
            ])
            
            assert result.exit_code == 0
            assert "Mode: Structs only" in result.output
            assert "Generated 1 files" in result.output
            
            # Check that only header file was generated
            assert (output_dir / "picomsg_generated.h").exists()
            assert not (output_dir / "picomsg_generated.c").exists()
            
            # Check header content
            header_content = (output_dir / "picomsg_generated.h").read_text()
            
            # Should contain struct definitions
            assert "test_point_t" in header_content
            assert "test_echorequest_t" in header_content
            
            # Should NOT contain error enums or function declarations
            assert "typedef enum" not in header_content
            assert "_from_bytes" not in header_content
            assert "_to_bytes" not in header_content
            assert "MAGIC_BYTE" not in header_content

    def test_compile_structs_only_with_custom_header_name(self):
        """Test compile command with --structs-only and custom header name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_file = Path(temp_dir) / "test.pico"
            schema_file.write_text("namespace test;\nstruct Point { x: f32; y: f32; }")
            
            output_dir = Path(temp_dir) / "output"
            
            result = self.runner.invoke(main, [
                'compile', str(schema_file),
                '--output', str(output_dir),
                '--header-name', 'custom_structs',
                '--structs-only'
            ])
            
            assert result.exit_code == 0
            assert "Mode: Structs only" in result.output
            
            # Check that only custom header file was generated
            assert (output_dir / "custom_structs.h").exists()
            assert not (output_dir / "custom_structs.c").exists()
            assert not (output_dir / "picomsg_generated.h").exists()

    def test_info_command_with_version(self):
        """Test info command shows version information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_file = Path(temp_dir) / "test.pico"
            schema_file.write_text("""
                version 5;
                namespace test.versioned;
                
                struct Point {
                    x: f32;
                    y: f32;
                }
                
                message TestMessage {
                    point: Point;
                    id: u32;
                }
            """)
            
            result = self.runner.invoke(main, ['info', str(schema_file)])
            
            assert result.exit_code == 0
            assert "Schema:" in result.output
            assert "Namespace: test.versioned" in result.output
            # Note: We might want to add version display to the info command later

    def test_validate_command_with_version(self):
        """Test validate command with version declaration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_file = Path(temp_dir) / "test.pico"
            schema_file.write_text("""
                version 3;
                namespace test.validation;
                
                struct Point {
                    x: f32;
                    y: f32;
                }
            """)
            
            result = self.runner.invoke(main, ['validate', str(schema_file)])
            
            assert result.exit_code == 0
            assert "✓ Schema file is valid" in result.output
            assert "Namespace: test.validation" in result.output

    def test_validate_command_invalid_version(self):
        """Test validate command with invalid version."""
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_file = Path(temp_dir) / "test.pico"
            schema_file.write_text("version 0;\nnamespace test;")
            
            result = self.runner.invoke(main, ['validate', str(schema_file)])
            
            assert result.exit_code == 1
            assert "Validation failed" in result.output
            assert "Schema version must be between 1 and 255" in result.output 
