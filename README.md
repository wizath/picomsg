# PicoMsg

Lightweight binary serialization format for embedded and performance-critical applications.

## Overview

PicoMsg is a binary serialization format optimized for embedded systems and performance-critical applications. It provides efficient C struct operations while offering high-level language bindings with comprehensive JSON integration and validation.

## Features

- **Zero-copy deserialization** in C with memory-aligned structures
- **Compact binary format** with minimal overhead and direct `memcpy()` operations
- **Multi-language support** with code generation for C, Rust, Python, and TypeScript
- **Modular schema organization** with include statements for code reuse and maintainability
- **Comprehensive JSON system** with validation, streaming, and pretty-printing
- **Schema definition language** with support for enums, structs, messages, and complex nesting
- **Cross-language JSON interoperability** for debugging and API development
- **Schema-aware JSON validation** with type coercion and detailed error handling
- **Enhanced code generation** with modern framework integration (serde, Pydantic v2)
- **Hexadecimal enum support** for hardware-oriented protocols
- **End-to-end testing** with real compilation and execution verification

## Quick Start

### 1. Install PicoMsg

```bash
pip install picomsg
```

### 2. Define Your Schema

Create a `.pico` schema file (supports include statements for modular organization):

```picomsg
version 2;
namespace api.v1;

enum ApiCommand : u8 {
    ECHO = 0x01,
    STATUS = 0x02,
    SHUTDOWN = 0x03
}

struct ApiHeader {
    command: u8;
    length: u16;
    crc16: u16;
}

message EchoRequest {
    header: ApiHeader;
    data: bytes;
    timestamp: u64;
}
```

### 3. Generate Language Bindings

```bash
# Generate Rust code with JSON validation
picomsg compile schema.pico --lang rust --output generated/

# Generate Python code with Pydantic validation
picomsg compile schema.pico --lang python --output generated/ --module-name api_bindings

# Generate TypeScript code with type safety
picomsg compile schema.pico --lang typescript --output generated/ --module-name api_types

# Generate C code for embedded systems
picomsg compile schema.pico --lang c --output generated/ --header-name api
```

### 4. Use Generated Code

**Python with JSON validation:**
```python
import api_bindings as api

# Create with validation
header = api.ApiHeader(command=1, length=1024, crc16=0xABCD)
request = api.EchoRequest(
    header=header,
    data=b"Hello, World!",
    timestamp=1640995200
)

# Binary serialization
binary_data = request.to_bytes()

# JSON with validation
json_data = request.to_json(indent=2)
validated_request = api.EchoRequest.from_json(json_data)
```

**Rust with serde integration:**
```rust
use generated::*;

// Create and serialize
let header = ApiHeader { command: 1, length: 1024, crc16: 0xABCD };
let request = EchoRequest {
    header,
    data: b"Hello, World!".to_vec(),
    timestamp: 1640995200,
};

// Binary format
let binary_data = request.to_bytes()?;

// JSON with validation
let json_data = serde_json::to_string(&request)?;
let validated_request: EchoRequest = serde_json::from_str(&json_data)?;
```

**TypeScript with full type safety:**
```typescript
import { ApiHeader, EchoRequest, ApiCommand } from './api_types';

// Create with type-safe constructors
const header = new ApiHeader({
    command: ApiCommand.ECHO,
    length: 1024,
    crc16: 0xABCD
});

const request = new EchoRequest({
    header: header,
    data: new TextEncoder().encode("Hello, World!"),
    timestamp: 1640995200
});

// Binary serialization
const binaryData = request.toBytes();

// JSON serialization
const jsonData = request.toJSON();
const restoredRequest = EchoRequest.fromJSON(jsonData);

// Base64 encoding
const base64Data = request.toBase64();
const fromBase64 = EchoRequest.fromBase64(base64Data);
```

## CLI Tutorial

PicoMsg provides a comprehensive command-line interface for schema compilation, validation, and JSON operations.

### Basic Commands

#### Schema Compilation

Compile schema files to target language bindings:

```bash
# Basic compilation
picomsg compile schema.pico --lang python --output generated/

# With custom module name
picomsg compile schema.pico --lang rust --output src/ --module-name protocol

# TypeScript with npm package generation
picomsg compile schema.pico --lang typescript --output frontend/types/ --module-name api-client

# C code generation with custom header name
picomsg compile schema.pico --lang c --output include/ --header-name device_api

# Generate only struct definitions (C only)
picomsg compile schema.pico --lang c --output include/ --structs-only
```

#### Schema Validation

Validate schema files for syntax and semantic errors:

