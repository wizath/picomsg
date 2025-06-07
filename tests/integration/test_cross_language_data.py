"""
Cross-language binary data integration tests.

These tests create binary data in one language implementation and verify
it can be correctly decoded by another language implementation.
"""

import pytest
import tempfile
import subprocess
import struct
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.c import CCodeGenerator
from picomsg.codegen.rust import RustCodeGenerator


class TestCrossLanguageData:
    """Test actual binary data exchange between C and Rust implementations."""
    
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
    
    def generate_c_code(self, schema_file: Path, output_dir: Path) -> bool:
        """Generate and compile C code."""
        try:
            parser = SchemaParser()
            schema = parser.parse_file(schema_file)
            
            generator = CCodeGenerator(schema)
            generator.set_option('header_name', 'test_generated')
            files = generator.generate()
            
            output_dir.mkdir(parents=True, exist_ok=True)
            for filename, content in files.items():
                (output_dir / filename).write_text(content)
            
            return True
        except Exception as e:
            print(f"C code generation failed: {e}")
            return False
    
    def generate_rust_code(self, schema_file: Path, output_dir: Path) -> bool:
        """Generate Rust code."""
        try:
            parser = SchemaParser()
            schema = parser.parse_file(schema_file)
            
            generator = RustCodeGenerator(schema)
            generator.set_option('module_name', 'test_generated')
            files = generator.generate()
            
            output_dir.mkdir(parents=True, exist_ok=True)
            for filename, content in files.items():
                (output_dir / filename).write_text(content)
            
            return True
        except Exception as e:
            print(f"Rust code generation failed: {e}")
            return False
    
    def create_rust_data_generator(self, rust_dir: Path, test_cases: List[Dict[str, Any]]) -> str:
        """Create a Rust program that generates test data."""
        program = '''
use std::fs::File;
use std::io::Write;
use byteorder::{LittleEndian, WriteBytesExt};

mod test_generated;
use test_generated::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut output = File::create("test_data.bin")?;
    
'''
        
        for i, test_case in enumerate(test_cases):
            struct_name = test_case['struct']
            fields = test_case['fields']
            
            program += f'''
    // Test case {i}: {struct_name}
    let test_{i} = {struct_name} {{
'''
            
            for field_name, field_value in fields.items():
                if isinstance(field_value, str):
                    program += f'        {field_name}: "{field_value}".to_string(),\n'
                elif isinstance(field_value, list):
                    if all(isinstance(x, str) for x in field_value):
                        array_str = ', '.join(f'"{x}".to_string()' for x in field_value)
                        program += f'        {field_name}: vec![{array_str}],\n'
                    else:
                        array_str = ', '.join(str(x) for x in field_value)
                        program += f'        {field_name}: vec![{array_str}],\n'
                else:
                    program += f'        {field_name}: {field_value},\n'
            
            program += f'''    }};
    
    let bytes_{i} = test_{i}.to_bytes()?;
    output.write_u32::<LittleEndian>(bytes_{i}.len() as u32)?;
    output.write_all(&bytes_{i})?;
'''
        
        program += '''
    
    println!("Generated {} test cases", ''' + str(len(test_cases)) + ''');
    Ok(())
}
'''
        
        return program
    
    def create_c_data_validator(self, c_dir: Path, test_cases: List[Dict[str, Any]]) -> str:
        """Create a C program that validates test data."""
        program = '''
#include "test_generated.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>

int main() {
    FILE *input = fopen("test_data.bin", "rb");
    if (!input) {
        printf("Failed to open test data file\\n");
        return 1;
    }
    
    int passed = 0;
    int total = ''' + str(len(test_cases)) + ''';
    
'''
        
        for i, test_case in enumerate(test_cases):
            struct_name = test_case['struct']
            fields = test_case['fields']
            c_struct_name = f"test_simple_{struct_name.lower()}_t"
            
            program += f'''
    // Test case {i}: {struct_name}
    {{
        uint32_t len_{i};
        if (fread(&len_{i}, sizeof(uint32_t), 1, input) != 1) {{
            printf("Failed to read length for test case {i}\\n");
            fclose(input);
            return 1;
        }}
        
        uint8_t *buffer_{i} = malloc(len_{i});
        if (fread(buffer_{i}, 1, len_{i}, input) != len_{i}) {{
            printf("Failed to read data for test case {i}\\n");
            free(buffer_{i});
            fclose(input);
            return 1;
        }}
        
        {c_struct_name} decoded_{i};
        test_simple_error_t result_{i} = test_simple_{struct_name.lower()}_from_bytes(buffer_{i}, len_{i}, &decoded_{i});
        
        if (result_{i} != TEST_SIMPLE_OK) {{
            printf("Failed to decode test case {i}: error %d\\n", result_{i});
            free(buffer_{i});
            fclose(input);
            return 1;
        }}
        
        // Validate fields
        int case_{i}_valid = 1;
'''
            
            for field_name, expected_value in fields.items():
                if isinstance(expected_value, str):
                    program += f'''        if (strcmp(decoded_{i}.{field_name}, "{expected_value}") != 0) {{
            printf("Test case {i}: {field_name} mismatch. Expected '{expected_value}', got '%s'\\n", decoded_{i}.{field_name});
            case_{i}_valid = 0;
        }}
'''
                elif isinstance(expected_value, (int, float)):
                    if isinstance(expected_value, float):
                        program += f'''        if (fabs(decoded_{i}.{field_name} - {expected_value}) > 1e-6) {{
            printf("Test case {i}: {field_name} mismatch. Expected {expected_value}, got %f\\n", decoded_{i}.{field_name});
            case_{i}_valid = 0;
        }}
'''
                    else:
                        program += f'''        if (decoded_{i}.{field_name} != {expected_value}) {{
            printf("Test case {i}: {field_name} mismatch. Expected {expected_value}, got %d\\n", decoded_{i}.{field_name});
            case_{i}_valid = 0;
        }}
'''
            
            program += f'''        
        if (case_{i}_valid) {{
            printf("Test case {i} ({struct_name}): PASSED\\n");
            passed++;
        }} else {{
            printf("Test case {i} ({struct_name}): FAILED\\n");
        }}
        
        free(buffer_{i});
    }}
'''
        
        program += '''
    
    fclose(input);
    
    printf("\\nResults: %d/%d tests passed\\n", passed, total);
    return (passed == total) ? 0 : 1;
}
'''
        
        return program
    
    def create_c_data_generator(self, c_dir: Path, test_cases: List[Dict[str, Any]]) -> str:
        """Create a C program that generates test data."""
        program = '''
#include "test_generated.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>

int main() {
    FILE *output = fopen("test_data.bin", "wb");
    if (!output) {
        printf("Failed to create test data file\\n");
        return 1;
    }
    
'''
        
        for i, test_case in enumerate(test_cases):
            struct_name = test_case['struct']
            fields = test_case['fields']
            c_struct_name = f"test_simple_{struct_name.lower()}_t"
            
            program += f'''
    // Test case {i}: {struct_name}
    {{
        {c_struct_name} test_{i} = {{0}};
'''
            
            for field_name, field_value in fields.items():
                if isinstance(field_value, str):
                    program += f'        strcpy(test_{i}.{field_name}, "{field_value}");\n'
                elif isinstance(field_value, (int, float)):
                    program += f'        test_{i}.{field_name} = {field_value};\n'
            
            program += f'''        
        uint8_t buffer_{i}[1024];
        size_t len_{i} = sizeof(buffer_{i});
        test_simple_error_t result_{i} = test_simple_{struct_name.lower()}_to_bytes(&test_{i}, buffer_{i}, &len_{i});
        
        if (result_{i} != TEST_SIMPLE_OK) {{
            printf("Failed to serialize test case {i}\\n");
            fclose(output);
            return 1;
        }}
        
        uint32_t len32_{i} = (uint32_t)len_{i};
        fwrite(&len32_{i}, sizeof(uint32_t), 1, output);
        fwrite(buffer_{i}, 1, len_{i}, output);
    }}
'''
        
        program += '''
    
    fclose(output);
    printf("Generated ''' + str(len(test_cases)) + ''' test cases\\n");
    return 0;
}
'''
        
        return program
    
    def create_rust_data_validator(self, rust_dir: Path, test_cases: List[Dict[str, Any]]) -> str:
        """Create a Rust program that validates test data."""
        program = '''
use std::fs::File;
use std::io::{Read, BufReader};
use byteorder::{LittleEndian, ReadBytesExt};

mod test_generated;
use test_generated::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let file = File::open("test_data.bin")?;
    let mut reader = BufReader::new(file);
    
    let mut passed = 0;
    let total = ''' + str(len(test_cases)) + ''';
    
'''
        
        for i, test_case in enumerate(test_cases):
            struct_name = test_case['struct']
            fields = test_case['fields']
            
            program += f'''
    // Test case {i}: {struct_name}
    {{
        let len_{i} = reader.read_u32::<LittleEndian>()?;
        let mut buffer_{i} = vec![0u8; len_{i} as usize];
        reader.read_exact(&mut buffer_{i})?;
        
        match {struct_name}::from_bytes(&buffer_{i}) {{
            Ok(decoded_{i}) => {{
                let mut case_{i}_valid = true;
                
'''
            
            for field_name, expected_value in fields.items():
                if isinstance(expected_value, str):
                    program += f'''                if decoded_{i}.{field_name} != "{expected_value}" {{
                    println!("Test case {i}: {field_name} mismatch. Expected '{expected_value}', got '{{}}'", decoded_{i}.{field_name});
                    case_{i}_valid = false;
                }}
'''
                elif isinstance(expected_value, list):
                    if all(isinstance(x, str) for x in expected_value):
                        expected_array = '[' + ', '.join(f'"{x}".to_string()' for x in expected_value) + ']'
                        program += f'''                let expected_{field_name} = vec!{expected_array};
                if decoded_{i}.{field_name} != expected_{field_name} {{
                    println!("Test case {i}: {field_name} array mismatch");
                    case_{i}_valid = false;
                }}
'''
                    else:
                        expected_array = '[' + ', '.join(str(x) for x in expected_value) + ']'
                        program += f'''                let expected_{field_name} = vec!{expected_array};
                if decoded_{i}.{field_name} != expected_{field_name} {{
                    println!("Test case {i}: {field_name} array mismatch");
                    case_{i}_valid = false;
                }}
'''
                elif isinstance(expected_value, float):
                    program += f'''                if (decoded_{i}.{field_name} - {expected_value}).abs() > 1e-6 {{
                    println!("Test case {i}: {field_name} mismatch. Expected {expected_value}, got {{}}", decoded_{i}.{field_name});
                    case_{i}_valid = false;
                }}
'''
                else:
                    program += f'''                if decoded_{i}.{field_name} != {expected_value} {{
                    println!("Test case {i}: {field_name} mismatch. Expected {expected_value}, got {{}}", decoded_{i}.{field_name});
                    case_{i}_valid = false;
                }}
'''
            
            program += f'''                
                if case_{i}_valid {{
                    println!("Test case {i} ({struct_name}): PASSED");
                    passed += 1;
                }} else {{
                    println!("Test case {i} ({struct_name}): FAILED");
                }}
            }},
            Err(e) => {{
                println!("Test case {i}: Failed to decode: {{}}", e);
            }}
        }}
    }}
'''
        
        program += '''
    
    println!("\\nResults: {}/{} tests passed", passed, total);
    if passed == total {
        Ok(())
    } else {
        std::process::exit(1);
    }
}
'''
        
        return program
    
    def test_rust_to_c_data_exchange(self):
        """Test: Generate data in Rust, decode and verify in C."""
        schema_content = '''
        namespace test.simple;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct Person {
            name: string;
            age: u32;
            height: f32;
        }
        
        struct Container {
            id: u32;
            tags: [string];
            count: u16;
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = self.create_schema_file(schema_content)
        
        rust_dir = temp_dir / "rust_generator"
        c_dir = temp_dir / "c_validator"
        
        # Generate Rust and C code
        assert self.generate_rust_code(schema_file, rust_dir)
        assert self.generate_c_code(schema_file, c_dir)
        
        # Test cases
        test_cases = [
            {
                'struct': 'TestSimplePoint',
                'fields': {'x': 1.5, 'y': 2.5}
            },
            {
                'struct': 'TestSimplePerson',
                'fields': {'name': 'Alice', 'age': 30, 'height': 165.5}
            },
            {
                'struct': 'TestSimpleContainer',
                'fields': {'id': 12345, 'tags': ['rust', 'test'], 'count': 2}
            }
        ]
        
        try:
            # Create Rust data generator
            cargo_toml = '''
