"""
Tests for PicoMsg C code generator.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path

from picomsg.schema.ast import (
    Schema, Namespace, Struct, Message, Field,
    PrimitiveType, StringType, BytesType, ArrayType, StructType
)
from picomsg.codegen.c import CCodeGenerator


class TestCCodeGenerator:
    """Test CCodeGenerator class."""
    
    def test_generate_empty_schema(self):
        """Test generating code for empty schema."""
        schema = Schema(namespace=None, structs=[], messages=[])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        
        assert len(files) == 2
        assert 'picomsg_generated.h' in files
        assert 'picomsg_generated.c' in files
        
        header = files['picomsg_generated.h']
        assert '#ifndef PICOMSG_GENERATED_H' in header
        assert '#define PICOMSG_GENERATED_H' in header
        assert '#include <stdint.h>' in header
        assert '#include <stddef.h>' in header
        assert '#include <stdbool.h>' in header
    
    def test_generate_with_namespace(self):
        """Test generating code with namespace."""
        namespace = Namespace(name='test.namespace')
        schema = Schema(namespace=namespace, structs=[], messages=[])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        
        # Check namespace prefix in constants
        assert 'TEST_NAMESPACE_MAGIC_BYTE_1' in header
        assert 'TEST_NAMESPACE_VERSION' in header
        assert 'test_namespace_error_t' in header
    
    def test_generate_simple_struct(self):
        """Test generating code for simple struct."""
        struct = Struct(name='Point', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
            Field(name='y', type=PrimitiveType(name='f32')),
        ])
        schema = Schema(namespace=None, structs=[struct], messages=[])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        impl = files['picomsg_generated.c']
        
        # Check struct definition
        assert 'typedef struct __attribute__((packed))' in header
        assert 'float x;' in header
        assert 'float y;' in header
        assert '} point_t;' in header
        
        # Check function declarations
        assert 'point_from_bytes(' in header
        assert 'point_to_bytes(' in header
        
        # Check function implementations
        assert 'point_from_bytes(' in impl
        assert 'point_to_bytes(' in impl
        assert 'memcpy(out, data, sizeof(point_t));' in impl
        assert 'memcpy(buf, msg, sizeof(point_t));' in impl
    
    def test_generate_all_primitive_types(self):
        """Test generating code with all primitive types."""
        struct = Struct(name='AllTypes', fields=[
            Field(name='u8_field', type=PrimitiveType(name='u8')),
            Field(name='u16_field', type=PrimitiveType(name='u16')),
            Field(name='u32_field', type=PrimitiveType(name='u32')),
            Field(name='u64_field', type=PrimitiveType(name='u64')),
            Field(name='i8_field', type=PrimitiveType(name='i8')),
            Field(name='i16_field', type=PrimitiveType(name='i16')),
            Field(name='i32_field', type=PrimitiveType(name='i32')),
            Field(name='i64_field', type=PrimitiveType(name='i64')),
            Field(name='f32_field', type=PrimitiveType(name='f32')),
            Field(name='f64_field', type=PrimitiveType(name='f64')),
        ])
        schema = Schema(namespace=None, structs=[struct], messages=[])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        
        # Check C type mappings
        assert 'uint8_t u8_field;' in header
        assert 'uint16_t u16_field;' in header
        assert 'uint32_t u32_field;' in header
        assert 'uint64_t u64_field;' in header
        assert 'int8_t i8_field;' in header
        assert 'int16_t i16_field;' in header
        assert 'int32_t i32_field;' in header
        assert 'int64_t i64_field;' in header
        assert 'float f32_field;' in header
        assert 'double f64_field;' in header
    
    def test_generate_variable_size_types(self):
        """Test generating code with variable-size types."""
        struct = Struct(name='VariableTypes', fields=[
            Field(name='name', type=StringType()),
            Field(name='data', type=BytesType()),
            Field(name='numbers', type=ArrayType(element_type=PrimitiveType(name='u32'))),
        ])
        schema = Schema(namespace=None, structs=[struct], messages=[])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        
        # Variable-size types should be represented as length/count prefixes
        assert 'uint16_t name;' in header  # String length prefix
        assert 'uint16_t data;' in header  # Bytes length prefix
        assert 'uint16_t numbers;' in header  # Array count prefix
    
    def test_generate_struct_references(self):
        """Test generating code with struct type references."""
        point_struct = Struct(name='Point', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
            Field(name='y', type=PrimitiveType(name='f32')),
        ])
        
        line_struct = Struct(name='Line', fields=[
            Field(name='start', type=StructType(name='Point')),
            Field(name='end', type=StructType(name='Point')),
        ])
        
        schema = Schema(namespace=None, structs=[point_struct, line_struct], messages=[])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        
        # Check struct type references
        assert 'point_t start;' in header
        assert 'point_t end;' in header
    
    def test_generate_with_namespace_struct_references(self):
        """Test generating code with namespace and struct references."""
        namespace = Namespace(name='geometry')
        
        point_struct = Struct(name='Point', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
        ])
        
        line_struct = Struct(name='Line', fields=[
            Field(name='start', type=StructType(name='Point')),
        ])
        
        schema = Schema(namespace=namespace, structs=[point_struct, line_struct], messages=[])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        
        # Check namespace-prefixed struct references
        assert 'geometry_point_t start;' in header
    
    def test_generate_messages(self):
        """Test generating code for messages."""
        message = Message(name='TestMessage', fields=[
            Field(name='id', type=PrimitiveType(name='u32')),
            Field(name='data', type=BytesType()),
        ])
        schema = Schema(namespace=None, structs=[], messages=[message])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        impl = files['picomsg_generated.c']
        
        # Check message type ID
        assert 'TESTMESSAGE_TYPE_ID 1' in header
        
        # Check message struct definition
        assert 'typedef struct __attribute__((packed))' in header
        assert 'uint32_t id;' in header
        assert 'uint16_t data;' in header
        assert '} testmessage_t;' in header
        
        # Check function declarations and implementations
        assert 'testmessage_from_bytes(' in header
        assert 'testmessage_to_bytes(' in header
        assert 'testmessage_from_bytes(' in impl
        assert 'testmessage_to_bytes(' in impl
    
    def test_generate_multiple_messages(self):
        """Test generating code for multiple messages."""
        message1 = Message(name='Request', fields=[
            Field(name='id', type=PrimitiveType(name='u32')),
        ])
        message2 = Message(name='Response', fields=[
            Field(name='id', type=PrimitiveType(name='u32')),
        ])
        schema = Schema(namespace=None, structs=[], messages=[message1, message2])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        
        # Check message type IDs are sequential
        assert 'REQUEST_TYPE_ID 1' in header
        assert 'RESPONSE_TYPE_ID 2' in header
    
    def test_generate_error_codes(self):
        """Test generating error code enum."""
        schema = Schema(namespace=None, structs=[], messages=[])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        
        # Check error enum
        assert 'typedef enum {' in header
        assert 'OK = 0,' in header
        assert 'ERROR_INVALID_HEADER,' in header
        assert 'ERROR_BUFFER_TOO_SMALL,' in header
        assert 'ERROR_INVALID_DATA,' in header
        assert 'ERROR_NULL_POINTER' in header
        assert '} error_t;' in header
    
    def test_generate_custom_header_name(self):
        """Test generating code with custom header name."""
        schema = Schema(namespace=None, structs=[], messages=[])
        generator = CCodeGenerator(schema)
        generator.set_option('header_name', 'custom_header')
        
        files = generator.generate()
        
        assert 'custom_header.h' in files
        assert 'custom_header.c' in files
        
        header = files['custom_header.h']
        impl = files['custom_header.c']
        
        assert '#ifndef CUSTOM_HEADER_H' in header
        assert '#define CUSTOM_HEADER_H' in header
        assert '#include "custom_header.h"' in impl
    
    def test_sanitize_identifier(self):
        """Test identifier sanitization."""
        schema = Schema(namespace=None, structs=[], messages=[])
        generator = CCodeGenerator(schema)
        
        # Test various invalid identifiers
        assert generator._sanitize_identifier('valid_name') == 'valid_name'
        assert generator._sanitize_identifier('123invalid') == '_123invalid'
        assert generator._sanitize_identifier('invalid-name') == 'invalid_name'
        assert generator._sanitize_identifier('invalid.name') == 'invalid_name'
        assert generator._sanitize_identifier('invalid name') == 'invalid_name'
    
    def test_get_c_type_mapping(self):
        """Test C type mapping."""
        schema = Schema(namespace=None, structs=[], messages=[])
        generator = CCodeGenerator(schema)
        
        # Test primitive type mappings
        assert generator._get_c_type(PrimitiveType(name='u8')) == 'uint8_t'
        assert generator._get_c_type(PrimitiveType(name='i32')) == 'int32_t'
        assert generator._get_c_type(PrimitiveType(name='f64')) == 'double'
        
        # Test variable-size type mappings
        assert generator._get_c_type(StringType()) == 'uint16_t'
        assert generator._get_c_type(BytesType()) == 'uint16_t'
        assert generator._get_c_type(ArrayType(element_type=PrimitiveType(name='u8'))) == 'uint16_t'
        
        # Test struct type mapping
        assert generator._get_c_type(StructType(name='Point')) == 'point_t'
    
    def test_get_c_type_with_namespace(self):
        """Test C type mapping with namespace."""
        namespace = Namespace(name='test.ns')
        schema = Schema(namespace=namespace, structs=[], messages=[])
        generator = CCodeGenerator(schema)
        
        # Struct type should include namespace prefix
        assert generator._get_c_type(StructType(name='Point')) == 'test_ns_point_t'
    
    def test_write_files(self):
        """Test writing generated files to disk."""
        struct = Struct(name='Point', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
        ])
        schema = Schema(namespace=None, structs=[struct], messages=[])
        generator = CCodeGenerator(schema)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator.write_files(output_dir)
            
            # Check files were created
            header_file = output_dir / 'picomsg_generated.h'
            impl_file = output_dir / 'picomsg_generated.c'
            
            assert header_file.exists()
            assert impl_file.exists()
            
            # Check file contents
            header_content = header_file.read_text()
            impl_content = impl_file.read_text()
            
            assert 'typedef struct' in header_content
            assert 'float x;' in header_content
            assert '#include "picomsg_generated.h"' in impl_content
    
    def test_generated_code_compiles(self):
        """Test that generated C code compiles successfully."""
        # Create a more complex schema
        header_struct = Struct(name='Header', fields=[
            Field(name='magic', type=PrimitiveType(name='u16')),
            Field(name='version', type=PrimitiveType(name='u8')),
        ])
        
        point_struct = Struct(name='Point', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
            Field(name='y', type=PrimitiveType(name='f32')),
        ])
        
        message = Message(name='TestMessage', fields=[
            Field(name='header', type=StructType(name='Header')),
            Field(name='point', type=StructType(name='Point')),
            Field(name='id', type=PrimitiveType(name='u32')),
        ])
        
        namespace = Namespace(name='test.compile')
        schema = Schema(namespace=namespace, structs=[header_struct, point_struct], messages=[message])
        generator = CCodeGenerator(schema)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator.write_files(output_dir)
            
            # Try to compile the generated code
            header_file = output_dir / 'picomsg_generated.h'
            impl_file = output_dir / 'picomsg_generated.c'
            obj_file = output_dir / 'picomsg_generated.o'
            
            try:
                # Compile with gcc
                result = subprocess.run([
                    'gcc', '-c', str(impl_file), '-o', str(obj_file),
                    '-Wall', '-Wextra', '-Werror'
                ], capture_output=True, text=True, timeout=10)
                
                # Check compilation succeeded
                assert result.returncode == 0, f"Compilation failed: {result.stderr}"
                assert obj_file.exists()
                
            except FileNotFoundError:
                # gcc not available, skip this test
                pytest.skip("gcc not available for compilation test")
            except subprocess.TimeoutExpired:
                pytest.fail("Compilation timed out")
    
    def test_function_generation_completeness(self):
        """Test that all necessary functions are generated."""
        struct = Struct(name='TestStruct', fields=[
            Field(name='value', type=PrimitiveType(name='u32')),
        ])
        
        message = Message(name='TestMessage', fields=[
            Field(name='id', type=PrimitiveType(name='u32')),
        ])
        
        schema = Schema(namespace=None, structs=[struct], messages=[message])
        generator = CCodeGenerator(schema)
        
        files = generator.generate()
        header = files['picomsg_generated.h']
        impl = files['picomsg_generated.c']
        
        # Check all expected functions are declared and implemented
        expected_functions = [
            'teststruct_from_bytes',
            'teststruct_to_bytes',
            'testmessage_from_bytes',
            'testmessage_to_bytes',
        ]
        
        for func_name in expected_functions:
            assert func_name in header, f"Function {func_name} not declared in header"
            assert func_name in impl, f"Function {func_name} not implemented"
    
    def test_header_guards(self):
        """Test that header guards are properly generated."""
        schema = Schema(namespace=None, structs=[], messages=[])
        generator = CCodeGenerator(schema)
        generator.set_option('header_name', 'test_header')
        
        files = generator.generate()
        header = files['test_header.h']
        
        # Check header guards
        lines = header.split('\n')
        assert lines[0] == '#ifndef TEST_HEADER_H'
        assert lines[1] == '#define TEST_HEADER_H'
        assert lines[-1] == '#endif // TEST_HEADER_H'
    
    def test_cpp_compatibility(self):
        """Test that generated code is C++ compatible."""
        namespace = Namespace("test")
        
        struct = Struct(name="Point", fields=[
            Field(name="x", type=PrimitiveType(name="f32")),
            Field(name="y", type=PrimitiveType(name="f32"))
        ])
        
        schema = Schema(namespace=namespace, structs=[struct], messages=[])
        
        generator = CCodeGenerator(schema)
        files = generator.generate()
        
        header_content = files["picomsg_generated.h"]
        assert 'extern "C" {' in header_content
        assert '}' in header_content.split('extern "C" {')[1]

    def test_structs_only_option(self):
        """Test structs_only option generates only structures."""
        namespace = Namespace("test")
        
        # Add a struct
        struct = Struct(name="Point", fields=[
            Field(name="x", type=PrimitiveType(name="f32")),
            Field(name="y", type=PrimitiveType(name="f32"))
        ])
        
        # Add a message
        message = Message(name="EchoRequest", fields=[
            Field(name="point", type=StructType(name="Point")),
            Field(name="id", type=PrimitiveType(name="u32"))
        ])
        
        schema = Schema(namespace=namespace, structs=[struct], messages=[message])
        
        generator = CCodeGenerator(schema)
        generator.set_option('structs_only', True)
        files = generator.generate()
        
        # Should only generate header file
        assert len(files) == 1
        assert "picomsg_generated.h" in files
        assert "picomsg_generated.c" not in files
        
        header_content = files["picomsg_generated.h"]
        
        # Should contain struct definitions
        assert "typedef struct" in header_content
        assert "test_point_t" in header_content
        assert "test_echorequest_t" in header_content
        
        # Should NOT contain error enums
        assert "typedef enum" not in header_content
        assert "TEST_OK" not in header_content
        assert "TEST_ERROR_" not in header_content
        
        # Should NOT contain function declarations
        assert "_from_bytes" not in header_content
        assert "_to_bytes" not in header_content
        
        # Should NOT contain format constants
        assert "MAGIC_BYTE" not in header_content
        assert "VERSION" not in header_content
        assert "TYPE_ID" not in header_content

    def test_structs_only_vs_regular_mode(self):
        """Test difference between structs_only and regular mode."""
        namespace = Namespace("test")
        
        struct = Struct(name="Point", fields=[
            Field(name="x", type=PrimitiveType(name="f32")),
            Field(name="y", type=PrimitiveType(name="f32"))
        ])
        
        schema = Schema(namespace=namespace, structs=[struct], messages=[])
        
        # Generate regular mode
        generator_regular = CCodeGenerator(schema)
        files_regular = generator_regular.generate()
        
        # Generate structs_only mode
        generator_structs = CCodeGenerator(schema)
        generator_structs.set_option('structs_only', True)
        files_structs = generator_structs.generate()
        
        # Regular mode should have both files
        assert len(files_regular) == 2
        assert "picomsg_generated.h" in files_regular
        assert "picomsg_generated.c" in files_regular
        
        # Structs only should have just header
        assert len(files_structs) == 1
        assert "picomsg_generated.h" in files_structs
        
        # Regular header should be longer (contains more content)
        regular_header = files_regular["picomsg_generated.h"]
        structs_header = files_structs["picomsg_generated.h"]
        
        assert len(regular_header) > len(structs_header)
        
        # Both should contain the struct definition
        assert "test_point_t" in regular_header
        assert "test_point_t" in structs_header
        
        # Only regular should contain error enum and functions
        assert "typedef enum" in regular_header
        assert "typedef enum" not in structs_header
        assert "_from_bytes" in regular_header
        assert "_from_bytes" not in structs_header

    def test_schema_version_in_generated_code(self):
        """Test that schema version is properly used in generated code."""
        namespace = Namespace("test")
        struct = Struct(name="Point", fields=[
            Field(name="x", type=PrimitiveType(name="f32"))
        ])
        
        # Test with explicit version
        schema_with_version = Schema(namespace=namespace, structs=[struct], messages=[], version=42)
        generator = CCodeGenerator(schema_with_version)
        files = generator.generate()
        
        header_content = files["picomsg_generated.h"]
        assert "#define TEST_VERSION 42" in header_content
        
        # Test without version (should default to 1)
        schema_no_version = Schema(namespace=namespace, structs=[struct], messages=[])
        generator = CCodeGenerator(schema_no_version)
        files = generator.generate()
        
        header_content = files["picomsg_generated.h"]
        assert "#define TEST_VERSION 1" in header_content

    def test_schema_version_edge_cases(self):
        """Test schema version edge cases in code generation."""
        namespace = Namespace("test")
        struct = Struct(name="Point", fields=[
            Field(name="x", type=PrimitiveType(name="f32"))
        ])
        
        # Test minimum version (1)
        schema = Schema(namespace=namespace, structs=[struct], messages=[], version=1)
        generator = CCodeGenerator(schema)
        files = generator.generate()
        header_content = files["picomsg_generated.h"]
        assert "#define TEST_VERSION 1" in header_content
        
        # Test maximum version (255)
        schema = Schema(namespace=namespace, structs=[struct], messages=[], version=255)
        generator = CCodeGenerator(schema)
        files = generator.generate()
        header_content = files["picomsg_generated.h"]
        assert "#define TEST_VERSION 255" in header_content

    def test_schema_version_with_structs_only_mode(self):
        """Test that version is not included in structs-only mode."""
        namespace = Namespace("test")
        struct = Struct(name="Point", fields=[
            Field(name="x", type=PrimitiveType(name="f32"))
        ])
        
        schema = Schema(namespace=namespace, structs=[struct], messages=[], version=10)
        generator = CCodeGenerator(schema)
        generator.set_option('structs_only', True)
        files = generator.generate()
        
        header_content = files["picomsg_generated.h"]
        
        # Should NOT contain version define in structs-only mode
        assert "TEST_VERSION" not in header_content
        assert "#define" not in header_content or "#ifndef" in header_content  # Only header guards 