```bash
# Validate a single schema
picomsg validate schema.pico

# Validate multiple schemas
picomsg validate *.pico
```

#### Schema Information

Get detailed information about schema contents:

```bash
# Show schema structure and statistics
picomsg info schema.pico

# Display all types and their relationships
picomsg info schema.pico --verbose
```

### JSON Operations

#### JSON Code Generation

Generate enhanced code with JSON validation:

```bash
# Python with Pydantic validation
picomsg json codegen schema.pico --lang python --output api/

# Rust with serde validation
picomsg json codegen schema.pico --lang rust --output src/

# TypeScript with type safety and npm package
picomsg json codegen schema.pico --lang typescript --output frontend/api/
```

#### JSON Validation

Validate JSON data against schema definitions:

```bash
# Validate JSON file
picomsg json validate schema.pico data.json

# Validate JSON from stdin
echo '{"command": 1, "data": "test"}' | picomsg json validate schema.pico -

# Validate with detailed error reporting
picomsg json validate schema.pico data.json --verbose
```

#### JSON Conversion

Convert between different JSON formats:

```bash
# Convert JSON array to line-delimited JSON
picomsg json convert array-to-lines data.json output.jsonl

# Convert line-delimited JSON to array
picomsg json convert lines-to-array data.jsonl output.json

# Pretty-print with schema annotations
picomsg json pretty schema.pico data.json --annotate
```

#### JSON Schema Information

Get information about JSON schema mappings:

```bash
# Show JSON schema for all types
picomsg json info schema.pico

# Show schema for specific message type
picomsg json info schema.pico --type EchoRequest
```

### Advanced Usage

#### Multi-file Compilation

Compile multiple related schema files:

```bash
# Compile all schemas in directory
picomsg compile *.pico --lang rust --output generated/

# Compile with namespace preservation
picomsg compile api/*.pico --lang python --output api_bindings/
```

#### Custom Output Organization

Organize generated code with custom naming:

```bash
# Rust with custom module structure
picomsg compile protocol.pico --lang rust --output src/protocol/ --module-name messages

# Python with package structure
picomsg compile api.pico --lang python --output myapi/ --module-name core
```

#### Integration with Build Systems

Use PicoMsg in automated build processes:

```bash
# Makefile integration
generate-api:
	picomsg compile api.pico --lang rust --output src/generated/
	picomsg compile api.pico --lang python --output python/api/

# CI/CD pipeline
picomsg validate schemas/*.pico
picomsg compile schemas/api.pico --lang rust --output target/generated/
```

## Schema Reference

PicoMsg schemas use a simple, readable syntax for defining binary message formats.

### Schema Structure

Every schema file must start with a version declaration and namespace:

```picomsg
version 2;
namespace com.example.api;
```

### Include Statements

Organize large schemas across multiple files using include statements:

```picomsg
// shared_types.pico
struct Point {
    x: f32;
    y: f32;
}

enum Color : u8 {
    RED = 1,
    GREEN = 2,
    BLUE = 3
}
```

```picomsg
// main.pico
include "shared_types.pico";

version 2;
namespace com.example.api;

message DrawCommand {
    position: Point;  // From shared_types.pico
    color: Color;     // From shared_types.pico
    size: f32;
}
```

#### Include Features

- **Recursive includes**: Files can include other files that also have includes
- **Path resolution**: Relative paths resolved relative to the including file
- **Namespace preservation**: Main file's namespace takes precedence
- **Conflict detection**: Prevents naming conflicts with clear error messages
- **Circular dependency detection**: Prevents infinite include loops

#### Usage with CLI

Pass the main schema file to any CLI command - includes are resolved automatically:

```bash
# Validates main.pico and all included files
picomsg validate main.pico

# Generates code from merged schema
picomsg compile main.pico --lang python --output generated/
```

### Data Types

#### Primitive Types

| Type | Size | Range | Description |
|------|------|-------|-------------|
| `u8` | 1 byte | 0 to 255 | Unsigned 8-bit integer |
| `u16` | 2 bytes | 0 to 65,535 | Unsigned 16-bit integer |
| `u32` | 4 bytes | 0 to 4,294,967,295 | Unsigned 32-bit integer |
| `u64` | 8 bytes | 0 to 18,446,744,073,709,551,615 | Unsigned 64-bit integer |
| `i8` | 1 byte | -128 to 127 | Signed 8-bit integer |
| `i16` | 2 bytes | -32,768 to 32,767 | Signed 16-bit integer |
| `i32` | 4 bytes | -2,147,483,648 to 2,147,483,647 | Signed 32-bit integer |
| `i64` | 8 bytes | -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807 | Signed 64-bit integer |
| `f32` | 4 bytes | IEEE 754 single precision | 32-bit floating point |
| `f64` | 8 bytes | IEEE 754 double precision | 64-bit floating point |
| `bool` | 1 byte | true or false | Boolean value |

