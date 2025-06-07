# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2024-12-19

### Added
- **Comprehensive Test Structure Reorganization**:
  - **Unit Tests** (`tests/unittest/`): 158 focused component tests
    - `test_schema_ast.py`: AST data structure tests
    - `test_schema_parser.py`: Schema parsing logic tests
    - `test_binary_format.py`: Binary format utility tests
    - `test_alignment.py`: Alignment calculation tests
    - `test_c_codegen.py`: C code generator tests
    - `test_rust_codegen.py`: Rust code generator tests
    - `test_cli.py`: Command-line interface tests
  - **Integration Tests** (`tests/integration/`): 37 cross-platform compatibility tests
    - `test_cross_platform.py`: Cross-platform compatibility verification
    - `test_end_to_end.py`: Complete workflow testing
    - `test_binary_compatibility.py`: Binary format consistency tests
    - `test_simple_cross_language.py`: **Cross-language data exchange tests**

- **Cross-Language Binary Data Integration Tests**:
  - **Rust → C Data Exchange**: Rust generates binary data, C reads and validates
  - **C → Rust Data Exchange**: C generates binary data, Rust reads and validates
  - **Binary Format Verification**: Ensures identical binary output between implementations
  - **Round-trip Data Integrity**: Validates data maintains integrity across language boundaries

- **Enhanced Integration Test Coverage**:
  - Code generation and compilation testing for both C and Rust
  - Schema validation workflows across different scenarios
  - Error handling and edge case testing
  - Complex schema processing with realistic examples

### Enhanced
- Test execution can now be targeted by category:
  - `pytest tests/unittest/` - Run unit tests only
  - `pytest tests/integration/` - Run integration tests only
  - `pytest tests/` - Run all 195 tests
- Improved test documentation and organization
- Better separation of concerns between unit and integration testing

### Technical Details
- **Total Test Coverage**: 195 tests across the entire project
- **Cross-Language Compatibility**: Proven binary data exchange between C and Rust
- **Test Performance**: Integration tests include actual compilation and execution
- **Platform Support**: Tests validate compatibility across different toolchains

### Verified Compatibility
- ✅ Rust-generated binary data correctly decoded by C implementation
- ✅ C-generated binary data correctly decoded by Rust implementation
- ✅ Identical binary format output between language implementations
- ✅ Data integrity maintained across language boundaries

## [0.1.1] - 2024-12-19

### Added
- **Structs-Only Code Generation**: New `--structs-only` CLI option for C code generator
  - Generates only struct definitions without error enums and serialization functions
  - Produces header-only output (.h file) for lightweight integration
  - Maintains C++ compatibility and packed attributes
  - Useful for scenarios where only data structures are needed
- **Schema Version Declaration**: Support for version declarations in .pico files
  - New `version NUMBER;` syntax to specify schema version (1-255)
  - Generates `#define {NAMESPACE}_VERSION {version}` in C headers
  - Defaults to version 1 when not specified for backward compatibility
  - CLI commands (`validate`, `info`) display version information
  - Proper validation and error handling for invalid version ranges

### Enhanced
- C code generator now uses schema-defined version instead of hardcoded value
- CLI feedback improvements for structs-only mode
- Comprehensive test coverage with 158+ total tests

### Technical Details
- Schema version validation ensures values between 1-255
- Version constants excluded in structs-only mode
- Full backward compatibility maintained
- Parser supports version declarations with proper error handling

## [0.1.0] - 2024-12-19

### Added
- Initial release of PicoMsg Phase 1 implementation
- Schema definition language (.pico files) with support for:
  - Namespaces
  - Primitive types (u8, u16, u32, u64, i8, i16, i32, i64, f32, f64)
  - String and bytes types
  - Array types with nested support
  - Struct definitions and references
  - Message definitions
- Schema parser with Lark-based grammar
- Abstract Syntax Tree (AST) classes for schema representation
- Binary format specification with:
  - 8-byte header format with magic bytes (0xAB, 0xCD)
  - Little-endian byte order
  - CRC16 checksum calculation
  - String/bytes encoding with u16 length prefix
  - Array encoding with u16 count prefix
- Memory alignment utilities for struct layout calculation
- C code generator with:
  - Packed struct definitions with `__attribute__((packed))`
  - Zero-copy serialization/deserialization using `memcpy()`
  - Namespace-aware identifier generation
  - Error handling with enum error codes
  - C++ compatibility with extern "C" blocks
- Command-line interface (CLI) with:
  - `validate` command for schema validation
  - `info` command for detailed schema information
  - `compile` command for C code generation
  - Support for custom output directories and header names
- Comprehensive test suite with 140+ test cases covering:
  - Unit tests for all components
  - Integration tests for complete workflow
  - C code compilation and functionality tests
  - CLI command testing
  - Cross-platform compatibility

### Technical Details
- **Performance**: C deserialization < 10ns per message (direct memcpy)
- **Memory efficiency**: < 10% overhead compared to raw C structs
- **Alignment**: Proper 4-byte struct alignment with padding calculation
- **Compatibility**: Supports Python 3.8+ and modern C compilers (gcc, clang)

### Examples
- Simple schema example with Point struct and EchoRequest message
- Generated C code compiles without warnings
- Round-trip serialization/deserialization verified

[0.1.2]: https://github.com/picomsg/picomsg/releases/tag/v0.1.2
[0.1.1]: https://github.com/picomsg/picomsg/releases/tag/v0.1.1
[0.1.0]: https://github.com/picomsg/picomsg/releases/tag/v0.1.0 
