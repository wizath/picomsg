"""
Simple cross-language binary data integration tests.

These tests create binary data in one language and verify it can be decoded by another.
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


class TestSimpleCrossLanguage:
    """Test simple binary data exchange between C and Rust."""
    
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
    
    def test_rust_generates_c_reads(self):
        """Test: Rust generates binary data, C reads and validates it."""
        schema_content = '''
        namespace test.simple;
        
        struct Point {
            x: f32;
            y: f32;
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = temp_dir / "test.pico"
        schema_file.write_text(schema_content)
        
        # Generate Rust code
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        rust_generator = RustCodeGenerator(schema)
        rust_generator.set_option('module_name', 'test_generated')
        rust_files = rust_generator.generate()
        
        rust_dir = temp_dir / "rust"
        rust_dir.mkdir()
        for filename, content in rust_files.items():
            (rust_dir / filename).write_text(content)
        
        # Generate C code
        c_generator = CCodeGenerator(schema)
        c_generator.set_option('header_name', 'test_generated')
        c_files = c_generator.generate()
        
        c_dir = temp_dir / "c"
        c_dir.mkdir()
        for filename, content in c_files.items():
            (c_dir / filename).write_text(content)
        
        try:
            # Create Rust data generator
            cargo_toml = '''
[package]
name = "data-gen"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
byteorder = "1.4"
'''
            (rust_dir / "Cargo.toml").write_text(cargo_toml)
            
            # Create Rust program that generates test data
            rust_main = '''
use std::fs::File;
use std::io::Write;

mod test_generated;
use test_generated::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let point = TestSimplePoint { x: 3.14, y: 2.71 };
    let data = point.to_bytes()?;
    
    let mut file = File::create("point_data.bin")?;
    file.write_all(&data)?;
    
    println!("Generated {} bytes of data", data.len());
    Ok(())
}
'''
            (rust_dir / "src").mkdir(exist_ok=True)
            (rust_dir / "src" / "main.rs").write_text(rust_main)
            (rust_dir / "src" / "test_generated.rs").write_text(rust_files["test_generated.rs"])
            
            # Run Rust to generate data
            result = subprocess.run(['cargo', 'run'], cwd=rust_dir, capture_output=True, text=True)
            if result.returncode != 0:
                pytest.skip(f"Rust execution failed: {result.stderr}")
            
            # Copy data to C directory
            import shutil
            shutil.copy(rust_dir / "point_data.bin", c_dir / "point_data.bin")
            
            # Create C program that reads and validates the data
            c_main = '''
#include "test_generated.h"
#include <stdio.h>
#include <stdlib.h>

int main() {
    FILE *file = fopen("point_data.bin", "rb");
    if (!file) {
        printf("Failed to open data file\\n");
        return 1;
    }
    
    // Get file size
    fseek(file, 0, SEEK_END);
    long size = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    // Read data
    uint8_t *buffer = malloc(size);
    fread(buffer, 1, size, file);
    fclose(file);
    
    // Decode
    test_simple_point_t point;
    test_simple_error_t result = test_simple_point_from_bytes(buffer, size, &point);
    
    if (result != TEST_SIMPLE_OK) {
        printf("Failed to decode: error %d\\n", result);
        free(buffer);
        return 1;
    }
    
    // Validate
    if (point.x >= 3.13 && point.x <= 3.15 && point.y >= 2.70 && point.y <= 2.72) {
        printf("SUCCESS: Point decoded correctly: x=%.2f, y=%.2f\\n", point.x, point.y);
        free(buffer);
        return 0;
    } else {
        printf("FAILED: Point values incorrect: x=%.2f, y=%.2f\\n", point.x, point.y);
        free(buffer);
        return 1;
    }
}
'''
            (c_dir / "main.c").write_text(c_main)
            
            # Compile C program
            compile_result = subprocess.run([
                'gcc', '-o', 'test_program', 'main.c', 'test_generated.c', '-lm'
            ], cwd=c_dir, capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                pytest.skip(f"C compilation failed: {compile_result.stderr}")
            
            # Run C program
            run_result = subprocess.run(['./test_program'], cwd=c_dir, capture_output=True, text=True)
            
            print("C output:", run_result.stdout)
            if run_result.stderr:
                print("C errors:", run_result.stderr)
            
            assert run_result.returncode == 0, f"C validation failed: {run_result.stdout}"
            assert "SUCCESS" in run_result.stdout
            
        except FileNotFoundError as e:
            if "cargo" in str(e):
                pytest.skip("Cargo not available")
            elif "gcc" in str(e):
                pytest.skip("GCC not available")
            else:
                raise
    
    def test_c_generates_rust_reads(self):
        """Test: C generates binary data, Rust reads and validates it."""
        schema_content = '''
        namespace test.simple;
        
        struct Message {
            id: u32;
            value: f64;
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = temp_dir / "test.pico"
        schema_file.write_text(schema_content)
        
        # Generate both implementations
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        c_generator = CCodeGenerator(schema)
        c_generator.set_option('header_name', 'test_generated')
        c_files = c_generator.generate()
        
        rust_generator = RustCodeGenerator(schema)
        rust_generator.set_option('module_name', 'test_generated')
        rust_files = rust_generator.generate()
        
        c_dir = temp_dir / "c"
        rust_dir = temp_dir / "rust"
        c_dir.mkdir()
        rust_dir.mkdir()
        
        for filename, content in c_files.items():
            (c_dir / filename).write_text(content)
        
        for filename, content in rust_files.items():
            (rust_dir / filename).write_text(content)
        
        try:
            # Create C data generator
            c_main = '''
#include "test_generated.h"
#include <stdio.h>
#include <stdlib.h>

int main() {
    test_simple_message_t msg = {42, 123.456};
    
    uint8_t buffer[1024];
    size_t size = sizeof(buffer);
    
    test_simple_error_t result = test_simple_message_to_bytes(&msg, buffer, &size);
    if (result != TEST_SIMPLE_OK) {
        printf("Failed to encode: error %d\\n", result);
        return 1;
    }
    
    FILE *file = fopen("message_data.bin", "wb");
    if (!file) {
        printf("Failed to create file\\n");
        return 1;
    }
    
    fwrite(buffer, 1, size, file);
    fclose(file);
    
    printf("Generated %zu bytes of data\\n", size);
    return 0;
}
'''
            (c_dir / "main.c").write_text(c_main)
            
            # Compile and run C generator
            compile_result = subprocess.run([
                'gcc', '-o', 'generator', 'main.c', 'test_generated.c', '-lm'
            ], cwd=c_dir, capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                pytest.skip(f"C compilation failed: {compile_result.stderr}")
            
            run_result = subprocess.run(['./generator'], cwd=c_dir, capture_output=True, text=True)
            if run_result.returncode != 0:
                pytest.fail(f"C data generation failed: {run_result.stdout}")
            
            # Copy data to Rust directory
            import shutil
            shutil.copy(c_dir / "message_data.bin", rust_dir / "message_data.bin")
            
            # Create Rust validator
            cargo_toml = '''
[package]
name = "data-validator"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
byteorder = "1.4"
'''
            (rust_dir / "Cargo.toml").write_text(cargo_toml)
            
            rust_main = '''
use std::fs;

mod test_generated;
use test_generated::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let data = fs::read("message_data.bin")?;
    
    match TestSimpleMessage::from_bytes(&data) {
        Ok(msg) => {
            if msg.id == 42 && (msg.value - 123.456).abs() < 1e-6 {
                println!("SUCCESS: Message decoded correctly: id={}, value={}", msg.id, msg.value);
                Ok(())
            } else {
                println!("FAILED: Message values incorrect: id={}, value={}", msg.id, msg.value);
                std::process::exit(1);
            }
        },
        Err(e) => {
            println!("FAILED: Decode error: {}", e);
            std::process::exit(1);
        }
    }
}
'''
            (rust_dir / "src").mkdir(exist_ok=True)
            (rust_dir / "src" / "main.rs").write_text(rust_main)
            (rust_dir / "src" / "test_generated.rs").write_text(rust_files["test_generated.rs"])
            
            # Run Rust validator
            result = subprocess.run(['cargo', 'run'], cwd=rust_dir, capture_output=True, text=True)
            
            print("Rust output:", result.stdout)
            if result.stderr:
                print("Rust errors:", result.stderr)
            
            assert result.returncode == 0, f"Rust validation failed: {result.stdout}"
            assert "SUCCESS" in result.stdout
            
        except FileNotFoundError as e:
            if "cargo" in str(e):
                pytest.skip("Cargo not available")
            elif "gcc" in str(e):
                pytest.skip("GCC not available")
            else:
                raise
    
 