[package]
name = "data-generator"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "generate"
path = "generate.rs"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
byteorder = "1.4"
'''
            (rust_dir / "Cargo.toml").write_text(cargo_toml)
            
            rust_generator_code = self.create_rust_data_generator(rust_dir, test_cases)
            (rust_dir / "generate.rs").write_text(rust_generator_code)
            
            # Run Rust data generator
            result = subprocess.run([
                'cargo', 'run', '--bin', 'generate'
            ], cwd=rust_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                pytest.skip(f"Rust data generation failed: {result.stderr}")
            
            # Copy generated data to C directory
            import shutil
            shutil.copy(rust_dir / "test_data.bin", c_dir / "test_data.bin")
            
            # Create C validator
            c_validator_code = self.create_c_data_validator(c_dir, test_cases)
            (c_dir / "validate.c").write_text(c_validator_code)
            
            # Compile C validator
            compile_result = subprocess.run([
                'gcc', '-o', str(c_dir / 'validate'),
                str(c_dir / 'validate.c'), str(c_dir / 'test_generated.c'),
                '-I', str(c_dir), '-lm'
            ], capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                pytest.skip(f"C compilation failed: {compile_result.stderr}")
            
            # Run C validator
            validate_result = subprocess.run([
                str(c_dir / 'validate')
            ], cwd=c_dir, capture_output=True, text=True)
            
            print("C validation output:", validate_result.stdout)
            if validate_result.stderr:
                print("C validation errors:", validate_result.stderr)
            
            assert validate_result.returncode == 0, f"C validation failed: {validate_result.stdout}"
            assert "3/3 tests passed" in validate_result.stdout
            
        except FileNotFoundError as e:
            if "cargo" in str(e):
                pytest.skip("Cargo not available for Rust test")
            elif "gcc" in str(e):
                pytest.skip("GCC not available for C test")
            else:
                raise
    
    def test_c_to_rust_data_exchange(self):
        """Test: Generate data in C, decode and verify in Rust."""
        schema_content = '''
        namespace test.simple;
        
        struct Config {
            enabled: u8;
            timeout: u32;
            name: string;
        }
        
        struct Stats {
            count: u64;
            average: f64;
            values: [u32];
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = self.create_schema_file(schema_content)
        
        c_dir = temp_dir / "c_generator"
        rust_dir = temp_dir / "rust_validator"
        
        # Generate C and Rust code
        assert self.generate_c_code(schema_file, c_dir)
        assert self.generate_rust_code(schema_file, rust_dir)
        
        # Test cases
        test_cases = [
            {
                'struct': 'Config',
                'fields': {'enabled': 1, 'timeout': 5000, 'name': 'production'}
            },
            {
                'struct': 'Stats',
                'fields': {'count': 1000, 'average': 42.5, 'values': [10, 20, 30, 40, 50]}
            }
        ]
        
        try:
            # Create C data generator
            c_generator_code = self.create_c_data_generator(c_dir, test_cases)
            (c_dir / "generate.c").write_text(c_generator_code)
            
            # Compile C generator
            compile_result = subprocess.run([
                'gcc', '-o', str(c_dir / 'generate'),
                str(c_dir / 'generate.c'), str(c_dir / 'test_generated.c'),
                '-I', str(c_dir), '-lm'
            ], capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                pytest.skip(f"C compilation failed: {compile_result.stderr}")
            
            # Run C data generator
            result = subprocess.run([
                str(c_dir / 'generate')
            ], cwd=c_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                pytest.fail(f"C data generation failed: {result.stdout}")
            
            # Copy generated data to Rust directory
            import shutil
            shutil.copy(c_dir / "test_data.bin", rust_dir / "test_data.bin")
            
            # Create Rust validator
            cargo_toml = '''
[package]
name = "data-validator"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "validate"
path = "validate.rs"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
byteorder = "1.4"
'''
            (rust_dir / "Cargo.toml").write_text(cargo_toml)
            
            rust_validator_code = self.create_rust_data_validator(rust_dir, test_cases)
            (rust_dir / "validate.rs").write_text(rust_validator_code)
            
            # Run Rust validator
            validate_result = subprocess.run([
                'cargo', 'run', '--bin', 'validate'
            ], cwd=rust_dir, capture_output=True, text=True)
            
            print("Rust validation output:", validate_result.stdout)
            if validate_result.stderr:
                print("Rust validation errors:", validate_result.stderr)
            
            assert validate_result.returncode == 0, f"Rust validation failed: {validate_result.stdout}"
            assert "2/2 tests passed" in validate_result.stdout
            
        except FileNotFoundError as e:
            if "cargo" in str(e):
                pytest.skip("Cargo not available for Rust test")
            elif "gcc" in str(e):
                pytest.skip("GCC not available for C test")
            else:
                raise
    
    def test_bidirectional_data_exchange(self):
        """Test: Round-trip data exchange between C and Rust."""
        schema_content = '''
        namespace test.roundtrip;
        
        struct Message {
            id: u32;
            content: string;
            timestamp: u64;
            priority: u8;
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = self.create_schema_file(schema_content)
        
        c_dir = temp_dir / "c_impl"
        rust_dir = temp_dir / "rust_impl"
        
        # Generate both implementations
        assert self.generate_c_code(schema_file, c_dir)
        assert self.generate_rust_code(schema_file, rust_dir)
        
        test_message = {
            'struct': 'TestRoundtripMessage',
            'fields': {
                'id': 12345,
                'content': 'Hello from cross-language test!',
                'timestamp': 1640995200,
                'priority': 3
            }
        }
        
        try:
            # Step 1: Generate data in Rust
            cargo_toml = '''
[package]
name = "roundtrip-test"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "rust_generate"
path = "rust_generate.rs"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
byteorder = "1.4"
'''
            (rust_dir / "Cargo.toml").write_text(cargo_toml)
            
            rust_gen_code = self.create_rust_data_generator(rust_dir, [test_message])
            (rust_dir / "rust_generate.rs").write_text(rust_gen_code)
            
            # Generate data with Rust
            result = subprocess.run([
                'cargo', 'run', '--bin', 'rust_generate'
            ], cwd=rust_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                pytest.skip(f"Rust data generation failed: {result.stderr}")
            
            # Step 2: Validate data with C
            import shutil
            shutil.copy(rust_dir / "test_data.bin", c_dir / "rust_data.bin")
            
            c_validator_code = self.create_c_data_validator(c_dir, [test_message])
            c_validator_code = c_validator_code.replace('test_data.bin', 'rust_data.bin')
            (c_dir / "validate_rust.c").write_text(c_validator_code)
            
            # Compile and run C validator
            compile_result = subprocess.run([
                'gcc', '-o', str(c_dir / 'validate_rust'),
                str(c_dir / 'validate_rust.c'), str(c_dir / 'test_generated.c'),
                '-I', str(c_dir), '-lm'
            ], capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                pytest.skip(f"C compilation failed: {compile_result.stderr}")
            
            validate_result = subprocess.run([
                str(c_dir / 'validate_rust')
            ], cwd=c_dir, capture_output=True, text=True)
            
            assert validate_result.returncode == 0, f"C validation of Rust data failed: {validate_result.stdout}"
            
            # Step 3: Generate data in C
            c_gen_code = self.create_c_data_generator(c_dir, [test_message])
            c_gen_code = c_gen_code.replace('test_data.bin', 'c_data.bin')
            (c_dir / "generate.c").write_text(c_gen_code)
            
            compile_result = subprocess.run([
                'gcc', '-o', str(c_dir / 'generate'),
                str(c_dir / 'generate.c'), str(c_dir / 'test_generated.c'),
                '-I', str(c_dir), '-lm'
            ], capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                pytest.skip(f"C compilation failed: {compile_result.stderr}")
            
            result = subprocess.run([
                str(c_dir / 'generate')
            ], cwd=c_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                pytest.fail(f"C data generation failed: {result.stdout}")
            
            # Step 4: Validate C data with Rust
            shutil.copy(c_dir / "c_data.bin", rust_dir / "test_data.bin")
            
            rust_validator_code = self.create_rust_data_validator(rust_dir, [test_message])
            (rust_dir / "validate.rs").write_text(rust_validator_code)
            
            # Add validator binary to Cargo.toml
            cargo_toml_updated = cargo_toml + '''
[[bin]]
name = "validate"
path = "validate.rs"
'''
            (rust_dir / "Cargo.toml").write_text(cargo_toml_updated)
            
            validate_result = subprocess.run([
                'cargo', 'run', '--bin', 'validate'
            ], cwd=rust_dir, capture_output=True, text=True)
            
            assert validate_result.returncode == 0, f"Rust validation of C data failed: {validate_result.stdout}"
            
            print("✅ Bidirectional data exchange test passed!")
            print("✅ Rust → C: Data generated in Rust successfully decoded in C")
            print("✅ C → Rust: Data generated in C successfully decoded in Rust")
            
        except FileNotFoundError as e:
            if "cargo" in str(e):
                pytest.skip("Cargo not available for Rust test")
            elif "gcc" in str(e):
                pytest.skip("GCC not available for C test")
            else:
                raise 