#### Variable-Length Types

| Type | Format | Description |
|------|--------|-------------|
| `string` | `u16` length + UTF-8 bytes | Variable-length UTF-8 string |
| `bytes` | `u16` length + raw bytes | Variable-length byte array |
| `[Type]` | `u16` count + elements | Variable-length array of any type |
| `[Type:N]` | N elements | Fixed-length array of N elements |

### Enums

Define enumerated values with explicit or automatic numbering:

```picomsg
// Basic enum with automatic numbering (0, 1, 2...)
enum Status : u8 {
    IDLE,
    RUNNING,
    ERROR
}

// Enum with explicit values (supports hexadecimal)
enum Command : u8 {
    RESET = 0x00,
    START = 0x01,
    STOP = 0x02,
    STATUS = 0x10
}

// Enum with mixed numbering
enum Priority : u16 {
    LOW,           // 0
    MEDIUM = 100,  // 100
    HIGH,          // 101
    CRITICAL = 1000 // 1000
}
```

**Backing Types:** Enums can use any integer type (`u8`, `u16`, `u32`, `u64`, `i8`, `i16`, `i32`, `i64`).

### Structs

Define composite data structures:

```picomsg
struct Point {
    x: f32;
    y: f32;
}

struct Rectangle {
    top_left: Point;
    bottom_right: Point;
    color: u32;
}

// Struct with arrays and optional fields
struct Polygon {
    vertices: [Point];
    colors: [u32];
    metadata: string;
}
```

### Messages

Top-level message definitions (similar to structs but used for protocol messages):

```picomsg
message DrawCommand {
    shape: Rectangle;
    timestamp: u64;
    user_id: u32;
}

message BatchDrawCommand {
    commands: [DrawCommand];
    batch_id: u64;
}
```

### Default Values

Specify default values for struct and message fields:

```picomsg
struct Configuration {
    timeout: u32 = 5000;
    retries: u8 = 3;
    debug: bool = false;
    name: string = "default";
}

message Request {
    header: ApiHeader;
    priority: Priority = MEDIUM;
    data: bytes;
}
```

**Supported Default Types:**
- Integers: `field: u32 = 42`
- Floats: `field: f64 = 3.14159`
- Booleans: `field: bool = true`
- Strings: `field: string = "default value"`
- Enums: `field: Status = IDLE`

### Complex Nesting

PicoMsg supports arbitrary nesting of data structures:

```picomsg
// Multi-dimensional arrays
struct Matrix {
    data: [[f64]];
    dimensions: [u32];
}

// Nested structures with arrays
struct Scene {
    objects: [GameObject];
    lights: [Light];
    camera: Camera;
}

struct GameObject {
    id: u32;
    position: Point;
    components: [Component];
}

struct Component {
    type: ComponentType;
    data: bytes;
    properties: [Property];
}

struct Property {
    key: string;
    value: string;
}
```

### Comments

Use C-style comments for documentation:

```picomsg
// Single-line comment
enum Status : u8 {
    IDLE,    // System is idle
    RUNNING, // System is processing
    ERROR    // System encountered an error
}

/*
 * Multi-line comment
 * for detailed documentation
 */
struct ApiHeader {
    command: u8;   // Command identifier
    length: u16;   // Payload length
    crc16: u16;    // Checksum
}
```

### Naming Conventions

**Recommended naming patterns:**
- **Namespaces:** `com.company.product` or `product.module`
- **Types:** `PascalCase` (e.g., `ApiHeader`, `DrawCommand`)
- **Fields:** `snake_case` (e.g., `user_id`, `timestamp`)
- **Enums:** `UPPER_CASE` values (e.g., `RUNNING`, `ERROR`)

### Schema Validation Rules

PicoMsg enforces several validation rules:

1. **Version declaration** must be first non-comment line
2. **Namespace declaration** must follow version
3. **Type names** must be unique within namespace
4. **Field names** must be unique within struct/message
5. **Enum values** must be unique within enum
6. **Circular references** are not allowed
7. **Array dimensions** must be positive integers
8. **Default values** must match field types

### Binary Format Details

**Encoding:**
- All multi-byte values use little-endian encoding
- Structs are packed with 4-byte alignment
- Strings are UTF-8 encoded with `u16` length prefix
- Arrays have `u16` count prefix followed by elements
- Booleans are stored as single bytes (0 = false, 1 = true)

