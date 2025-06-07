"""
Integration tests for PicoMsg library.
Tests the complete workflow from schema parsing to code generation.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.c import CCodeGenerator


class TestIntegration:
    """Integration tests for complete PicoMsg workflow."""
    
    def test_complete_workflow_simple_schema(self):
        """Test complete workflow with simple schema."""
        schema_text = """
        namespace test.simple;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message EchoRequest {
            point: Point;
            id: u32;
        }
        """
        
        # Parse schema
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        # Verify parsed schema
        assert schema.namespace.name == "test.simple"
        assert len(schema.structs) == 1
        assert len(schema.messages) == 1
        
        point_struct = schema.get_struct("Point")
        assert point_struct is not None
        assert len(point_struct.fields) == 2
        
        echo_message = schema.get_message("EchoRequest")
        assert echo_message is not None
        assert len(echo_message.fields) == 2
        
        # Generate C code
        generator = CCodeGenerator(schema)
        files = generator.generate()
        
        # Verify generated files
        assert len(files) == 2
        assert 'picomsg_generated.h' in files
        assert 'picomsg_generated.c' in files
        
        header = files['picomsg_generated.h']
        impl = files['picomsg_generated.c']
        
        # Verify header content
        assert 'test_simple_point_t' in header
        assert 'test_simple_echorequest_t' in header
        assert 'ECHOREQUEST_TYPE_ID 1' in header
        
        # Verify implementation content
        assert 'test_simple_point_from_bytes' in impl
        assert 'test_simple_echorequest_from_bytes' in impl
    
    def test_complete_workflow_complex_schema(self):
        """Test complete workflow with complex schema."""
        schema_text = """
        namespace api.v1;
        
        struct ApiHeader {
            command: u8;
            length: u16;
            crc16: u16;
        }
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message EchoRequest {
            header: ApiHeader;
            point: Point;
            data: bytes;
        }
        
        message StatusResponse {
            header: ApiHeader;
            uptime: u32;
            status: u8;
        }
        """
        
        # Parse schema
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        # Verify parsed schema structure
        assert schema.namespace.name == "api.v1"
        assert len(schema.structs) == 2
        assert len(schema.messages) == 2
        
        # Generate C code
        generator = CCodeGenerator(schema)
        files = generator.generate()
        
        # Verify generated code structure
        header = files['picomsg_generated.h']
        impl = files['picomsg_generated.c']
        
        # Check namespace prefixes
        assert 'api_v1_apiheader_t' in header
        assert 'api_v1_point_t' in header
        assert 'api_v1_echorequest_t' in header
        assert 'api_v1_statusresponse_t' in header
        
        # Check message type IDs
        assert 'ECHOREQUEST_TYPE_ID 1' in header
        assert 'STATUSRESPONSE_TYPE_ID 2' in header
        
        # Check function declarations
        assert 'api_v1_echorequest_from_bytes' in header
        assert 'api_v1_statusresponse_from_bytes' in header
    
    def test_file_based_workflow(self):
        """Test complete workflow using file I/O."""
        schema_text = """
        namespace file.test;
        
        struct Header {
            magic: u16;
            version: u8;
        }
        
        message TestMessage {
            header: Header;
            payload: bytes;
        }
        """
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write schema to file
            schema_file = temp_path / 'test.pico'
            schema_file.write_text(schema_text)
            
            # Parse from file
            parser = SchemaParser()
            schema = parser.parse_file(schema_file)
            
            # Generate code
            generator = CCodeGenerator(schema)
            output_dir = temp_path / 'generated'
            generator.write_files(output_dir)
            
            # Verify files were created
            header_file = output_dir / 'picomsg_generated.h'
            impl_file = output_dir / 'picomsg_generated.c'
            
            assert header_file.exists()
            assert impl_file.exists()
            
            # Verify file contents
            header_content = header_file.read_text()
            impl_content = impl_file.read_text()
            
            assert 'file_test_header_t' in header_content
            assert 'file_test_testmessage_t' in header_content
            assert '#include "picomsg_generated.h"' in impl_content
    
    def test_generated_code_compilation(self):
        """Test that generated code compiles successfully."""
        schema_text = """
        namespace compile.test;
        
        struct Vector3 {
            x: f32;
            y: f32;
            z: f32;
        }
        
        struct Transform {
            position: Vector3;
            rotation: Vector3;
            scale: Vector3;
        }
        
        message UpdateTransform {
            entity_id: u32;
            transform: Transform;
            timestamp: u64;
        }
        
        message GetTransform {
            entity_id: u32;
        }
        """
        
        # Parse and generate
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        generator = CCodeGenerator(schema)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator.write_files(output_dir)
            
            header_file = output_dir / 'picomsg_generated.h'
            impl_file = output_dir / 'picomsg_generated.c'
            obj_file = output_dir / 'picomsg_generated.o'
            
            try:
                # Try to compile with gcc
                result = subprocess.run([
                    'gcc', '-c', str(impl_file), '-o', str(obj_file),
                    '-Wall', '-Wextra', '-Werror', '-std=c99'
                ], capture_output=True, text=True, timeout=10)
                
                assert result.returncode == 0, f"Compilation failed: {result.stderr}"
                assert obj_file.exists()
                
                # Verify no warnings
                assert result.stderr == "", f"Compilation warnings: {result.stderr}"
                
            except FileNotFoundError:
                pytest.skip("gcc not available for compilation test")
            except subprocess.TimeoutExpired:
                pytest.fail("Compilation timed out")
    
    def test_generated_code_functionality(self):
        """Test that generated code functions correctly."""
        schema_text = """
        namespace func.test;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message TestMessage {
            id: u32;
            point: Point;
        }
        """
        
        # Parse and generate
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        generator = CCodeGenerator(schema)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator.write_files(output_dir)
            
            # Create a test program
            test_program = """
