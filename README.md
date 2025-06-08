# PicoMsg

Lightweight binary serialization format for embedded and performance-critical applications.

## Overview

PicoMsg is a binary serialization format similar to FlatBuffers but optimized for embedded systems and performance-critical applications. It provides efficient C struct operations while offering high-level language bindings.

## Features

- **Zero-copy deserialization** in C
- **Memory aligned** structures for direct `memcpy()` operations
- **Compact binary format** with minimal overhead
- **Multi-language support** (C, Rust, Python, JavaScript)
- **Schema definition language** (.pico files)
- **Comprehensive JSON system** with validation, streaming, and pretty-printing
- **Cross-language JSON interoperability** for debugging and APIs
- **Schema-aware JSON validation** with type coercion and error handling
- **Streaming JSON support** for large datasets and memory efficiency
- **Enhanced code generation** with JSON integration for Rust and Python

## Quick Start

1. Define your schema in a `.pico` file:

```
namespace api.v1;

struct ApiHeader {
    command: u8;
    length: u16;
    crc16: u16;
}

message EchoRequest {
    header: ApiHeader;
    data: bytes;
}
```

2. Generate language bindings:

```bash
picomsg compile schema.pico --lang c --output generated/
picomsg compile schema.pico --lang python --output generated/ --module-name api_bindings
picomsg compile schema.pico --lang rust --output generated/
```

3. Use the generated code in your application:

```python
# Python example with JSON support
import api_bindings as api

# Create and serialize
header = api.ApiHeader(command=42, length=1024, crc16=0xABCD)
binary_data = header.to_bytes()
json_data = header.to_json(indent=2)

# Deserialize
header2 = api.ApiHeader.from_bytes(binary_data)
header3 = api.ApiHeader.from_json(json_data)
```

## Supported Data Types

PicoMsg supports a comprehensive set of data types for building efficient binary protocols:

### Primitive Types

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

### Variable-Length Types

| Type | Format | Description |
|------|--------|-------------|
| `string` | `u16` length + UTF-8 bytes | Variable-length UTF-8 string |
| `bytes` | `u16` length + raw bytes | Variable-length byte array |
| `[Type]` | `u16` count + elements | Variable-length array of any type |

### Custom Types

- **Structs**: User-defined composite types
- **Messages**: Top-level message definitions (similar to structs)

## Nesting Data Structures

PicoMsg supports deep nesting of data structures, allowing you to build complex protocols:

### Basic Nesting

```
namespace api.v1;

struct Point {
    x: f32;
    y: f32;
}

struct Rectangle {
    top_left: Point;
    bottom_right: Point;
}

message DrawCommand {
    shape: Rectangle;
    color: u32;
}
```

### Arrays and Collections

```
struct Polygon {
    vertices: [Point];      // Array of Point structs
    colors: [u32];          // Array of color values
}

struct Scene {
    polygons: [Polygon];    // Array of Polygon structs
    metadata: [string];     // Array of strings
}
```

### Nested Arrays

```
struct Matrix {
    rows: [[f32]];          // 2D array (array of arrays)
}

struct Dataset {
    samples: [[[u8]]];      // 3D array
}
```

### Complex Nesting Example

```
namespace game.protocol;

struct Player {
    id: u32;
    name: string;
    position: Point;
    inventory: [Item];
}

struct Item {
    id: u16;
    name: string;
    properties: [Property];
}

struct Property {
    key: string;
    value: bytes;
}

message GameState {
    players: [Player];
    world_data: bytes;
    timestamp: u64;
}
```

### Binary Format Details

- **Alignment**: All multi-byte values use little-endian encoding
- **Struct Packing**: Structs are packed with 4-byte alignment
- **String Encoding**: Strings are UTF-8 encoded with `u16` length prefix
- **Array Format**: Arrays have `u16` count prefix followed by elements
- **Nested Structures**: Embedded structs are serialized inline

### Language-Specific Type Mapping

| PicoMsg | C | Rust | Python |
|---------|---|------|--------|
| `u8` | `uint8_t` | `u8` | `int` |
| `u32` | `uint32_t` | `u32` | `int` |
| `f64` | `double` | `f64` | `float` |
| `string` | `char*` | `String` | `str` |
| `bytes` | `uint8_t*` | `Vec<u8>` | `bytes` |
| `[Type]` | `Type*` | `Vec<Type>` | `List[Type]` |
| Custom struct | `struct_name_t` | `StructName` | `StructName` |

## JSON Conversion System

PicoMsg includes a comprehensive JSON conversion system with advanced features:

### Core Features
- **Schema-aware validation** with automatic type coercion
- **Streaming JSON parsing** for memory-efficient processing of large files
- **Pretty-printing** with customizable formatting
- **Error handling** with detailed validation messages
- **CLI integration** with dedicated JSON commands

### JSON CLI Commands

```bash
# Validate JSON against schema
picomsg json validate data.json --schema schema.pico

# Pretty-print JSON files
picomsg json pretty data.json --indent 4

# Convert between JSON formats
picomsg json convert data.json --format jsonlines --output data.jsonl

# Generate enhanced code with JSON support
picomsg json codegen schema.pico --lang python --output generated/

# Get schema information
picomsg json info schema.pico
```

### Streaming JSON Support

```python
from picomsg.json.streaming import StreamingJSONParser, StreamingJSONWriter

# Parse large JSON files efficiently
parser = StreamingJSONParser(schema)
for record in parser.parse_file("large_dataset.json"):
    # Process each record individually
    validated_data = parser.validate_record(record)

# Write streaming JSON output
writer = StreamingJSONWriter("output.jsonl", schema)
for data in large_dataset:
    writer.write_record(data)
```

## Installation

```bash
pip install picomsg
```

## Development

```bash
git clone https://github.com/picomsg/picomsg
cd picomsg
python -m venv venv
source venv/bin/activate
pip install -e .
```

## License

MIT License 