**Memory Layout:**
```
Message Header: [magic_bytes(2)] [version(1)] [type_id(1)] [length(4)]
Payload: [struct_data...]
```

### Language-Specific Mappings

| PicoMsg | C | Rust | Python | TypeScript |
|---------|---|------|--------|------------|
| `u8` | `uint8_t` | `u8` | `int` | `number` |
| `u16` | `uint16_t` | `u16` | `int` | `number` |
| `u32` | `uint32_t` | `u32` | `int` | `number` |
| `u64` | `uint64_t` | `u64` | `int` | `number` |
| `i8` | `int8_t` | `i8` | `int` | `number` |
| `i16` | `int16_t` | `i16` | `int` | `number` |
| `i32` | `int32_t` | `i32` | `int` | `number` |
| `i64` | `int64_t` | `i64` | `int` | `number` |
| `f32` | `float` | `f32` | `float` | `number` |
| `f64` | `double` | `f64` | `float` | `number` |
| `bool` | `bool` | `bool` | `bool` | `boolean` |
| `string` | `char*` | `String` | `str` | `string` |
| `bytes` | `uint8_t*` | `Vec<u8>` | `bytes` | `Uint8Array` |
| `[Type]` | `Type*` | `Vec<Type>` | `List[Type]` | `Type[]` |
| `[Type:N]` | `Type[N]` | `[Type; N]` | `List[Type]` | `Type[]` |
| Enum | `enum_name_t` | `EnumName` | `EnumName` | `EnumName` |
| Struct | `struct_name_t` | `StructName` | `StructName` | `StructName` |

### Language-Specific Features

| Feature | C | Rust | Python | TypeScript |
|---------|---|------|--------|------------|
| **JSON Support** | ❌ | ✅ (serde) | ✅ (Pydantic) | ✅ (native) |
| **Base64 Encoding** | ❌ | ✅ | ✅ | ✅ |
| **Type Safety** | ⚠️ (compile-time) | ✅ (strict) | ⚠️ (runtime) | ✅ (strict) |
| **Memory Management** | Manual | Automatic | Automatic | Automatic |
| **Package Generation** | Headers only | Cargo crate | Python package | npm package |
| **Static Factory Methods** | ❌ | ✅ | ✅ | ✅ |
| **Validation** | ❌ | ✅ (validator) | ✅ (Pydantic) | ✅ (TypeScript) |

## JSON Integration

PicoMsg provides comprehensive JSON support with validation and framework integration.

### JSON Validation Features

**Rust Integration:**
- Full `serde` + `validator` crate support
- Automatic range validation for integer types
- Finite float validation (prevents NaN/infinity)
- Custom validation functions for complex types

**Python Integration:**
- Pydantic v2 compatibility with modern validators
- Constrained types (`conint`, `confloat`, `constr`)
- Strict validation with assignment checking
- Comprehensive error reporting

**TypeScript Integration:**
- Native JSON serialization with type safety
- Static factory methods (`fromJSON`, `fromBytes`, `fromBase64`)
- Full TypeScript type definitions and IntelliSense support
- Runtime type validation with detailed error messages
- npm package generation with proper dependencies

### JSON Code Generation

Generate enhanced code with JSON validation:

```bash
# Python with Pydantic validation
picomsg json codegen schema.pico --lang python --output api/

# Rust with serde validation
picomsg json codegen schema.pico --lang rust --output src/

# TypeScript with type safety and npm package
picomsg json codegen schema.pico --lang typescript --output frontend/api/
```

### JSON Validation Examples

**Python with Pydantic:**
```python
from pydantic import ValidationError
import api_bindings as api

try:
    # This will validate ranges automatically
    header = api.ApiHeader(command=1, length=1024, crc16=65535)
    
    # This will raise ValidationError (command > 255)
    invalid_header = api.ApiHeader(command=300, length=1024, crc16=0)
except ValidationError as e:
    print(f"Validation error: {e}")
```

**Rust with serde + validator:**
```rust
use serde_json;
use validator::Validate;

// Automatic validation on deserialization
let json_data = r#"{"command": 1, "length": 1024, "crc16": 65535}"#;
let header: ApiHeader = serde_json::from_str(json_data)?;

// Manual validation
header.validate()?;
```