#include "picomsg_generated.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

int main() {
    // Test struct serialization
    func_test_point_t point = {1.5f, 2.5f};
    uint8_t buffer[256];
    size_t size = sizeof(buffer);
    
    func_test_error_t result = func_test_point_to_bytes(&point, buffer, &size);
    assert(result == FUNC_TEST_OK);
    assert(size == sizeof(func_test_point_t));
    
    // Test struct deserialization
    func_test_point_t point2;
    result = func_test_point_from_bytes(buffer, size, &point2);
    assert(result == FUNC_TEST_OK);
    assert(point2.x == 1.5f);
    assert(point2.y == 2.5f);
    
    // Test message serialization
    func_test_testmessage_t message = {42, {3.0f, 4.0f}};
    size = sizeof(buffer);
    
    result = func_test_testmessage_to_bytes(&message, buffer, &size);
    assert(result == FUNC_TEST_OK);
    assert(size == sizeof(func_test_testmessage_t));
    
    // Test message deserialization
    func_test_testmessage_t message2;
    result = func_test_testmessage_from_bytes(buffer, size, &message2);
    assert(result == FUNC_TEST_OK);
    assert(message2.id == 42);
    assert(message2.point.x == 3.0f);
    assert(message2.point.y == 4.0f);
    
    printf("All tests passed!\\n");
    return 0;
}
"""
            
            test_file = output_dir / 'test_program.c'
            test_file.write_text(test_program)
            
            executable = output_dir / 'test_program'
            
            try:
                # Compile test program
                compile_result = subprocess.run([
                    'gcc', str(test_file), str(output_dir / 'picomsg_generated.c'),
                    '-o', str(executable),
                    '-Wall', '-Wextra', '-Werror', '-std=c99'
                ], capture_output=True, text=True, timeout=10)
                
                assert compile_result.returncode == 0, f"Test compilation failed: {compile_result.stderr}"
                
                # Run test program
                run_result = subprocess.run([str(executable)], 
                                          capture_output=True, text=True, timeout=5)
                
                assert run_result.returncode == 0, f"Test execution failed: {run_result.stderr}"
                assert "All tests passed!" in run_result.stdout
                
            except FileNotFoundError:
                pytest.skip("gcc not available for functionality test")
            except subprocess.TimeoutExpired:
                pytest.fail("Test execution timed out")
    
    def test_error_handling_workflow(self):
        """Test error handling throughout the workflow."""
        # Test parser error handling
        invalid_schema = """
        struct InvalidStruct {
            field: UndefinedType;
        }
        """
        
        parser = SchemaParser()
        with pytest.raises(ValueError, match="Undefined type"):
            parser.parse_string(invalid_schema)
        
        # Test syntax error handling
        syntax_error_schema = """
        struct SyntaxError {
            field_without_type;
        }
        """
        
        with pytest.raises(ValueError, match="Parse error"):
            parser.parse_string(syntax_error_schema)
        
        # Test duplicate name error handling
        duplicate_schema = """
        struct Point {
            x: f32;
        }
        
        struct Point {
            y: f32;
        }
        """
        
        with pytest.raises(ValueError, match="Duplicate struct names"):
            parser.parse_string(duplicate_schema)
    
    def test_namespace_handling_workflow(self):
        """Test namespace handling throughout the workflow."""
        schema_text = """
        namespace deeply.nested.namespace.test;
        
        struct NamespaceTest {
            value: u32;
        }
        
        message NamespaceMessage {
            test: NamespaceTest;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        # Verify namespace parsing
        assert schema.namespace.name == "deeply.nested.namespace.test"
        
        # Generate code and verify namespace prefixes
        generator = CCodeGenerator(schema)
        files = generator.generate()
        
        header = files['picomsg_generated.h']
        
        # Check that namespace is properly converted to C identifiers
        assert 'deeply_nested_namespace_test_namespacetest_t' in header
        assert 'deeply_nested_namespace_test_namespacemessage_t' in header
        assert 'DEEPLY_NESTED_NAMESPACE_TEST_MAGIC_BYTE_1' in header
    
    def test_empty_schema_workflow(self):
        """Test workflow with empty schema."""
        schema_text = ""
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        assert schema.namespace is None
        assert len(schema.structs) == 0
        assert len(schema.messages) == 0
        
        # Generate code for empty schema
        generator = CCodeGenerator(schema)
        files = generator.generate()
        
        # Should still generate valid header and implementation
        assert len(files) == 2
        header = files['picomsg_generated.h']
        
        # Should contain basic includes and error enum
        assert '#include <stdint.h>' in header
        assert 'typedef enum' in header
        assert 'OK = 0' in header
    
    def test_round_trip_data_integrity(self):
        """Test that data maintains integrity through serialization/deserialization."""
        schema_text = """
        namespace integrity.test;
        
        struct TestData {
            u8_val: u8;
            u16_val: u16;
            u32_val: u32;
            u64_val: u64;
            i8_val: i8;
            i16_val: i16;
            i32_val: i32;
            i64_val: i64;
            f32_val: f32;
            f64_val: f64;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        generator = CCodeGenerator(schema)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generator.write_files(output_dir)
            
            # Create integrity test program
            integrity_test = """
#include "picomsg_generated.h"
#include <stdio.h>
#include <assert.h>
#include <math.h>

int main() {
    integrity_test_testdata_t original = {
        .u8_val = 255,
        .u16_val = 65535,
        .u32_val = 4294967295U,
        .u64_val = 18446744073709551615ULL,
        .i8_val = -128,
        .i16_val = -32768,
        .i32_val = -2147483648,
        .i64_val = -9223372036854775807LL,
        .f32_val = 3.14159f,
        .f64_val = 2.718281828459045
    };
    
    uint8_t buffer[256];
    size_t size = sizeof(buffer);
    
    // Serialize
    integrity_test_error_t result = integrity_test_testdata_to_bytes(&original, buffer, &size);
    assert(result == INTEGRITY_TEST_OK);
    
    // Deserialize
    integrity_test_testdata_t restored;
    result = integrity_test_testdata_from_bytes(buffer, size, &restored);
    assert(result == INTEGRITY_TEST_OK);
    
    // Verify all values
    assert(restored.u8_val == original.u8_val);
    assert(restored.u16_val == original.u16_val);
    assert(restored.u32_val == original.u32_val);
    assert(restored.u64_val == original.u64_val);
    assert(restored.i8_val == original.i8_val);
    assert(restored.i16_val == original.i16_val);
    assert(restored.i32_val == original.i32_val);
    assert(restored.i64_val == original.i64_val);
    assert(fabsf(restored.f32_val - original.f32_val) < 1e-6f);
    assert(fabs(restored.f64_val - original.f64_val) < 1e-15);
    
    printf("Data integrity test passed!\\n");
    return 0;
}
"""
            
            test_file = output_dir / 'integrity_test.c'
            test_file.write_text(integrity_test)
            
            executable = output_dir / 'integrity_test'
            
            try:
                compile_result = subprocess.run([
                    'gcc', str(test_file), str(output_dir / 'picomsg_generated.c'),
                    '-o', str(executable), '-std=c99', '-lm'
                ], capture_output=True, text=True, timeout=10)
                
                assert compile_result.returncode == 0
                
                run_result = subprocess.run([str(executable)], 
                                          capture_output=True, text=True, timeout=5)
                
                assert run_result.returncode == 0
                assert "Data integrity test passed!" in run_result.stdout
                
            except FileNotFoundError:
                pytest.skip("gcc not available for integrity test") 
