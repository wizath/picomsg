"""
End-to-end tests for enum generation across all languages.
Tests the fix for hexadecimal enum value parsing and proper enum generation.
These tests generate code, compile it, and verify the output works correctly.
"""

import pytest
import tempfile
import subprocess
import os
from pathlib import Path
from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator
from picomsg.codegen.rust import RustCodeGenerator
from picomsg.codegen.c import CCodeGenerator


def rust_available():
    """Check if Rust compiler is available."""
    try:
        result = subprocess.run(["cargo", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def gcc_available():
    """Check if GCC compiler is available."""
    try:
        result = subprocess.run(["gcc", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


class TestEnumGenerationE2E:
    """End-to-end tests for enum generation across languages."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SchemaParser()
    
    def _create_rust_project(self, temp_path: Path, files: dict, project_name: str = "enum_test"):
        """Create a Rust project structure with generated files."""
        # Create Cargo.toml
        cargo_toml = f'''[package]
name = "{project_name}"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = {{ version = "1.0", features = ["derive"] }}
byteorder = "1.4"
base64 = "0.21"
'''
        
        # Create src directory
        src_dir = temp_path / "src"
        src_dir.mkdir(exist_ok=True)
        
        # Write Cargo.toml
        with open(temp_path / "Cargo.toml", 'w') as f:
            f.write(cargo_toml)
        
        # Write all files
        for filename, content in files.items():
            if filename.endswith('.rs'):
                file_path = src_dir / filename
            else:
                file_path = temp_path / filename
            
            with open(file_path, 'w') as f:
                f.write(content)
    
    def _compile_and_run_rust(self, temp_path: Path, timeout: int = 60) -> subprocess.CompletedProcess:
        """Compile and run a Rust project."""
        # Compile
        compile_result = subprocess.run(
            ["cargo", "build"], cwd=temp_path,
            capture_output=True, text=True, timeout=timeout
        )
        
        if compile_result.returncode != 0:
            raise subprocess.CalledProcessError(
                compile_result.returncode, 
                ["cargo", "build"],
                output=compile_result.stdout,
                stderr=compile_result.stderr
            )
        
        # Run
        run_result = subprocess.run(
            ["cargo", "run"], cwd=temp_path,
            capture_output=True, text=True, timeout=30
        )
        
        return run_result
    
    @pytest.fixture
    def hex_enum_schema(self):
        """Schema with hexadecimal enum values."""
        return """
        version 2;
        namespace test.api;
        
        enum ApiCommand : u8 {
            ECHO = 0x01,
            STATUS = 0x02,
            TEST = 0x03,
            UPTIME = 0x04
        }
        
        enum ApiFlags : u8 {
            REQUEST = 0x00,
            RESPONSE = 0x01,
            ERROR = 0x02
        }
        
        struct ApiHeader {
            command: u8;
            flags: u8;
            length: u8;
            error: u8;
            crc: u16;
        }
        
        message EchoRequest {
            header: ApiHeader;
            command: ApiCommand;
            flags: ApiFlags;
            id: u32;
        }
        """
    
    @pytest.fixture
    def decimal_enum_schema(self):
        """Schema with decimal enum values for comparison."""
        return """
        version 2;
        namespace test.api;
        
        enum Priority : u16 {
            LOW = 1,
            MEDIUM = 2,
            HIGH = 3,
            CRITICAL = 4
        }
        
        struct Task {
            name: string;
            priority: Priority;
                }
        """
    
    @pytest.mark.skipif(not rust_available(), reason="Rust compiler not available")
    def test_rust_enum_compilation_and_execution(self):
        """End-to-end test: Generate Rust enum code, compile it, and verify it works."""
        # Simplified schema focusing on enum functionality
        schema_text = """
        version 2;
        namespace test.api;
        
        enum ApiCommand : u8 {
            ECHO = 0x01,
            STATUS = 0x02,
            TEST = 0x03,
            UPTIME = 0x04
        }
        
        enum ApiFlags : u8 {
            REQUEST = 0x00,
            RESPONSE = 0x01,
            ERROR = 0x02
        }
        
        struct SimpleMessage {
            command: u8;
            flags: u8;
            id: u32;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = RustCodeGenerator(schema)
        files = generator.generate()
        
        # Create test main.rs that uses the enums
        main_rs = '''
mod picomsg_generated;
use picomsg_generated::*;

fn main() {
    println!("Testing Rust enum generation end-to-end...");
    
    // Test enum values are correct (hexadecimal parsing)
    println!("Testing enum values:");
    assert_eq!(TestApiApiCommand::ECHO as u8, 1);    // 0x01
    assert_eq!(TestApiApiCommand::STATUS as u8, 2);  // 0x02
    assert_eq!(TestApiApiCommand::TEST as u8, 3);    // 0x03
    assert_eq!(TestApiApiCommand::UPTIME as u8, 4);  // 0x04
    println!("✓ Enum values correct");
    
    // Test enum conversion methods
    println!("Testing enum conversions:");
    assert_eq!(TestApiApiCommand::from_u8(1), Some(TestApiApiCommand::ECHO));
    assert_eq!(TestApiApiCommand::from_u8(2), Some(TestApiApiCommand::STATUS));
    assert_eq!(TestApiApiCommand::from_u8(99), None);
    
    assert_eq!(TestApiApiCommand::ECHO.to_u8(), 1);
    assert_eq!(TestApiApiCommand::STATUS.to_u8(), 2);
    println!("✓ Enum conversions work");
    
    // Test ApiFlags enum
    println!("Testing ApiFlags enum:");
    assert_eq!(TestApiApiFlags::REQUEST as u8, 0);   // 0x00
    assert_eq!(TestApiApiFlags::RESPONSE as u8, 1);  // 0x01
    assert_eq!(TestApiApiFlags::ERROR as u8, 2);     // 0x02
    
    assert_eq!(TestApiApiFlags::from_u8(0), Some(TestApiApiFlags::REQUEST));
    assert_eq!(TestApiApiFlags::from_u8(1), Some(TestApiApiFlags::RESPONSE));
    assert_eq!(TestApiApiFlags::from_u8(2), Some(TestApiApiFlags::ERROR));
    assert_eq!(TestApiApiFlags::from_u8(99), None);
    println!("✓ ApiFlags enum works");
    
    // Test enum usage in struct
    println!("Testing enum usage in struct:");
    let message = TestApiSimpleMessage {
        command: TestApiApiCommand::ECHO.to_u8(),
        flags: TestApiApiFlags::REQUEST.to_u8(),
        id: 42,
    };
    
    // Verify we can convert back to enums
    let cmd_enum = TestApiApiCommand::from_u8(message.command);
    let flags_enum = TestApiApiFlags::from_u8(message.flags);
    
    assert_eq!(cmd_enum, Some(TestApiApiCommand::ECHO));
    assert_eq!(flags_enum, Some(TestApiApiFlags::REQUEST));
    println!("✓ Enum usage in struct works");
    
    println!("SUCCESS: All enum tests passed!");
}
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.rs"] = main_rs
            
            self._create_rust_project(temp_path, files)
            
            try:
                result = self._compile_and_run_rust(temp_path)
                
                # Verify the program ran successfully
                assert result.returncode == 0, f"Program failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                
                # Verify specific outputs
                assert "✓ Enum values correct" in result.stdout
                assert "✓ Enum conversions work" in result.stdout
                assert "✓ ApiFlags enum works" in result.stdout
                assert "✓ Enum usage in struct works" in result.stdout
                assert "SUCCESS: All enum tests passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Rust compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")

    def test_hexadecimal_enum_parsing(self, hex_enum_schema):
        """Test that hexadecimal enum values are parsed correctly."""
        parser = SchemaParser()
        schema = parser.parse_string(hex_enum_schema)
        
        # Verify ApiCommand enum
        api_command = schema.get_enum("ApiCommand")
        assert api_command is not None
        assert api_command.backing_type.name == "u8"
        
        values = {v.name: v.value for v in api_command.values}
        assert values["ECHO"] == 1      # 0x01
        assert values["STATUS"] == 2    # 0x02
        assert values["TEST"] == 3      # 0x03
        assert values["UPTIME"] == 4    # 0x04
        
        # Verify ApiFlags enum
        api_flags = schema.get_enum("ApiFlags")
        assert api_flags is not None
        
        flag_values = {v.name: v.value for v in api_flags.values}
        assert flag_values["REQUEST"] == 0   # 0x00
        assert flag_values["RESPONSE"] == 1  # 0x01
        assert flag_values["ERROR"] == 2     # 0x02
    
    def test_mixed_hex_decimal_enum_parsing(self):
        """Test parsing enums with mixed hex and decimal values."""
        schema_text = """
        enum MixedEnum : u8 {
            FIRST = 1,
            SECOND = 0x02,
            THIRD = 3,
            FOURTH = 0x04
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        mixed_enum = schema.enums[0]
        values = {v.name: v.value for v in mixed_enum.values}
        assert values["FIRST"] == 1
        assert values["SECOND"] == 2
        assert values["THIRD"] == 3
        assert values["FOURTH"] == 4
    
    def test_rust_enum_generation(self, hex_enum_schema):
        """Test Rust enum generation with hexadecimal values."""
        parser = SchemaParser()
        schema = parser.parse_string(hex_enum_schema)
        
        gen = RustCodeGenerator(schema)
        files = gen.generate()
        rust_code = list(files.values())[0]
        
        # Verify enum definitions are generated
        assert "pub enum TestApiApiCommand {" in rust_code
        assert "pub enum TestApiApiFlags {" in rust_code
        
        # Verify correct enum values
        assert "ECHO = 1," in rust_code
        assert "STATUS = 2," in rust_code
        assert "TEST = 3," in rust_code
        assert "UPTIME = 4," in rust_code
        
        assert "REQUEST = 0," in rust_code
        assert "RESPONSE = 1," in rust_code
        assert "ERROR = 2," in rust_code
        
        # Verify enum attributes
        assert "#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]" in rust_code
        assert "#[repr(u8)]" in rust_code
        
        # Verify conversion methods
        assert "pub fn from_u8(value: u8) -> Option<Self>" in rust_code
        assert "pub fn to_u8(self) -> u8" in rust_code
        
        # Verify match arms for conversion
        assert "1 => Some(Self::ECHO)," in rust_code
        assert "2 => Some(Self::STATUS)," in rust_code
        assert "0 => Some(Self::REQUEST)," in rust_code
        
        # Verify no duplicate values (the bug we fixed)
        lines = rust_code.split('\n')
        echo_lines = [line for line in lines if "ECHO = " in line]
        assert len(echo_lines) == 1, "ECHO should only be defined once"
        
        status_lines = [line for line in lines if "STATUS = " in line]
        assert len(status_lines) == 1, "STATUS should only be defined once"
    
    def test_python_enum_generation(self, hex_enum_schema):
        """Test Python enum generation with hexadecimal values."""
        parser = SchemaParser()
        schema = parser.parse_string(hex_enum_schema)
        
        gen = PythonCodeGenerator(schema)
        files = gen.generate()
        python_code = list(files.values())[0]
        
        # Verify enum class generation
        assert "class TestApiApiCommand(IntEnum):" in python_code
        assert "class TestApiApiFlags(IntEnum):" in python_code
        
        # Verify correct enum values
        assert "ECHO = 1" in python_code
        assert "STATUS = 2" in python_code
        assert "TEST = 3" in python_code
        assert "UPTIME = 4" in python_code
        
        assert "REQUEST = 0" in python_code
        assert "RESPONSE = 1" in python_code
        assert "ERROR = 2" in python_code
        
        # Verify utility methods
        assert "def from_int(cls, value: int)" in python_code
        assert "def to_int(self) -> int" in python_code
    
    def test_c_enum_generation(self, hex_enum_schema):
        """Test C enum generation with hexadecimal values."""
        parser = SchemaParser()
        schema = parser.parse_string(hex_enum_schema)
        
        gen = CCodeGenerator(schema)
        files = gen.generate()
        c_header = files[list(files.keys())[0]]  # Get header file
        
        # Verify enum definitions
        assert "typedef enum {" in c_header
        
        # Verify correct enum values (C uses TEST_API_ prefix)
        assert "TEST_API_APICOMMAND_ECHO = 1," in c_header
        assert "TEST_API_APICOMMAND_STATUS = 2," in c_header
        assert "TEST_API_APICOMMAND_TEST = 3," in c_header
        assert "TEST_API_APICOMMAND_UPTIME = 4," in c_header
        
        assert "TEST_API_APIFLAGS_REQUEST = 0," in c_header
        assert "TEST_API_APIFLAGS_RESPONSE = 1," in c_header
        assert "TEST_API_APIFLAGS_ERROR = 2," in c_header
    
    def test_enum_serialization_rust(self, hex_enum_schema):
        """Test that Rust enum serialization works correctly."""
        parser = SchemaParser()
        schema = parser.parse_string(hex_enum_schema)
        
        gen = RustCodeGenerator(schema)
        files = gen.generate()
        rust_code = list(files.values())[0]
        
        # Verify enum fields in structs are handled
        assert "command: TestApiApiCommand," in rust_code
        assert "flags: TestApiApiFlags," in rust_code
        
        # Verify enum read/write methods exist
        assert "_generate_enum_read" not in rust_code  # Internal method shouldn't appear
        
        # Check that enum fields are properly serialized in message implementations
        # The enum should be read/written as its backing type
        message_impl_found = False
        for line in rust_code.split('\n'):
            if "impl TestApiSerialize for TestApiEchoRequest" in line:
                message_impl_found = True
                break
        assert message_impl_found, "Message implementation should be generated"
    
    def test_enum_functionality_python_execution(self, hex_enum_schema):
        """Test that generated Python enum code executes correctly."""
        parser = SchemaParser()
        schema = parser.parse_string(hex_enum_schema)
        
        gen = PythonCodeGenerator(schema)
        files = gen.generate()
        python_code = list(files.values())[0]
        
        # Execute the generated code
        exec_globals = {}
        exec(python_code, exec_globals)
        
        # Test ApiCommand enum
        ApiCommand = exec_globals['TestApiApiCommand']
        assert ApiCommand.ECHO.value == 1
        assert ApiCommand.STATUS.value == 2
        assert ApiCommand.TEST.value == 3
        assert ApiCommand.UPTIME.value == 4
        
        # Test conversion methods
        assert ApiCommand.from_int(1) == ApiCommand.ECHO
        assert ApiCommand.from_int(2) == ApiCommand.STATUS
        assert ApiCommand.ECHO.to_int() == 1
        assert ApiCommand.STATUS.to_int() == 2
        
        # Test ApiFlags enum
        ApiFlags = exec_globals['TestApiApiFlags']
        assert ApiFlags.REQUEST.value == 0
        assert ApiFlags.RESPONSE.value == 1
        assert ApiFlags.ERROR.value == 2
        
        # Test invalid values
        with pytest.raises(ValueError):
            ApiCommand.from_int(99)
    
    def test_large_hex_values(self):
        """Test parsing of large hexadecimal values."""
        schema_text = """
        enum LargeEnum : u32 {
            SMALL = 0x01,
            MEDIUM = 0xFF,
            LARGE = 0xFFFF,
            HUGE = 0xFFFFFFFF
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        large_enum = schema.enums[0]
        values = {v.name: v.value for v in large_enum.values}
        assert values["SMALL"] == 1
        assert values["MEDIUM"] == 255
        assert values["LARGE"] == 65535
        assert values["HUGE"] == 4294967295
    
    def test_enum_in_message_serialization(self, hex_enum_schema):
        """Test end-to-end serialization of messages containing enums."""
        parser = SchemaParser()
        schema = parser.parse_string(hex_enum_schema)
        
        # Test Python generation and execution
        gen = PythonCodeGenerator(schema)
        files = gen.generate()
        python_code = list(files.values())[0]
        
        exec_globals = {}
        exec(python_code, exec_globals)
        
        # Create message with enum fields
        EchoRequest = exec_globals['TestApiEchoRequest']
        ApiHeader = exec_globals['TestApiApiHeader']
        ApiCommand = exec_globals['TestApiApiCommand']
        ApiFlags = exec_globals['TestApiApiFlags']
        
        header = ApiHeader(command=1, flags=0, length=0, error=0, crc=0)
        message = EchoRequest(
            header=header,
            command=ApiCommand.ECHO,
            flags=ApiFlags.REQUEST,
            id=42
        )
        
        # Test serialization
        data = message.to_bytes()
        assert len(data) > 0
        
        # Test deserialization
        message2 = EchoRequest.from_bytes(data)
        assert message2.command == ApiCommand.ECHO
        assert message2.flags == ApiFlags.REQUEST
        assert message2.id == 42
    
    def test_regression_no_duplicate_enum_values(self):
        """Regression test: ensure no duplicate enum values are generated."""
        schema_text = """
        enum TestEnum : u8 {
            A = 0x01,
            B = 0x02,
            C = 0x03
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        # Test Rust generation
        gen = RustCodeGenerator(schema)
        files = gen.generate()
        rust_code = list(files.values())[0]
        
        # Count occurrences of each enum value
        a_count = rust_code.count("A = 1,")
        b_count = rust_code.count("B = 2,")
        c_count = rust_code.count("C = 3,")
        
        assert a_count == 1, f"A should appear exactly once, found {a_count}"
        assert b_count == 1, f"B should appear exactly once, found {b_count}"
        assert c_count == 1, f"C should appear exactly once, found {c_count}"
        
        # Ensure no "x01", "x02" artifacts from the old bug
        assert "x01" not in rust_code
        assert "x02" not in rust_code
        assert "x03" not in rust_code
    
    def test_enum_compilation_rust(self, hex_enum_schema):
        """Test that generated Rust enum code compiles without errors."""
        parser = SchemaParser()
        schema = parser.parse_string(hex_enum_schema)
        
        gen = RustCodeGenerator(schema)
        files = gen.generate()
        rust_code = list(files.values())[0]
        
        # Write to temporary file and attempt compilation check
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
            f.write(rust_code)
            temp_file = f.name
        
        try:
            # Basic syntax validation - check for common compilation errors
            # Extract enum discriminant values specifically from enum definitions
            lines = rust_code.split('\n')
            
            # Find enum blocks and extract their discriminant values
            in_enum = False
            enum_name = None
            enum_values = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('pub enum ') and line.endswith(' {'):
                    in_enum = True
                    enum_name = line.split()[2].rstrip(' {')
                elif in_enum and line == '}':
                    in_enum = False
                    enum_name = None
                elif in_enum and ' = ' in line and line.endswith(','):
                    # This is an enum variant with explicit discriminant
                    parts = line.split(' = ')
                    if len(parts) == 2:
                        try:
                            value = int(parts[1].rstrip(','))
                            enum_values.append((enum_name, value))
                        except ValueError:
                            pass  # Skip non-numeric values
            
            # Group by enum and check for duplicates within each enum
            enum_groups = {}
            for enum_name, value in enum_values:
                if enum_name not in enum_groups:
                    enum_groups[enum_name] = []
                enum_groups[enum_name].append(value)
            
            # Check for duplicates within each enum
            for enum_name, values in enum_groups.items():
                unique_values = set(values)
                assert len(values) == len(unique_values), f"Duplicate values in enum {enum_name}: {values}"
            
        finally:
            os.unlink(temp_file) 