**TypeScript with type safety:**
```typescript
import { ApiHeader, ApiCommand } from './api_types';

try {
    // Type-safe construction with validation
    const header = new ApiHeader({
        command: ApiCommand.ECHO,
        length: 1024,
        crc16: 65535
    });
    
    // JSON serialization with validation
    const jsonData = header.toJSON();
    const restored = ApiHeader.fromJSON(jsonData);
    
    // This would cause TypeScript compilation error
    // const invalid = new ApiHeader({ command: "invalid" });
    
} catch (error) {
    console.error(`Validation error: ${error.message}`);
}
```

### JSON Utilities

**Validation helpers:**
```python
# Validate JSON string
result = api.validate_json_string(json_data, api.ApiHeader)

# Validate dictionary
result = api.validate_dict(data_dict, api.ApiHeader)

# Convert to validated JSON
validated_json = api.to_validated_json(header_instance)
```

**JSON conversion:**
```bash
# Pretty-print with schema information
picomsg json pretty schema.pico data.json --annotate

# Convert between formats
picomsg json convert array-to-lines data.json output.jsonl
```

## Examples

### Complete Protocol Example

```picomsg
version 2;
namespace device.protocol;

enum DeviceCommand : u8 {
    PING = 0x01,
    GET_STATUS = 0x02,
    SET_CONFIG = 0x03,
    RESET = 0xFF
}

enum DeviceStatus : u8 {
    OFFLINE = 0x00,
    ONLINE = 0x01,
    ERROR = 0x02,
    MAINTENANCE = 0x03
}

struct DeviceHeader {
    command: DeviceCommand;
    sequence: u16;
    timestamp: u64;
}

struct DeviceConfig {
    sample_rate: u32 = 1000;
    enable_logging: bool = true;
    device_name: string = "Device";
    channels: [u8];
}

message PingRequest {
    header: DeviceHeader;
}

message PingResponse {
    header: DeviceHeader;
    device_id: u32;
    firmware_version: string;
}

message StatusRequest {
    header: DeviceHeader;
}

message StatusResponse {
    header: DeviceHeader;
    status: DeviceStatus;
    uptime: u64;
    error_count: u32;
}

message ConfigRequest {
    header: DeviceHeader;
    config: DeviceConfig;
}

message ConfigResponse {
    header: DeviceHeader;
    success: bool;
    error_message: string;
}
```

### Usage in Different Languages

**Python:**
```python
import device_protocol as proto

# Create request
header = proto.DeviceHeader(
    command=proto.DeviceCommand.GET_STATUS,
    sequence=1,
    timestamp=1640995200
)
request = proto.StatusRequest(header=header)

# Serialize to binary
binary_data = request.to_bytes()

# JSON with validation
json_data = request.to_json(indent=2)
validated_request = proto.StatusRequest.from_json(json_data)
```

**Rust:**
```rust
use device_protocol::*;

// Create request
let header = DeviceHeader {
    command: DeviceCommand::GetStatus,
    sequence: 1,
    timestamp: 1640995200,
};
let request = StatusRequest { header };

// Serialize to binary
let binary_data = request.to_bytes()?;

// JSON with validation
let json_data = serde_json::to_string(&request)?;
let validated_request: StatusRequest = serde_json::from_str(&json_data)?;
```

**C:**
```c
#include "device_protocol.h"

// Create request
device_protocol_deviceheader_t header = {
    .command = DEVICE_PROTOCOL_DEVICECOMMAND_GET_STATUS,
    .sequence = 1,
    .timestamp = 1640995200
};
device_protocol_statusrequest_t request = { .header = header };

// Serialize to binary
uint8_t buffer[256];
size_t length = sizeof(buffer);
device_protocol_error_t result = device_protocol_statusrequest_to_bytes(
    &request, buffer, &length
);
```

## Performance

PicoMsg is designed for high-performance applications:

- **Zero-copy deserialization** in C
- **Minimal memory allocation** with stack-based operations
- **Efficient binary format** with compact encoding
- **Fast JSON validation** with optimized parsers
- **Batch processing support** for high-throughput scenarios

### Benchmarks

Recent performance testing shows:
- **1000+ message processing** with sub-millisecond latency
- **Cross-language consistency** in serialization performance
- **JSON validation overhead** typically <5% of total processing time
- **Memory efficiency** with minimal heap allocation

## Contributing

Contributions are welcome! Please see our contributing guidelines and ensure all tests pass:

```bash
# Run the full test suite
python -m pytest

# Run end-to-end tests (requires Rust)
python -m pytest tests/end2end/

# Run specific test categories
python -m pytest tests/unittest/
python -m pytest tests/integration/
```

## License

PicoMsg is released under the MIT License. See LICENSE file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed release notes and version history. 
