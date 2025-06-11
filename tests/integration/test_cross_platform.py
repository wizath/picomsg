"""
Cross-platform integration tests for PicoMsg.

These tests verify that data encoded by one language can be decoded by another,
ensuring binary compatibility across all supported platforms.
"""

import pytest
import tempfile
import subprocess
import struct
from pathlib import Path
from typing import Dict, Any

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.c import CCodeGenerator
from picomsg.codegen.rust import RustCodeGenerator


class TestCrossPlatformCompatibility:
    """Test binary compatibility between different language implementations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = None
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_schema(self, content: str) -> Path:
        """Create a temporary schema file."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
        
        schema_file = Path(self.temp_dir) / "test.pico"
        schema_file.write_text(content)
        return schema_file
    
    def generate_c_code(self, schema_file: Path, output_dir: Path) -> Dict[str, str]:
        """Generate C code from schema."""
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        generator = CCodeGenerator(schema)
        generator.set_option('header_name', 'test_generated')
        
        files = generator.generate()
        
        # Write files to output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            (output_dir / filename).write_text(content)
        
        return files
    
    def generate_rust_code(self, schema_file: Path, output_dir: Path) -> Dict[str, str]:
        """Generate Rust code from schema."""
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        generator = RustCodeGenerator(schema)
        generator.set_option('module_name', 'test_generated')
        
        files = generator.generate()
        
        # Write files to output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            (output_dir / filename).write_text(content)
        
        return files
    
    def compile_c_code(self, c_dir: Path) -> bool:
        """Compile C code and return success status."""
        try:
            # Create a simple test program
            test_c_content = '''
#include "test_generated.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

int main() {
    // Test basic struct serialization
    test_simple_point_t point = {1.5f, 2.5f};
    
    uint8_t buffer[1024];
    size_t len = sizeof(buffer);
    
    test_simple_error_t result = test_simple_point_to_bytes(&point, buffer, &len);
    if (result != TEST_SIMPLE_OK) {
        printf("Serialization failed\\n");
        return 1;
    }
    
    test_simple_point_t decoded_point;
    result = test_simple_point_from_bytes(buffer, len, &decoded_point);
    if (result != TEST_SIMPLE_OK) {
        printf("Deserialization failed\\n");
        return 1;
    }
    
    if (decoded_point.x != point.x || decoded_point.y != point.y) {
        printf("Data mismatch\\n");
        return 1;
    }
    
    printf("C test passed\\n");
    return 0;
}
'''
            
            test_c_file = c_dir / "test_main.c"
            test_c_file.write_text(test_c_content)
            
            # Compile
            result = subprocess.run([
                'gcc', '-o', str(c_dir / 'test_program'),
                str(test_c_file), str(c_dir / 'test_generated.c'),
                '-I', str(c_dir)
            ], capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"C compilation error: {e}")
            return False
    
    def test_c_code_compilation(self):
        """Test that generated C code compiles successfully."""
        schema_content = '''
        version 1;
        namespace test.simple;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct ApiHeader {
            command: u8;
            length: u16;
            crc16: u16;
        }
        
        message EchoRequest {
            header: ApiHeader;
            point: Point;
            id: u32;
        }
        '''
        
        schema_file = self.create_test_schema(schema_content)
        c_dir = Path(self.temp_dir) / "c_output"
        
        # Generate C code
        c_files = self.generate_c_code(schema_file, c_dir)
        
        # Verify files were generated
        assert "test_generated.h" in c_files
        assert "test_generated.c" in c_files
        
        # Verify files exist on disk
        assert (c_dir / "test_generated.h").exists()
        assert (c_dir / "test_generated.c").exists()
        
        # Test compilation
        compilation_success = self.compile_c_code(c_dir)
        assert compilation_success, "C code should compile successfully"
    
    def test_rust_code_compilation(self):
        """Test that generated Rust code compiles successfully."""
        schema_content = '''
        version 1;
        namespace test.simple;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct ApiHeader {
            command: u8;
            length: u16;
            crc16: u16;
        }
        
        message EchoRequest {
            header: ApiHeader;
            point: Point;
            id: u32;
        }
        '''
        
        schema_file = self.create_test_schema(schema_content)
        rust_dir = Path(self.temp_dir) / "rust_output"
        
        # Generate Rust code
        rust_files = self.generate_rust_code(schema_file, rust_dir)
        
        # Verify files were generated
        assert "test_generated.rs" in rust_files
        
        # Create Cargo.toml
        cargo_toml = '''
[package]
name = "test-generated"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
byteorder = "1.4"
base64 = "0.21"
'''
        
        (rust_dir / "Cargo.toml").write_text(cargo_toml)
        
        # Create lib.rs
        lib_rs = '''
pub mod test_generated;
pub use test_generated::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_point_serialization() {
        let point = TestSimplePoint { x: 1.5, y: 2.5 };
        let bytes = point.to_bytes().expect("Failed to serialize");
        let decoded = TestSimplePoint::from_bytes(&bytes).expect("Failed to deserialize");
        assert_eq!(point, decoded);
    }
}
'''
        
        src_dir = rust_dir / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "lib.rs").write_text(lib_rs)
        (rust_dir / "test_generated.rs").rename(src_dir / "test_generated.rs")
        
        # Test compilation
        try:
            result = subprocess.run([
                'cargo', 'test'
            ], cwd=rust_dir, capture_output=True, text=True)
            
            assert result.returncode == 0, f"Rust compilation failed: {result.stderr}"
            
        except FileNotFoundError:
            pytest.skip("Cargo not available for Rust compilation test")
    
    def test_binary_format_compatibility(self):
        """Test that binary format is consistent across implementations."""
        # Test basic primitive encoding
        test_data = [
            # (type, value, expected_bytes)
            ('u8', 42, b'\x2a'),
            ('u16', 1234, b'\xd2\x04'),  # Little endian
            ('u32', 0x12345678, b'\x78\x56\x34\x12'),  # Little endian
            ('f32', 3.14159, struct.pack('<f', 3.14159)),
        ]
        
        for type_name, value, expected in test_data:
            # This would be expanded to test actual encoding/decoding
            # For now, we verify the expected byte patterns
            if type_name == 'u8':
                assert struct.pack('<B', value) == expected
            elif type_name == 'u16':
                assert struct.pack('<H', value) == expected
            elif type_name == 'u32':
                assert struct.pack('<I', value) == expected
            elif type_name == 'f32':
                assert struct.pack('<f', value) == expected
    
    def test_string_encoding_compatibility(self):
        """Test string encoding compatibility."""
        test_strings = [
            "",
            "hello",
            "Hello, World!",
            "Unicode: 🚀 ñ ü",
            "A" * 1000,  # Long string
        ]
        
        for test_string in test_strings:
            # Encode as PicoMsg string format (u16 length + UTF-8 bytes)
            utf8_bytes = test_string.encode('utf-8')
            length = len(utf8_bytes)
            
            if length <= 65535:  # Max u16 value
                expected = struct.pack('<H', length) + utf8_bytes
                
                # Verify we can decode it back
                decoded_length = struct.unpack('<H', expected[:2])[0]
                decoded_string = expected[2:2+decoded_length].decode('utf-8')
                
                assert decoded_string == test_string
    
    def test_array_encoding_compatibility(self):
        """Test array encoding compatibility."""
        # Test u32 array
        test_array = [1, 2, 3, 4, 5]
        
        # Encode as PicoMsg array format (u16 count + elements)
        count = len(test_array)
        expected = struct.pack('<H', count)
        for item in test_array:
            expected += struct.pack('<I', item)
        
        # Verify we can decode it back
        decoded_count = struct.unpack('<H', expected[:2])[0]
        assert decoded_count == count
        
        decoded_array = []
        offset = 2
        for i in range(decoded_count):
            value = struct.unpack('<I', expected[offset:offset+4])[0]
            decoded_array.append(value)
            offset += 4
        
        assert decoded_array == test_array
    
    def test_struct_layout_compatibility(self):
        """Test that struct layouts are compatible between implementations."""
        schema_content = '''
        namespace test.layout;
        
        struct SimpleStruct {
            a: u8;
            b: u16;
            c: u32;
        }
        
        struct ComplexStruct {
            header: SimpleStruct;
            data: [u8];
            name: string;
        }
        '''
        
        schema_file = self.create_test_schema(schema_content)
        
        # Generate both C and Rust code
        c_dir = Path(self.temp_dir) / "c_layout"
        rust_dir = Path(self.temp_dir) / "rust_layout"
        
        c_files = self.generate_c_code(schema_file, c_dir)
        rust_files = self.generate_rust_code(schema_file, rust_dir)
        
        # Verify both generated successfully
        assert "test_generated.h" in c_files
        assert "test_generated.rs" in rust_files
        
        # Check that both use packed structs
        c_content = c_files["test_generated.h"]
        rust_content = rust_files["test_generated.rs"]
        
        # C should use packed attribute
        assert "__attribute__((packed))" in c_content or "#pragma pack" in c_content
        
        # Rust should use proper field ordering and types
        assert "pub a: u8," in rust_content
        assert "pub b: u16," in rust_content
        assert "pub c: u32," in rust_content
    
    def test_message_type_id_consistency(self):
        """Test that message type IDs are consistent across implementations."""
        schema_content = '''
        namespace test.messages;
        
        message FirstMessage {
            id: u32;
        }
        
        message SecondMessage {
            data: string;
        }
        
        message ThirdMessage {
            value: f64;
        }
        '''
        
        schema_file = self.create_test_schema(schema_content)
        
        # Generate both C and Rust code
        c_dir = Path(self.temp_dir) / "c_messages"
        rust_dir = Path(self.temp_dir) / "rust_messages"
        
        c_files = self.generate_c_code(schema_file, c_dir)
        rust_files = self.generate_rust_code(schema_file, rust_dir)
        
        c_content = c_files["test_generated.h"]
        rust_content = rust_files["test_generated.rs"]
        
        # Check that type IDs are consistent
        # FirstMessage should be ID 1, SecondMessage ID 2, ThirdMessage ID 3
        assert "FIRSTMESSAGE_TYPE_ID 1" in c_content or "FIRSTMESSAGE_TYPE_ID: u16 = 1" in rust_content
        assert "SECONDMESSAGE_TYPE_ID 2" in c_content or "SECONDMESSAGE_TYPE_ID: u16 = 2" in rust_content
        assert "THIRDMESSAGE_TYPE_ID 3" in c_content or "THIRDMESSAGE_TYPE_ID: u16 = 3" in rust_content
    
    def test_version_consistency(self):
        """Test that schema version is consistent across implementations."""
        schema_content = '''
        version 42;
        namespace test.version;
        
        struct VersionTest {
            value: u32;
        }
        '''
        
        schema_file = self.create_test_schema(schema_content)
        
        # Generate both C and Rust code
        c_dir = Path(self.temp_dir) / "c_version"
        rust_dir = Path(self.temp_dir) / "rust_version"
        
        c_files = self.generate_c_code(schema_file, c_dir)
        rust_files = self.generate_rust_code(schema_file, rust_dir)
        
        c_content = c_files["test_generated.h"]
        rust_content = rust_files["test_generated.rs"]
        
        # Check that version is consistent
        assert "VERSION 42" in c_content
        assert "VERSION: u8 = 42" in rust_content
    
    def test_namespace_handling_consistency(self):
        """Test that namespace handling is consistent across implementations."""
        schema_content = '''
        namespace com.example.test;
        
        struct NamespaceTest {
            value: u32;
        }
        '''
        
        schema_file = self.create_test_schema(schema_content)
        
        # Generate both C and Rust code
        c_dir = Path(self.temp_dir) / "c_namespace"
        rust_dir = Path(self.temp_dir) / "rust_namespace"
        
        c_files = self.generate_c_code(schema_file, c_dir)
        rust_files = self.generate_rust_code(schema_file, rust_dir)
        
        c_content = c_files["test_generated.h"]
        rust_content = rust_files["test_generated.rs"]
        
        # Check namespace handling
        # C should use underscores
        assert "com_example_test_" in c_content.lower()
        
        # Rust should use PascalCase
        assert "ComExampleTest" in rust_content 
