"""
Integration tests for Python interoperability.
"""

import pytest
import tempfile
import sys
import subprocess
from pathlib import Path

from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator


class TestPythonInterop:
    """Test Python interoperability."""
    
    def test_python_code_compilation(self):
        """Test that generated Python code compiles and runs."""
        schema_content = """
        namespace test.python;
        version 1;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message TestMessage {
            id: u32;
            point: Point;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        # Write to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write generated file
            for filename, content in files.items():
                (temp_path / filename).write_text(content)
            
            # Test that Python can import and run the module
            test_script = temp_path / "test_script.py"
            test_script.write_text("""
import picomsg_generated as pm

# Test basic creation
point = pm.TestPythonPoint(x=3.14, y=2.71)
print(f"Point: x={point.x}, y={point.y}")

# Test message creation
msg = pm.TestPythonTestMessage(id=42, point=point)
print(f"Message: id={msg.id}")

# Test JSON serialization
json_str = point.to_json()
print(f"JSON: {json_str}")

# Test binary serialization
binary_data = point.to_bytes()
print(f"Binary size: {len(binary_data)} bytes")

# Test round-trip
point2 = pm.TestPythonPoint.from_bytes(binary_data)
print(f"Round-trip: x={point2.x}, y={point2.y}")

print("SUCCESS: All tests passed")
""")
            
            # Run the test script
            result = subprocess.run([
                sys.executable, str(test_script)
            ], cwd=temp_dir, capture_output=True, text=True)
            
            assert result.returncode == 0, f"Python script failed: {result.stderr}"
            assert "SUCCESS: All tests passed" in result.stdout

    
    def test_json_conversion_accuracy(self):
        """Test JSON conversion accuracy."""
        schema_content = """
        namespace test.json;
        
        struct JsonTest {
            id: u32;
            value: f32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for filename, content in files.items():
                (temp_path / filename).write_text(content)
            
            test_script = temp_path / "test_json.py"
            test_script.write_text("""
import json
import picomsg_generated as pm

# Create test object
obj = pm.TestJsonJsonTest(id=42, value=3.14)

# Test to_json
json_str = obj.to_json()
print(f"JSON: {json_str}")

# Parse JSON to verify structure
parsed = json.loads(json_str)
assert parsed["id"] == 42
assert abs(parsed["value"] - 3.14) < 0.01

# Test from_json
obj2 = pm.TestJsonJsonTest.from_json(json_str)
assert obj2.id == 42
assert abs(obj2.value - 3.14) < 0.01

# Test pretty printing
pretty_json = obj.to_json(indent=2)
assert "\\n" in pretty_json  # Should have newlines

print("SUCCESS: JSON conversion works correctly")
""")
            
            result = subprocess.run([
                sys.executable, str(test_script)
            ], cwd=temp_dir, capture_output=True, text=True)
            
            assert result.returncode == 0, f"JSON test failed: {result.stderr}"
            assert "SUCCESS: JSON conversion works correctly" in result.stdout
    
    def test_binary_format_consistency(self):
        """Test that binary format is consistent."""
        schema_content = """
        namespace test.binary;
        
        struct BinaryTest {
            a: u32;
            b: f32;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for filename, content in files.items():
                (temp_path / filename).write_text(content)
            
            test_script = temp_path / "test_binary.py"
            test_script.write_text("""
import struct
import picomsg_generated as pm

# Create test object
obj = pm.TestBinaryBinaryTest(a=0x12345678, b=3.14)

# Get binary data
binary_data = obj.to_bytes()
print(f"Binary data: {binary_data.hex()}")

# Verify binary format (little-endian)
# u32: 0x12345678 -> 78 56 34 12
# f32: 3.14 -> approximately 40 48 f5 c3
expected_u32 = struct.pack('<I', 0x12345678)
expected_f32 = struct.pack('<f', 3.14)

assert binary_data[:4] == expected_u32, f"u32 mismatch: {binary_data[:4].hex()} != {expected_u32.hex()}"
assert binary_data[4:8] == expected_f32, f"f32 mismatch: {binary_data[4:8].hex()} != {expected_f32.hex()}"

# Test round-trip
obj2 = pm.TestBinaryBinaryTest.from_bytes(binary_data)
assert obj2.a == 0x12345678
assert abs(obj2.b - 3.14) < 0.001

print("SUCCESS: Binary format is consistent")
""")
            
            result = subprocess.run([
                sys.executable, str(test_script)
            ], cwd=temp_dir, capture_output=True, text=True)
            
            assert result.returncode == 0, f"Binary test failed: {result.stderr}"
            assert "SUCCESS: Binary format is consistent" in result.stdout



    
    def test_namespace_isolation(self):
        """Test that namespaces properly isolate generated code."""
        schema_content = """
        namespace api.v1;
        
        struct Header {
            type: u8;
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_content)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for filename, content in files.items():
                (temp_path / filename).write_text(content)
            
            test_script = temp_path / "test_namespace.py"
            test_script.write_text("""
import picomsg_generated as pm

# Test that namespace prefixes are applied
assert hasattr(pm, 'ApiV1Header'), "ApiV1Header class should exist"
assert hasattr(pm, 'ApiV1Error'), "ApiV1Error class should exist"
assert hasattr(pm, 'ApiV1Base'), "ApiV1Base class should exist"

# Test constants have namespace prefixes
assert hasattr(pm, 'APIV1_MAGIC_BYTE_1'), "APIV1_MAGIC_BYTE_1 should exist"
assert pm.APIV1_MAGIC_BYTE_1 == 0xAB

# Test that classes work
header = pm.ApiV1Header(type=42)
assert header.type == 42

print("SUCCESS: Namespace isolation works correctly")
""")
            
            result = subprocess.run([
                sys.executable, str(test_script)
            ], cwd=temp_dir, capture_output=True, text=True)
            
            assert result.returncode == 0, f"Namespace test failed: {result.stderr}"
            assert "SUCCESS: Namespace isolation works correctly" in result.stdout 
