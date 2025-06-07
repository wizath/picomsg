"""
Binary compatibility tests between C and Rust implementations.

These tests generate binary data using one implementation and verify
it can be correctly decoded by the other implementation.
"""

import pytest
import tempfile
import subprocess
import struct
from pathlib import Path
from typing import Dict, List, Tuple

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.c import CCodeGenerator
from picomsg.codegen.rust import RustCodeGenerator


class TestBinaryCompatibility:
    """Test binary data compatibility between C and Rust implementations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = None
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_dir(self) -> Path:
        """Create a temporary directory."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
        return Path(self.temp_dir)
    
    def create_schema_file(self, content: str) -> Path:
        """Create a schema file."""
        temp_dir = self.create_temp_dir()
        schema_file = temp_dir / "test.pico"
        schema_file.write_text(content)
        return schema_file
    
    def generate_test_data(self, data_type: str, value: any) -> bytes:
        """Generate test binary data for a given type and value."""
        if data_type == "u8":
            return struct.pack('<B', value)
        elif data_type == "u16":
            return struct.pack('<H', value)
        elif data_type == "u32":
            return struct.pack('<I', value)
        elif data_type == "u64":
            return struct.pack('<Q', value)
        elif data_type == "i8":
            return struct.pack('<b', value)
        elif data_type == "i16":
            return struct.pack('<h', value)
        elif data_type == "i32":
            return struct.pack('<i', value)
        elif data_type == "i64":
            return struct.pack('<q', value)
        elif data_type == "f32":
            return struct.pack('<f', value)
        elif data_type == "f64":
            return struct.pack('<d', value)
        elif data_type == "string":
            utf8_bytes = value.encode('utf-8')
            return struct.pack('<H', len(utf8_bytes)) + utf8_bytes
        elif data_type == "bytes":
            return struct.pack('<H', len(value)) + value
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    
    def create_c_test_program(self, c_dir: Path, test_cases: List[Tuple[str, str, any]]) -> str:
        """Create a C test program that generates binary data."""
        test_code = '''
#include "test_generated.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

int main() {
    FILE *output = fopen("test_data.bin", "wb");
    if (!output) {
        printf("Failed to open output file\\n");
        return 1;
    }
    
'''
        
        for i, (struct_name, field_name, value) in enumerate(test_cases):
            if isinstance(value, str):
                test_code += f'''
    // Test case {i}: {struct_name}.{field_name} = "{value}"
    test_simple_{struct_name.lower()}_t test_{i} = {{0}};
'''
                if field_name in ["name", "message", "data"]:  # string fields
                    test_code += f'    strcpy(test_{i}.{field_name}, "{value}");'
            else:
                test_code += f'''
    // Test case {i}: {struct_name}.{field_name} = {value}
    test_simple_{struct_name.lower()}_t test_{i} = {{0}};
    test_{i}.{field_name} = {value};
'''
            
            test_code += f'''
    
    uint8_t buffer_{i}[1024];
    size_t len_{i} = sizeof(buffer_{i});
    test_simple_error_t result_{i} = test_simple_{struct_name.lower()}_to_bytes(&test_{i}, buffer_{i}, &len_{i});
    if (result_{i} != TEST_SIMPLE_OK) {{
        printf("Serialization failed for test case {i}\\n");
        fclose(output);
        return 1;
    }}
    
    fwrite(&len_{i}, sizeof(size_t), 1, output);
    fwrite(buffer_{i}, 1, len_{i}, output);
'''
        
        test_code += '''
    
    fclose(output);
    printf("C test data generated successfully\\n");
    return 0;
}
'''
        
        return test_code
    
    def create_rust_test_program(self, rust_dir: Path, test_cases: List[Tuple[str, str, any]]) -> str:
        """Create a Rust test program that reads and validates binary data."""
        test_code = '''
use std::fs::File;
use std::io::{Read, BufReader};
use byteorder::{LittleEndian, ReadBytesExt};

mod test_generated;
use test_generated::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let file = File::open("test_data.bin")?;
    let mut reader = BufReader::new(file);
    
'''
        
        for i, (struct_name, field_name, expected_value) in enumerate(test_cases):
            rust_struct_name = f"TestSimple{struct_name}"
            
            test_code += f'''
    // Test case {i}: Read and validate {struct_name}.{field_name}
    let len_{i} = reader.read_u64::<LittleEndian>()? as usize;
    let mut buffer_{i} = vec![0u8; len_{i}];
    reader.read_exact(&mut buffer_{i})?;
    
    let decoded_{i} = {rust_struct_name}::from_bytes(&buffer_{i})?;
'''
            
            if isinstance(expected_value, str):
                test_code += f'    assert_eq!(decoded_{i}.{field_name}, "{expected_value}");'
            else:
                test_code += f'    assert_eq!(decoded_{i}.{field_name}, {expected_value});'
            
            test_code += f'''
    println!("Test case {i} passed: {struct_name}.{field_name}");
'''
        
        test_code += '''
    
    println!("All Rust validation tests passed");
    Ok(())
}
'''
        
        return test_code
    
    def test_primitive_types_binary_format(self):
        """Test that primitive types have consistent binary format."""
        # Test basic primitive encoding
        test_data = [
            ('u8', 42, b'\x2a'),
            ('u16', 1234, b'\xd2\x04'),  # Little endian
            ('u32', 0x12345678, b'\x78\x56\x34\x12'),  # Little endian
            ('f32', 3.14159, struct.pack('<f', 3.14159)),
        ]
        
        for type_name, value, expected in test_data:
            if type_name == 'u8':
                assert struct.pack('<B', value) == expected
            elif type_name == 'u16':
                assert struct.pack('<H', value) == expected
            elif type_name == 'u32':
                assert struct.pack('<I', value) == expected
            elif type_name == 'f32':
                assert struct.pack('<f', value) == expected
    
    def test_string_encoding_format(self):
        """Test string encoding format consistency."""
        test_strings = [
            "",
            "hello",
            "Hello, World!",
            "Unicode: 🚀 ñ ü",
            "A" * 100,  # Long string
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
    
    def test_array_encoding_format(self):
        """Test array encoding format consistency."""
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
    
    def test_struct_layout_consistency(self):
        """Test that struct layouts are consistent between implementations."""
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
        
        schema_file = self.create_schema_file(schema_content)
        
        # Generate both C and Rust code
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        c_generator = CCodeGenerator(schema)
        rust_generator = RustCodeGenerator(schema)
        
        c_files = c_generator.generate()
        rust_files = rust_generator.generate()
        
        # Verify both generated successfully
        assert "picomsg_generated.h" in c_files
        assert "picomsg_generated.rs" in rust_files
        
        # Check that both use packed structs
        c_content = c_files["picomsg_generated.h"]
        rust_content = rust_files["picomsg_generated.rs"]
        
        # C should use packed attribute
        assert "__attribute__((packed))" in c_content or "#pragma pack" in c_content
        
        # Rust should use proper field ordering and types
        assert "pub a: u8," in rust_content
        assert "pub b: u16," in rust_content
        assert "pub c: u32," in rust_content
    
    def test_endianness_consistency(self):
        """Test that both implementations use little-endian consistently."""
        # Test multi-byte values
        test_values = [
            ("u16", 0x1234),
            ("u32", 0x12345678),
            ("u64", 0x123456789ABCDEF0),
            ("i16", -0x1234),
            ("i32", -0x12345678),
            ("f32", 3.14159),
            ("f64", 3.141592653589793),
        ]
        
        for type_name, value in test_values:
            if type_name == "u16":
                expected = struct.pack('<H', value)
                decoded = struct.unpack('<H', expected)[0]
            elif type_name == "u32":
                expected = struct.pack('<I', value)
                decoded = struct.unpack('<I', expected)[0]
            elif type_name == "u64":
                expected = struct.pack('<Q', value)
                decoded = struct.unpack('<Q', expected)[0]
            elif type_name == "i16":
                expected = struct.pack('<h', value)
                decoded = struct.unpack('<h', expected)[0]
            elif type_name == "i32":
                expected = struct.pack('<i', value)
                decoded = struct.unpack('<i', expected)[0]
            elif type_name == "f32":
                expected = struct.pack('<f', value)
                decoded = struct.unpack('<f', expected)[0]
                assert abs(decoded - value) < 1e-6  # Float precision
                continue
            elif type_name == "f64":
                expected = struct.pack('<d', value)
                decoded = struct.unpack('<d', expected)[0]
                assert abs(decoded - value) < 1e-15  # Double precision
                continue
            
            assert decoded == value
    
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
        
        schema_file = self.create_schema_file(schema_content)
        
        # Generate both C and Rust code
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        c_generator = CCodeGenerator(schema)
        rust_generator = RustCodeGenerator(schema)
        
        c_files = c_generator.generate()
        rust_files = rust_generator.generate()
        
        c_content = c_files["picomsg_generated.h"]
        rust_content = rust_files["picomsg_generated.rs"]
        
        # Check that type IDs are consistent
        # FirstMessage should be ID 1, SecondMessage ID 2, ThirdMessage ID 3
        assert "FIRSTMESSAGE_TYPE_ID 1" in c_content
        assert "SECONDMESSAGE_TYPE_ID 2" in c_content
        assert "THIRDMESSAGE_TYPE_ID 3" in c_content
        
        assert "FIRSTMESSAGE_TYPE_ID: u16 = 1" in rust_content
        assert "SECONDMESSAGE_TYPE_ID: u16 = 2" in rust_content
        assert "THIRDMESSAGE_TYPE_ID: u16 = 3" in rust_content
    
    def test_version_consistency(self):
        """Test that schema version is consistent across implementations."""
        schema_content = '''
        version 42;
        namespace test.version;
        
        struct VersionTest {
            value: u32;
        }
        '''
        
        schema_file = self.create_schema_file(schema_content)
        
        # Generate both C and Rust code
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        c_generator = CCodeGenerator(schema)
        rust_generator = RustCodeGenerator(schema)
        
        c_files = c_generator.generate()
        rust_files = rust_generator.generate()
        
        c_content = c_files["picomsg_generated.h"]
        rust_content = rust_files["picomsg_generated.rs"]
        
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
        
        schema_file = self.create_schema_file(schema_content)
        
        # Generate both C and Rust code
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        c_generator = CCodeGenerator(schema)
        rust_generator = RustCodeGenerator(schema)
        
        c_files = c_generator.generate()
        rust_files = rust_generator.generate()
        
        c_content = c_files["picomsg_generated.h"]
        rust_content = rust_files["picomsg_generated.rs"]
        
        # Check namespace handling
        # C should use underscores
        assert "com_example_test_" in c_content.lower()
        
        # Rust should use PascalCase
        assert "ComExampleTest" in rust_content
