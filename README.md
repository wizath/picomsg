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
- **JSON interoperability** for debugging and APIs

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
```

3. Use the generated code in your application.

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
